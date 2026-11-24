"""Deterministic normalisation helpers. Original values are always kept alongside normalised ones."""
import re

BRANDS = {
    'lg': 'LG', 'lg electronics': 'LG', 'samsung': 'Samsung', 'whirlpool': 'Whirlpool', 'maytag': 'Maytag', 'ge': 'GE', 'general electric': 'GE',
    'bosch': 'Bosch', 'frigidaire': 'Frigidaire', 'hotpoint': 'Hotpoint', 'indesit': 'Indesit', 'beko': 'Beko', 'miele': 'Miele', 'candy': 'Candy',
    'hoover': 'Hoover', 'ifb': 'IFB', 'godrej': 'Godrej', 'haier': 'Haier', 'voltas': 'Voltas', 'daikin': 'Daikin', 'blue star': 'Blue Star',
    'bluestar': 'Blue Star', 'panasonic': 'Panasonic', 'hitachi': 'Hitachi', 'carrier': 'Carrier', 'lloyd': 'Lloyd', 'onida': 'Onida',
    'crompton': 'Crompton', 'havells': 'Havells', 'orient': 'Orient', 'usha': 'Usha', 'bajaj': 'Bajaj', 'atomberg': 'Atomberg', 'zanussi': 'Zanussi',
    'electrolux': 'Electrolux', 'siemens': 'Siemens', 'aeg': 'AEG', 'kenwood': 'Kenwood', 'dyson': 'Dyson',
    'kent': 'Kent', 'aquaguard': 'Aquaguard', 'eureka forbes': 'Aquaguard', 'pureit': 'Pureit', 'livpure': 'Livpure', 'ao smith': 'AO Smith',
}
UNKNOWN_BRAND = {'', 'unknown', 'n/a', 'na', 'none', '?', '-', 'not known', 'no brand', 'generic'}

CATEGORY = {
    'washer': 'washing_machine', 'washing machine': 'washing_machine', 'washing_machine': 'washing_machine',
    'refrigerator': 'refrigerator', 'fridge': 'refrigerator', 'fridge/freezer': 'refrigerator',
    'dryer': 'dryer', 'dishwasher': 'dishwasher', 'oven_range': 'oven_range',
    'split_ac': 'split_ac', 'aircon/dehumidifier': 'aircon_dehumidifier', 'fan': 'fan_other', 'ceiling_fan': 'ceiling_fan',
    'mcb_electrical': 'mcb_electrical', 'rooftop_solar': 'rooftop_solar', 'microwave': 'microwave_oven', 'microwave_oven': 'microwave_oven',
    'water purifier': 'water_purifier', 'water_purifier': 'water_purifier',
}

COMPONENTS = {
    'ntc thermistor': 'thermistor', 'thermistor': 'thermistor', 'temperature sensor': 'temperature sensor',
    'pcb': 'control board', 'main pcb': 'control board', 'control board': 'control board', 'main board': 'control board',
    'door lock': 'door lock', 'door interlock': 'door lock', 'door switch': 'door lock',
    'drain pump': 'drain pump', 'pump': 'drain pump', 'inlet valve': 'water inlet valve', 'water inlet valve': 'water inlet valve',
    'motor': 'drive motor', 'drive motor': 'drive motor', 'capacitor': 'capacitor', 'run capacitor': 'capacitor',
}

CODE_RE = re.compile(r'\b(?:error|code|err)?\s*([A-Z]{1,3}[ -]?\d{1,3}|\d{1,2}[A-Z]{1,2}|[A-Z][A-Z])\b')
SYMPTOMS = [
    ('not cooling', r'not cool|no cool|warm|not cold|cooling (is )?(low|weak|poor)'), ('not starting', r'won.?t start|not start|doesn.?t start|dead|no power|not turn(ing)? on'),
    ('noisy', r'nois|loud|rattl|grind|bang|squeal|hum'), ('vibration', r'vibrat|shak|walk|wobbl'), ('leaking', r'leak|drip|water on (the )?floor'),
    ('not draining', r'not drain|won.?t drain|water (stays|remains)'), ('not spinning', r'not spin|won.?t spin|no spin|drum (doesn.?t|won.?t) (turn|rotate)'),
    ('tripping breaker', r'trip|breaker|fuse blow'), ('burning smell', r'burn|smok|smell'), ('door will not open or lock', r'door (won.?t|not) (open|lock)|door lock'),
    ('error code shown', r'\berror\b|\bcode\b'), ('slow', r'\bslow'), ('ice build-up', r'\bice\b|frost'),
]


