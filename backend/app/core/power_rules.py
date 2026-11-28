"""The one definition of "power-sensitive" text, shared by repair steps, chat replies, the live relay and dataset import.

Two levels:
- POWER_WORDS (steps): any mention of opening, covers, wiring, terminals, capacitors, boards and similar internals.
  Deliberately broad: a structured step that touches these is locked until the safety statements are recorded.
- ACTION_WORDS (free text): an instruction to *do* power-sensitive work (open, remove, discharge, measure, bypass...).
  Used on chat and live replies, where merely naming a likely faulty part ("a weak capacitor") must stay readable.

Hindi/Hinglish verbs are included because technicians and the model both use them (khol = open, nikal = take out,
badal = replace, jod = connect, chhu = touch, taar = wire). Keep this list conservative: adding words only makes the
gate stricter; removing words weakens it.
"""
import re

POWER_WORDS = re.compile(
    r'\b(open(s|ed|ing)?|remov(e|es|ed|ing|al)|unscrew\w*|disconnect\w*|detach\w*|dismantl\w*|cover(s)?|canopy|panel(s)?|'
    r'wire(s|d)?|wiring|terminal(s)?|capacitor(s)?|discharg\w*|replac(e|es|ed|ing|ement)|solder\w*|connector(s)?|'
    r'board(s)?|pcb(s)?|element(s)?|motor(s)?|pump(s)?|valve(s)?|thermistor(s)?|compressor(s)?|'
    r'multimeter|continuity|live (wire|terminal|circuit|side)|bypass\w*|jumper\w*|'
    r'khol\w*|nikal\w*|nikaal\w*|taar)\b', re.I)

ACTION_WORDS = re.compile(
    r'\b(open(s|ed|ing)?|remov(e|es|ed|ing)|unscrew\w*|disconnect\w*|detach\w*|dismantl\w*|take (it |them |(?!(the |your )?(plug|food|clothes|laundry|load|dish|bowl|plate|filter)\b)(\w+ ){1,3}?)?(off|out|apart)|'
    r'pull (it |them )?(off|out)|lift (off )?the (cover|panel|lid)|lower(ing)? the (canopy|cover|panel)|slide (the )?(canopy|cover) down|'
    r'take down|unclip\w*|unmount\w*|pr(y|ise|ize) (off|open|out)|loosen(ing)? the (canopy|cover|panel|screw|terminal)\w*|expos(e|es|ing) the|'
    r'access(ing)? the (capacitor|terminal|wire|wiring|board|pcb|motor|inside|internal|housing|connection)\w*|discharg\w*|replac(e|es|ed|ing)|swap(ping)?|solder\w*|desolder\w*|'
    r'rewir\w*|re-?connect\w*|strip(ping)? the|cut the wire|touch(ing)? the (terminal|wire|capacitor|board|pcb|contact)\w*|'
    r'probe\w*|measur\w*|(check|test|read)(s|ing)? (the |for )?(voltage|current|supply) (across|between|at the (terminal|wire|capacitor|board|pcb)|on the (terminal|wire|capacitor|board|pcb))|multimeter|continuity|megger|short(ing)? (the|across|out)|bridg(e|ing) the|bypass\w*|jumper\w*|'
    r'khol\w*|nikal\w*|nikaal\w*|badal\w*|jod\w*|chhu\w*|chhoo\w*)\b', re.I)

# Steps in a chat reply. Live internal parts: a step that reaches, reads or handles them needs isolation however it is phrased
# ("Note the microfarad rating printed on the capacitor" means the canopy is already open). The verbs of POWER_WORDS are in
# ACTION_WORDS. External parts (motor, pump, compressor, valve, cover, panel) lock unless the step only observes them, so
# "Note the error code on the display panel" or "Listen for the compressor clicking" stays readable.
_LIVE = (r'canopy|(?<!thin )(?<!stiff )(?<!piece of )(?<!cleaning )wire(s|d)?(?! brush)|wiring|terminal(s)?|capacitor(s)?|connector(s)?|(control |main |power |circuit )?board(s)?|pcb(s)?|'
         r'element(s)?|thermistor(s)?|relay(s)?|ptc|olp|overload (protector|relay)|starter( relay)?|winding(s)?|taar')