def clean(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return None if s == '' or s.lower() == 'nan' else re.sub(r'\s+', ' ', s)


def brand(v) -> str | None:
    s = clean(v)
    if not s or s.lower() in UNKNOWN_BRAND:
        return None
    return BRANDS.get(s.lower(), s.title() if s.islower() or s.isupper() else s)


def category(v) -> str | None:
    s = clean(v)
    return CATEGORY.get(s.lower()) if s else None


def error_code(v) -> str | None:
    """Uppercase and strip separators: 'e-21' -> 'E21', 'oE' -> 'OE'. The original is stored separately by callers."""
    s = clean(v)
    return re.sub(r'[\s\-_.:]', '', s).upper() if s else None


def component(v) -> str | None:
    s = clean(v)
    return COMPONENTS.get(s.lower(), s.lower()) if s else None


def symptoms(text: str | None) -> list[str]:
    t = (text or '').lower()
    return [label for label, rx in SYMPTOMS if re.search(rx, t)]


KW = {'error', 'code', 'err', 'showing', 'shows', 'show', 'displaying', 'displays', 'display', 'blinking', 'flashing'}
NOT_CODE = {'on', 'is', 'in', 'an', 'the', 'and', 'of', 'to', 'it', 'me', 'my', 'no', 'not', 'ka', 'ki', 'hai', 'aa', 'raha', 'rahi', 'number', 'code', 'error', 'par', 'pe', 'mein', 'me', 'pr', 'bhi', 'hi'}


def extract_codes(text: str) -> list[str]:
    """Error codes a technician typed, normalised. Mixed letter+digit tokens (E21, 4C, F3E0) always count.
    Pure-letter or pure-digit tokens (IF, OE, 22) only count right after a word like code/error/showing.
    'Er IF' style codes yield both 'IF' and 'ERIF', because sources differ on keeping the prefix."""
    words = re.findall(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?', text)
    out: list[str] = []
    for i, w in enumerate(words):
        lw = w.lower()
        prev = words[i - 1].lower() if i else ''
        if lw == 'ch' and i + 1 < len(words) and re.fullmatch(r'\d{1,3}', words[i + 1]):  # LG writes 'CH 38' as well as 'CH38'
            out.append(error_code(w + words[i + 1])); continue
        if prev == 'ch' and re.fullmatch(r'\d{1,3}', lw):
            continue
        if re.fullmatch(r'(?=[a-z0-9-]*\d)(?=[a-z0-9-]*[a-z])[a-z0-9-]{2,6}', lw) and not re.fullmatch(r'\d+(am|pm|kg|hz|w|v|s|min|hp|ton|tr|l)', lw):
            out.append(error_code(w))
        elif prev in KW and lw not in NOT_CODE and lw not in KW and re.fullmatch(r'[a-z]{2,3}|\d{1,3}', lw):
            if lw in ('er', 'err') and i + 1 < len(words) and re.fullmatch(r'[a-z0-9]{1,3}', words[i + 1].lower()):
                out += [error_code(words[i + 1]), error_code(w + words[i + 1])]
            else:
                out.append(error_code(w))
    return list(dict.fromkeys(c for c in out if c))


def steps(text: str | None) -> list[str]:
    s = clean(text)
    if not s:
        return []
    parts = [p.strip(' ;') for p in re.split(r'(?<=[.;])\s+(?=[A-Z])|\n+|\s*\d+[.)]\s+', s) if p and p.strip(' ;')]
    return parts or [s]


# One shared definition of power-sensitive text (also used by steps, chat and the live relay).
from ..core.power_rules import POWER_WORDS, step_needs_power_off  # noqa: E402,F401
CATEGORY_SAFETY = {
    'washing_machine': ['Unplug the machine or switch off at the MCB and verify with your own tester before removing any panel.', 'Drain residual water before tilting or opening.'],
    'refrigerator': ['Unplug before removing covers. Sealed-system or gas work needs a certified technician.'],
    'split_ac': ['Switch off at the MCB and verify with your own tester before opening covers. Refrigerant handling needs certification.'],
    'aircon_dehumidifier': ['Unplug before opening. Refrigerant handling needs certification.'],
    'ceiling_fan': ['Switch off at the MCB and verify with your own tester. Discharge the capacitor before handling.'],
    'fan_other': ['Unplug before opening.'],
    'mcb_electrical': ['Isolate upstream and verify with your own tester before touching the board.'],
    'rooftop_solar': ['DC side can remain live in daylight. Escalate DC and inverter work to a qualified solar technician.'],
    'microwave_oven': ['Unplug before cleaning. Never remove the outer cabinet: the high-voltage capacitor can hold a lethal charge after unplugging. Magnetron, door interlock and internal work is for authorised service only.'],
    'water_purifier': ['Close the inlet valve and unplug before touching filters or tubing. Filter, membrane, UV lamp and SMPS work is for an authorised technician.'],
    'dryer': ['Unplug before opening.'], 'dishwasher': ['Unplug and isolate water before opening.'], 'oven_range': ['Isolate power (and gas where fitted) before opening.'],
}


def safety_policy(category_: str, step_list: list[str]) -> tuple[bool, list[str]]:
    needs = any(step_needs_power_off(s) for s in step_list)
    pol = list(CATEGORY_SAFETY.get(category_, []))
    if needs:
        pol.append('FixSaathi keeps power-sensitive steps locked until the technician records power-off and tester-check statements.')
    return needs, pol


# Appliance detection from free text. Named appliances are checked before generic words, so "fridge not cooling" is a
# refrigerator, "AC indoor fan" is an AC and "ceiling fan" is a fan. Order matters.
APPLIANCE_PATTERNS = [
    ('microwave_oven', r'\bmicro ?waves?\b|माइक्रोवेव'),
    ('water_purifier', r'\bpurifiers?\b|\bro (?:water|filter|purifier|machine|system|unit|membrane)\b|\bwater filter\b|\b(?:aquaguard|kent|pureit|livpure)\b|\bpurified water\b|प्यूरीफायर|आरओ'),
    ('refrigerator', r'\bfridges?\b|\brefrigerators?\b|\bfreezers?\b|\bfrij\b|फ्रिज|फ्रीज|रेफ्रिजरेटर'),
    ('washing_machine', r'\bwashing\b|\bwashers?\b|\bwasher\b|\b(?:top|front) ?load\b|वॉशिंग|वाशिंग'),
    ('split_ac', r'\bsplit\b|\bacs?\b|\bair ?condition\w*|\baircon\b|एसी|ए\.सी'),
    ('ceiling_fan', r'\bceiling fans?\b|\bfans?\b|\bpankha\b|पंखा|पंखे'),
    ('mcb_electrical', r'\bmcb\b|\brccb\b|\belcb\b|\bbreaker\b|\bdistribution board\b'),
    ('rooftop_solar', r'\bsolar\b'),
]
WEAK_APPLIANCE_PATTERNS = [('split_ac', r'\bcooling\b'), ('washing_machine', r'\bspin\w*|\bdrum\b'), ('mcb_electrical', r'\btrip\w*')]


def detect_appliance(text: str | None) -> str:
    """Best guess at the appliance a technician is describing, or 'unknown'. Deterministic and explainable."""
    t = (text or '').lower()
    for pats in (APPLIANCE_PATTERNS, WEAK_APPLIANCE_PATTERNS):
        for cat, rx in pats:
            if re.search(rx, t):
                return cat
    return 'unknown'