LIVE_PARTS = re.compile(rf'\b({_LIVE}|removal|multimeter|continuity|live (wire|terminal|circuit|side))\b', re.I)
SOFT_PARTS = re.compile(r'\b(cover(s)?|panel(s)?|motor(s)?|pump(s)?|valve(s)?|compressor(s)?)\b', re.I)
# A step that only watches or listens. Anything else done to an external part (tighten, clean, shake, pull...) is hands-on.
OBSERVE_ONLY = re.compile(r'^\W*(listen|hear|note|notice|watch|observe|wait|record|count|see|look (at|for)|read)\b(?!.*\b(inside|behind)\b)', re.I)
# Free text: checking, testing or handling a live internal part is work on it ("Check the capacitor terminals for burn marks",
# "Unplug the PTC starter from the compressor"). Same sentence only.
HANDS_ON_LIVE = re.compile(
    r'\b(check(s|ing)?|test(s|ing)?|inspect(s|ing)?|examin(e|es|ing)|clean(s|ing)?|tighten(s|ing)?|feel(s|ing)?|look(ing)? (at|for)|'
    r'unplug(s|ging)?|pull(s|ing)?|shak(e|es|ing)|tap(s|ping)?|fit(s|ting)?|install(s|ing)?|swap(s|ping)?)'
    rf'(?:[^\w.!?]+\w+){{0,4}}?[^\w.!?]+(?=({_LIVE})\b)', re.I)
# A list item that opens with one of these names a suspected fault ("Faulty PTC relay", "Weak capacitor"), not a step to perform.
FAULT_LEAD = re.compile(
    r'^(\W*)(faulty|weak|failed|failing|worn|burnt|burned|damaged|defective|bad|blown|stuck|jammed|clogged|blocked|loose|low|dead|'
    r'leaking|leaky|broken|tripped|dirty|shorted|cracked|seized|swollen|bulging|degraded|overheating|tight|dry|corroded|'
    r'insufficient|incorrect|wrong|possible|likely|probable|suspected)\b', re.I)
# A clause that opens with one of these is an instruction, even inside a list of causes ("- Unplug the PTC and shake it").
IMPERATIVE = re.compile(
    r'^\W*(unplug|plug|check|test|measure|remove|open|inspect|look|listen|note|spin|clean|replace|disconnect|try|turn|switch|'
    r'verify|use|take|pull|push|shake|feel|tighten|ensure|make|set|reset|press|fit|install|swap|tap|hold|lift|lower|access|'
    r'bridge|short|apply|connect|reconnect|discharge|probe|examine|confirm|compare|read|clear|move|adjust|lubricate|oil|grease|'
    r'unscrew|screw|loosen|cut|strip|solder|bypass|jumper|insert|attach|detach|clip|unclip|mount|unmount|start|run|power)\b', re.I)

# A verb within a few words after one of these is a prohibition ("never open", "do not touch the terminals", "mat kholna").
NEGATION = re.compile(r"\b(not|never|don'?t|do not|avoid|without|mat|na|nahi|nahin|kabhi)\b(\W+\w+){0,3}\W*$", re.I)
# A verb used as a precondition is the safety reminder itself, not the work: "before opening the canopy, switch off the MCB",
# "canopy kholne se pehle MCB off karo". The work verb that follows such a reminder is still caught on its own.
BEFORE = re.compile(r'\b(before|prior to|until)\W*$', re.I)
BEFORE_HI = re.compile(r'^\w*\s+(se|ke|say)\s+(pehle|pahle|pehele)\b', re.I)

# Hindi in Devanagari. \b does not work inside Devanagari words (vowel signs are not \w), so these match word stems.
# Work verbs: open, take out, change, join, touch, cut, remove, discharge, short, bypass.
HI_ACTION = re.compile(r'(खोल|निकाल|बदल|जोड़|जोड़|छू|छुए|छुएं|काट|हटा|डिस्चार्ज|शॉर्ट|बाईपास|बायपास|मल्टीमीटर|मीटर लगा)')
# Measuring voltage or current is live work ("मल्टीमीटर से वोल्टेज चेक करें").
HI_MEASURE = re.compile(r'(वोल्टेज|करंट|वोल्ट)[^।.!?\n]{0,40}?(चेक|जांच|जाँच|नाप|माप|टेस्ट(?!र))|(चेक|जांच|जाँच|नाप|माप|टेस्ट(?!र))[^।.!?\n]{0,20}?(वोल्टेज|करंट)')
HI_NEGATION = re.compile(r'(^|\s)(मत|न|ना|नहीं|नहीँ|कभी|बिना)\s+(\S+\s+){0,2}$')
HI_BEFORE = re.compile(r'^[^।.!?\n]{0,30}?(से|के)\s+(पहले|पूर्व)')


def _hi_instruction(t: str) -> bool:
    for rx in (HI_ACTION, HI_MEASURE):
        for m in rx.finditer(t):
            if HI_NEGATION.search(t[max(0, m.start() - 25):m.start()]) or HI_BEFORE.match(t[m.start():]):
                continue
            return True
    return False


MICROWAVE_INTERNAL = re.compile(
    r'\b(cabinet|outer (case|cover)|remove (the )?(cover|case|casing|panel)|open(ing)? (the )?(oven|microwave|case|casing|cover|panel)|'
    r'unscrew|magnetron|high[- ]voltage|hv (capacitor|diode|transformer)|capacitor|diode|transformer|interlock switch)\b', re.I)
MICROWAVE_ESCALATION = ('Do not open the microwave. Its high-voltage capacitor can hold a lethal charge even after unplugging. '
                        'Unplug the oven, note the symptom and model number, and hand it to authorised service.')


# Scripts these rules cannot read: Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, and Arabic/Urdu.
# (Devanagari Hindi and Latin-script English/Hinglish have rules above.) Text in them cannot be checked for live-work
# instructions, so it is treated as power-sensitive: withheld until isolation is recorded, never shown unscreened.
UNSCREENED_SCRIPT = re.compile(r'[\u0600-\u06FF\u0980-\u0D7F]')
SCREENED_LANGUAGES = ('English', 'Hindi')


# Fixed sentences the app itself prescribes (the creator answer in Kannada and Tamil). They describe no work, so they pass.
_FIXED_SAFE = re.compile(r'(ನನ್ನನ್ನು|என்னை|FixSaathi(-ಅನ್ನು|-ஐ)?)\s*[A-Za-z .]{2,60}?\s*(ಅವರು ರಚಿಸಿದ್ದಾರೆ|ಅವರು ರಚಿಸಿದರು|உருவாக்கினார்)\s*[.।]?')


def unscreenable(text: str) -> bool:
    """True if the text contains a script the safety rules cannot read."""
    return bool(UNSCREENED_SCRIPT.search(_FIXED_SAFE.sub(' ', text or '')))


def step_needs_power_off(text: str) -> bool:
    """Structured repair steps: broad rule."""
    return unscreenable(text) or bool(POWER_WORDS.search(text or '') or ACTION_WORDS.search(text or '') or _hi_instruction(text or ''))


def _is_instruction(t: str, m: re.Match) -> bool:
    before = t[max(0, m.start() - 40):m.start()]
    if NEGATION.search(before) or BEFORE.search(before):
        return False
    return not BEFORE_HI.search(t[m.start():m.end() + 20])


def instructs_power_work(text: str) -> bool:
    """Free text: True if it tells someone to do power-sensitive work. Prohibitions ('never open the cover') and
    preconditions ('before opening it, switch off the MCB') do not count; the work itself does."""
    t = text or ''
    return (unscreenable(t) or any(_is_instruction(t, m) for rx in (ACTION_WORDS, HANDS_ON_LIVE) for m in rx.finditer(t))
            or _hi_instruction(t))


def step_text_needs_power_off(text: str) -> bool:
    """A numbered or bulleted step in a reply: locked if it does power-sensitive work, reaches a live internal part, or does
    anything other than observe an external part (motor, compressor, panel...). Only explicit prohibitions pass."""
    t = text or ''

    def hit(rx: re.Pattern) -> bool:
        return any(not NEGATION.search(t[max(0, m.start() - 40):m.start()]) for m in rx.finditer(t))
    return (unscreenable(t) or hit(ACTION_WORDS) or hit(LIVE_PARTS) or hit(HANDS_ON_LIVE) or (hit(SOFT_PARTS) and not OBSERVE_ONLY.match(t))
            or _hi_instruction(t))


def mentions_microwave_internals(text: str) -> bool:
    t = text or ''
    if unscreenable(t):
        return True
    for m in MICROWAVE_INTERNAL.finditer(t):
        if not NEGATION.search(t[max(0, m.start() - 40):m.start()]):
            return True
    return False
