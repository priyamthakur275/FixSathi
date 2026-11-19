import sys, io, json, copy
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
from reportlab.lib.colors import HexColor, white

F = "/usr/share/fonts/truetype/google-fonts/"
pdfmetrics.registerFont(TTFont("R", F + "Poppins-Regular.ttf"))
pdfmetrics.registerFont(TTFont("M", F + "Poppins-Medium.ttf"))
pdfmetrics.registerFont(TTFont("B", F + "Poppins-Bold.ttf"))
pdfmetrics.registerFont(TTFont("L", F + "Poppins-Light.ttf"))

W, H = 720, 405
INK, GREY, LINE = HexColor("#202124"), HexColor("#5f6368"), HexColor("#dadce0")
BLUE, RED, YEL, GRN = HexColor("#4285F4"), HexColor("#EA4335"), HexColor("#F9AB00"), HexColor("#34A853")
TINT = {BLUE: "#E8F0FE", RED: "#FCE8E6", YEL: "#FEF7E0", GRN: "#E6F4EA"}
FILLC = HexColor("#D93025")

D = json.load(open(sys.argv[1]))


def T(y):  # top-based -> reportlab y
    return H - y


def text(c, x, ytop, s, font="R", size=9, color=INK, width=None, lead=None):
    """Draw wrapped text starting with its top at ytop. Returns bottom y (top-based)."""
    lead = lead or size * 1.32
    lines = simpleSplit(s, font, size, width) if width else [s]
    for i, ln in enumerate(lines):
        col = FILLC if "[FILL" in ln else color
        c.setFillColor(col)
        c.setFont(font, size)
        c.drawString(x, T(ytop + size * 0.95 + i * lead), ln)
    return ytop + len(lines) * lead


def cover_typehere(c):
    c.setFillColor(white)
    c.rect(36, T(160), 300, 26, stroke=0, fill=1)


def heading(c, title, sub):
    text(c, 39, 82, title, "M", 18.5)
    text(c, 39, 106, sub, "R", 10.5, GREY)


def card(c, x, ytop, w, h, accent, title, body, tsize=9.5, bsize=8):
    c.setFillColor(HexColor(TINT[accent]))
    c.roundRect(x, T(ytop + h), w, h, 7, stroke=0, fill=1)
    c.setFillColor(accent)
    c.roundRect(x, T(ytop + 4), w, 4, 2, stroke=0, fill=1)
    y = text(c, x + 10, ytop + 11, title, "M", tsize, INK, w - 20)
    text(c, x + 10, y + 3, body, "R", bsize, HexColor("#3c4043"), w - 20, bsize * 1.38)


def box(c, x, ytop, w, h, accent, title, sub=None, tsize=8.3, ssize=6.8):
    c.setFillColor(HexColor(TINT[accent]))
    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.roundRect(x, T(ytop + h), w, h, 6, stroke=1, fill=1)
    y = text(c, x + 7, ytop + 6, title, "M", tsize, INK, w - 14)
    if sub:
        text(c, x + 7, y + 1, sub, "R", ssize, GREY, w - 14, ssize * 1.3)


def arrow(c, x1, y1, x2, y2, col=GREY, both=False):
    import math
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(1.1)
    c.line(x1, T(y1), x2, T(y2))
    def head(xa, ya, xb, yb):
        ang = math.atan2(T(yb) - T(ya), xb - xa)
        p = c.beginPath()
        p.moveTo(xb, T(yb))
        p.lineTo(xb - 6 * math.cos(ang - 0.4), T(yb) - 6 * math.sin(ang - 0.4))
        p.lineTo(xb - 6 * math.cos(ang + 0.4), T(yb) - 6 * math.sin(ang + 0.4))
        p.close(); c.drawPath(p, stroke=0, fill=1)
    head(x1, y1, x2, y2)
    if both:
        head(x2, y2, x1, y1)


# ---------------- slides ----------------
def s_cover(c):
    c.setFillColor(white)
    text(c, 135, 263, D["team_name"], "M", 13)
    text(c, 125, 297, D["team_size"], "M", 13)
    text(c, 185, 331, D["problem_line"], "R", 10.5, INK, 500, 13.5)
    text(c, 53, 372, D["product_line"], "M", 11, BLUE, 620)


def s_problem(c):
    cover_typehere(c)
    cols = [BLUE, RED, YEL, GRN]
    cw, gap = 151, 9
    for i, (t, b) in enumerate(D["pains"]):
        card(c, 39 + i * (cw + gap), 140, cw, 122, cols[i], t, b)
    c.setFillColor(HexColor("#F1F3F4"))
    c.roundRect(39, T(380), 631, 104, 7, stroke=0, fill=1)
    text(c, 51, 284, "Who is affected", "M", 9.5)
    text(c, 51, 299, D["affected"], "R", 8.3, HexColor("#3c4043"), 600, 11.5)
    text(c, 51, 333, D["gt_label"], "M", 9.5)
    text(c, 51, 348, D["ground_truth"], "R", 8.3, HexColor("#3c4043"), 600, 11.5)


def s_solution(c):
    cover_typehere(c)
    text(c, 39, 136, D["solution_line"], "M", 11.5, BLUE, 640)
    cols = [BLUE, RED, YEL, GRN, BLUE]
    bw, gap = 118, 10.25
    for i, (t, b) in enumerate(D["flow"]):
        x = 39 + i * (bw + gap)
        c.setFillColor(cols[i]); c.circle(x + 13, T(176), 9, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("B", 9); c.drawCentredString(x + 13, T(179.3), str(i + 1))
        text(c, x + 27, 170, t, "M", 8.8, INK, bw - 27)
        text(c, x, 192, b, "R", 7.6, HexColor("#3c4043"), bw - 4, 10.2)
        if i < 4:
            arrow(c, x + bw - 6, 176, x + bw + gap + 1, 176, LINE)
    cw = 204
    for i, (t, b) in enumerate(D["outcomes"]):
        card(c, 39 + i * (cw + 9.5), 290, cw, 92, [GRN, BLUE, YEL][i], t, b)


def s_arch(c):
    cover_typehere(c)
    # column 1: people
    box(c, 39, 140, 128, 104, BLUE, "Technician app", "Phone browser / PWA. Camera 1 fps + mic 16 kHz in, voice out. Hinglish, Kannada, Tamil, English. Safety lock, steps, report.")
    box(c, 39, 254, 128, 70, GRN, "Manager dashboard", "Live feed: jobs, safety, first-time fix, rated accuracy, AI cost per repair")
    c.setDash(3, 2)
    box(c, 39, 334, 128, 48, YEL, "Roadmap: Gemma offline", "On-device checklist and notes, sync later")
    c.setDash()
    # column 2: cloud core
    box(c, 200, 140, 150, 70, BLUE, "Cloud Run session service", "Node, asia-south1. WebSocket relay of live audio/video; key in Secret Manager; auto-reconnect")
    box(c, 200, 222, 150, 76, RED, "Gemini Live API", "Sees and hears the repair in real time, speaks guidance, calls our tools via function calling")
    box(c, 200, 310, 150, 72, GRN, "Firestore", "Jobs, service reports, before/after photos, measured cost, reply time and technician ratings")
    # column 3: tools / agents
    c.setStrokeColor(LINE); c.setDash(3, 2); c.setLineWidth(1)
    c.roundRect(383, T(382), 287, 242, 8, stroke=1, fill=0); c.setDash()
    text(c, 393, 146, "Tools Gemini Live calls (function calling)", "M", 8.8, INK, 270)
    agents = [(RED, "Safety gate (in code)", "Blocks any step that touches wires until power-off and tester check are confirmed"),
              (BLUE, "Diagnosis agent: Gemini API", "Ranks likely causes from symptom + live frame + fault knowledge base (JSON)"),
              (YEL, "Part locator: Gemini API", "Returns the part's box on the live frame; the app draws the marker"),
              (GRN, "Step cards: Nano Banana", "Visual picture card for a step, from the real camera frame"),
              (BLUE, "Report agent: Gemini API", "Structured JSON service report at job end, saved with photos")]
    for i, (col, t, s_) in enumerate(agents):
        yy = 164 + i * 43
        box(c, 393, yy, 267, 37, col, t, s_, 8, 6.8)
    arrow(c, 167, 190, 200, 175, GREY, both=True)
    arrow(c, 275, 210, 275, 222, GREY, both=True)
    arrow(c, 350, 260, 383, 260, GREY, both=True)
    arrow(c, 275, 298, 275, 310, GREY)
    arrow(c, 200, 345, 167, 290, GREY)


def s_tools(c):
    cover_typehere(c)
    cols = [BLUE, RED, GRN]
    cw = 204
    for i, (t, b) in enumerate(D["tools"]):
        card(c, 39 + i * (cw + 9.5), 140, cw, 150, cols[i], t, b, 10.5, 8.1)
    c.setFillColor(HexColor("#F1F3F4"))
    c.roundRect(39, T(382), 631, 80, 7, stroke=0, fill=1)
    text(c, 51, 311, "Deployed and scaled on Google Cloud", "M", 9.5)
    text(c, 51, 326, D["cloud"], "R", 8.2, HexColor("#3c4043"), 605, 11.3)


def s_models(c):
    cover_typehere(c)
    cols = [RED, BLUE, YEL, GRN]
    y = 140
    c.setFillColor(GREY); c.setFont("M", 8)
    for x, h in [(51, "MODEL"), (175, "WHAT IT DOES IN FIXSAATHI"), (520, "WHY THIS MODEL")]:
        c.drawString(x, T(y + 8), h)
    y = 154
    for i, (m, role, why) in enumerate(D["models"]):
        h = 54
        c.setFillColor(HexColor(TINT[cols[i]]))
        c.roundRect(39, T(y + h), 631, h, 6, stroke=0, fill=1)
        c.setFillColor(cols[i]); c.roundRect(39, T(y + h), 4, h, 2, stroke=0, fill=1)
        text(c, 51, y + 8, m, "M", 10, INK, 115)
        text(c, 175, y + 7, role, "R", 7.9, HexColor("#3c4043"), 330, 10.6)
        text(c, 520, y + 7, why, "R", 7.9, HexColor("#3c4043"), 140, 10.6)
        y += h + 6


def s_business(c):
    heading(c, "Business Model & Market", "Who pays, how much, and how we reach them.")
    cols = [BLUE, RED, GRN]
    cw = 204
    for i, (t, b) in enumerate(D["pricing"]):
        card(c, 39 + i * (cw + 9.5), 132, cw, 100, cols[i], t, b, 9.5, 7.9)
    text(c, 39, 245, "Extra revenue: " + D["extra_rev"], "R", 8.2, HexColor("#3c4043"), 630, 11)
    text(c, 39, 270, "Go-to-market", "M", 10)
    cw = 204
    for i, (t, b) in enumerate(D["gtm"]):
        card(c, 39 + i * (cw + 9.5), 288, cw, 94, [YEL, BLUE, GRN][i], t, b, 9.3, 7.8)


def s_comp(c):
    heading(c, "Competition & Differentiation", "Why existing options leave technicians on their own.")
    xs = [51, 205, 420]
    c.setFillColor(GREY); c.setFont("M", 8)
    for x, h in zip(xs, ["ALTERNATIVE", "WHAT IT DOES", "GAP FOR THE TECHNICIAN"]):
        c.drawString(x, T(140), h)
    y = 148
    for i, (a, w_, g) in enumerate(D["competitors"]):
        hl = i == len(D["competitors"]) - 1
        h = 40
        c.setFillColor(HexColor("#E8F0FE") if hl else HexColor("#F8F9FA"))
        c.roundRect(39, T(y + h), 631, h, 6, stroke=0, fill=1)
        if hl:
            c.setFillColor(BLUE); c.roundRect(39, T(y + h), 4, h, 2, stroke=0, fill=1)
        text(c, xs[0], y + 7, a, "M", 8.6, BLUE if hl else INK, 145, 10.5)
        text(c, xs[1], y + 7, w_, "R", 7.8, HexColor("#3c4043"), 205, 10.3)
        text(c, xs[2], y + 7, g, "M" if hl else "R", 7.8, INK if hl else HexColor("#3c4043"), 240, 10.3)
        y += h + 5
    text(c, 39, y + 6, "Moat: " + D["moat"], "R", 8.2, INK, 630, 11)


def s_team(c):
    heading(c, "Founding Team & Roadmap", "Who is building FixSaathi and what we will ship.")
    n = len(D["team"])
    y = 132
    text(c, 39, y, "Founding team", "M", 10)
    y += 18
    h = min(72, (250 - 6 * (n - 1)) / max(n, 1))
    cols = [BLUE, RED, YEL, GRN]
    for i, (nm, role, bg) in enumerate(D["team"]):
        c.setFillColor(HexColor(TINT[cols[i % 4]]))
        c.roundRect(39, T(y + h), 300, h, 6, stroke=0, fill=1)
        c.setFillColor(cols[i % 4]); c.circle(56, T(y + h / 2), 9, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("B", 8.5)
        ini = "".join(p[0] for p in nm.replace("[", "").split()[:2]).upper() if "[FILL" not in nm else "?"
        c.drawCentredString(56, T(y + h / 2 + 3), ini)
        yy = text(c, 72, y + 6, nm + "  ·  " + role, "M", 8.6, INK, 260)
        text(c, 72, yy + 1, bg, "R", 7.5, HexColor("#3c4043"), 260, 9.8)
        y += h + 6
    if D.get("team_note"):
        c.setFillColor(HexColor("#F1F3F4")); c.roundRect(39, T(y + 46), 300, 46, 6, stroke=0, fill=1)
        text(c, 49, y + 7, D["team_note"], "R", 7.6, INK, 282, 10.2)
    text(c, 362, 132, "Roadmap", "M", 10)
    y = 150
    cols = [GRN, BLUE, YEL, RED]
    for i, (when, what) in enumerate(D["roadmap"]):
        c.setFillColor(cols[i]); c.circle(370, T(y + 6), 4.5, stroke=0, fill=1)
        if i < len(D["roadmap"]) - 1:
            c.setStrokeColor(LINE); c.setLineWidth(1.2); c.line(370, T(y + 12), 370, T(y + 52))
        text(c, 382, y, when, "M", 8.8, INK, 290)
        text(c, 382, y + 13, what, "R", 7.8, HexColor("#3c4043"), 288, 10.3)
        y += 58


def s_market(c):
    heading(c, "Market Opportunity & Why Now", "A fast-growing installed base, too few skilled hands, and AI that can finally see.")
    cols = [BLUE, RED, YEL, GRN]
    cw, gap = 151, 9
    for i, (big, lab) in enumerate(D["stats"]):
        x = 39 + i * (cw + gap)
        c.setFillColor(HexColor(TINT[cols[i]])); c.roundRect(x, T(232), cw, 100, 7, stroke=0, fill=1)
        c.setFillColor(cols[i]); c.roundRect(x, T(136), cw, 4, 2, stroke=0, fill=1)
        text(c, x + 10, 146, big, "B", 19, INK, cw - 20)
        text(c, x + 10, 176, lab, "R", 7.6, HexColor("#3c4043"), cw - 20, 10.2)
    text(c, 39, 246, "Why now", "M", 10)
    y = 262
    for b in D["why_now"]:
        c.setFillColor(BLUE); c.circle(45, T(y + 5.5), 2.2, stroke=0, fill=1)
        y = text(c, 53, y, b, "R", 8.2, HexColor("#3c4043"), 615, 11) + 4
    text(c, 39, 384, D["sources"], "L", 6, GREY, 640, 7.5)


def phone(c, x, ytop, w, h):
    c.setFillColor(HexColor("#202124")); c.roundRect(x, T(ytop + h), w, h, 14, stroke=0, fill=1)
    c.setFillColor(white); c.roundRect(x + 4, T(ytop + h - 4), w - 8, h - 8, 11, stroke=0, fill=1)
    c.setFillColor(HexColor("#202124")); c.roundRect(x + w/2 - 14, T(ytop + 10), 28, 4, 2, stroke=0, fill=1)


def tick(c, x, ytop, col=GRN, s=6):
    c.setStrokeColor(col); c.setLineWidth(1.4)
    c.line(x, T(ytop + s*0.55), x + s*0.38, T(ytop + s)); c.line(x + s*0.38, T(ytop + s), x + s, T(ytop + s*0.15))


def fan(c, cx, cy, r):
    import math
    c.setFillColor(HexColor("#bdc1c6"))
    for k in range(3):
        a = math.radians(90 + k * 120)
        p = c.beginPath()
        p.moveTo(cx, T(cy))
        for t in range(0, 21):
            u = t / 20; ang = a - 0.28 + 0.56 * u; rr = r * (0.25 + 0.75 * math.sin(math.pi * u) ** 0.4)
            p.lineTo(cx + rr * math.cos(ang), T(cy) + rr * math.sin(ang))
        p.close(); c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(HexColor("#e8eaed")); c.circle(cx, T(cy), r * 0.2, stroke=0, fill=1)
    c.setFillColor(HexColor("#9aa0a6")); c.rect(cx - 2, T(cy - r * 0.2), 4, r * 0.75, stroke=0, fill=1)


def s_mockup(c):
    heading(c, "Product Preview", "What the technician sees on the job (concept mockup of the MVP).")
    W_, H_ = 122, 232
    cols = [39 + i * 213.7 for i in range(3)]
    top = 124
    # ---- phone 1: live guidance
    x = cols[0] + (213.7 - W_) / 2 - 20; phone(c, x, top, W_, H_)
    ix, iw = x + 4, W_ - 8
    c.setFillColor(HexColor("#3c4043")); c.rect(ix, T(top + 214), iw, 196, stroke=0, fill=1)
    c.setFillColor(HexColor("#9aa0a6")); c.rect(ix + iw/2 - 2, T(top + 100), 4, 44, stroke=0, fill=1)
    fan(c, ix + iw / 2, top + 104, 42)
    c.setFillColor(HexColor("#5f6368")); c.roundRect(ix + iw/2 - 10, T(top + 60), 20, 15, 2, stroke=0, fill=1)
    c.setStrokeColor(YEL); c.setLineWidth(1.4); c.setDash(3, 2)
    c.roundRect(ix + iw/2 - 16, T(top + 66), 32, 27, 4, stroke=1, fill=0); c.setDash()
    c.setFillColor(YEL); c.roundRect(ix + iw/2 + 18, T(top + 52), 40, 11, 3, stroke=0, fill=1)
    c.setFillColor(INK); c.setFont("M", 5.6); c.drawString(ix + iw/2 + 21, T(top + 49.5), "Capacitor?")
    c.setFillColor(HexColor("#202124")); c.rect(ix, T(top + 30), iw, 12, stroke=0, fill=1)
    c.setFillColor(RED); c.circle(ix + 9, T(top + 24), 2.6, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("M", 6); c.drawString(ix + 14, T(top + 26), "FixSaathi · LIVE")
    c.setFont("R", 5.4); c.drawRightString(ix + iw - 6, T(top + 26), "Step 2 of 5")
    c.setFillColor(HexColor("#E6F4EA")); c.roundRect(ix + 6, T(top + 140), iw - 12, 13, 4, stroke=0, fill=1)
    tick(c, ix + 11, top + 130.5, GRN, 5.5)
    c.setFillColor(HexColor("#137333")); c.setFont("M", 5.6); c.drawString(ix + 20, T(top + 136), "Safety: main switch OFF")
    c.setFillColor(white); c.roundRect(ix + 6, T(top + 196), iw - 12, 50, 6, stroke=0, fill=1)
    text(c, ix + 11, top + 150, "Ab capacitor check karein, ye phoola hua lag raha hai. Do wires dhyaan se nikaalein.", "R", 6.1, INK, iw - 22, 7.8)
    c.setFillColor(BLUE)
    for k, hh in enumerate([4, 8, 12, 7, 10, 5, 9, 4]):
        c.roundRect(ix + iw/2 - 18 + k * 4.8, T(top + 207 + hh/2), 2.6, hh, 1.2, stroke=0, fill=1)
    # ---- phone 2: diagnosis
    x = cols[1] + (213.7 - W_) / 2 - 20; phone(c, x, top, W_, H_); ix = x + 4
    text(c, ix + 8, top + 18, "Diagnosis", "M", 8, INK)
    c.setFillColor(HexColor("#e8eaed")); c.roundRect(ix + 6, T(top + 104), iw - 12, 76, 6, stroke=0, fill=1)
    c.setFillColor(HexColor("#5f6368")); c.roundRect(ix + iw/2 - 20, T(top + 82), 40, 30, 4, stroke=0, fill=1)
    c.setFillColor(HexColor("#9aa0a6")); c.roundRect(ix + iw/2 - 12, T(top + 76), 24, 18, 6, stroke=0, fill=1)
    c.setStrokeColor(RED); c.setLineWidth(1.6); c.circle(ix + iw/2, T(top + 67), 19, stroke=1, fill=0)
    c.line(ix + iw/2 + 14, T(top + 54), ix + iw/2 + 30, T(top + 42))
    c.setFillColor(RED); c.roundRect(ix + iw/2 + 12, T(top + 44), 40, 11, 3, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("M", 5.4); c.drawString(ix + iw/2 + 15, T(top + 41.5), "Swollen cap.")
    text(c, ix + 8, top + 110, "Likely causes", "M", 6.6, INK)
    for k, (nm, pct, col) in enumerate([("Capacitor failure", 0.82, RED), ("Winding issue", 0.12, YEL), ("Regulator fault", 0.06, GREY)]):
        yy = top + 124 + k * 17
        c.setFillColor(INK); c.setFont("R", 5.8); c.drawString(ix + 8, T(yy + 5), nm)
        c.setFillColor(HexColor("#e8eaed")); c.roundRect(ix + 8, T(yy + 11), iw - 16, 3.5, 1.5, stroke=0, fill=1)
        c.setFillColor(col); c.roundRect(ix + 8, T(yy + 11), (iw - 16) * pct, 3.5, 1.5, stroke=0, fill=1)
    c.setFillColor(BLUE); c.roundRect(ix + 8, T(top + 200), iw - 16, 18, 9, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("M", 6.4); c.drawCentredString(ix + iw/2, T(top + 193.5), "Guide me: replace capacitor")
    text(c, ix + 8, top + 206, "Not sure? Escalate to senior", "R", 5.6, BLUE, iw - 16)
    # ---- phone 3: report
    x = cols[2] + (213.7 - W_) / 2 - 20; phone(c, x, top, W_, H_); ix = x + 4
    text(c, ix + 8, top + 18, "Service report", "M", 8, INK)
    c.setFillColor(HexColor("#E6F4EA")); c.roundRect(ix + 8, T(top + 44), 72, 12, 6, stroke=0, fill=1)
    tick(c, ix + 13, top + 35, GRN, 5)
    c.setFillColor(HexColor("#137333")); c.setFont("M", 5.6); c.drawString(ix + 21, T(top + 40.5), "Fixed on first visit")
    rows = [("Job", "#FS-1042"), ("Appliance", "Ceiling fan"), ("Fault", "Capacitor failure"), ("Part used", "Capacitor x1"), ("Time on job", "18 min")]
    for k, (a, b) in enumerate(rows):
        yy = top + 52 + k * 15
        c.setFillColor(GREY); c.setFont("R", 5.6); c.drawString(ix + 8, T(yy + 6), a)
        c.setFillColor(INK); c.setFont("M", 5.8); c.drawRightString(ix + iw - 8, T(yy + 6), b)
        c.setStrokeColor(HexColor("#f1f3f4")); c.setLineWidth(0.6); c.line(ix + 8, T(yy + 10), ix + iw - 8, T(yy + 10))
    text(c, ix + 8, top + 130, "Before / after", "M", 6.2, INK)
    for k in range(2):
        c.setFillColor(HexColor("#e8eaed")); c.roundRect(ix + 8 + k * 53, T(top + 180), 49, 38, 4, stroke=0, fill=1)
        fan(c, ix + 32.5 + k * 53, top + 161, 14)
    c.setFillColor(GRN); c.roundRect(ix + 8, T(top + 205), iw - 16, 18, 9, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("M", 6.2); c.drawCentredString(ix + iw/2, T(top + 198.5), "Sent to service centre")
    # ---- captions
    caps = [(RED, "1  Live guidance", "Gemini Live sees the fan and talks the technician through each step in Hinglish, hands-free, with a safety gate first."),
            (BLUE, "2  Visual diagnosis", "Gemini ranks likely causes; Nano Banana circles the faulty part. One tap to start the guided fix or escalate."),
            (GRN, "3  Automatic report", "The report agent writes the job record with photos and saves it to Firestore for the manager dashboard.")]
    for i, (col, t, b) in enumerate(caps):
        px = cols[i] + (213.7 - W_) / 2 - 20 + W_ + 8
        c.setFillColor(col); c.roundRect(px, T(top + 36), 3, 26, 1.5, stroke=0, fill=1)
        text(c, px + 8, top + 10, t, "M", 8.2, INK, 58, 10)
        text(c, px + 8, top + 42, b, "R", 6.9, HexColor("#3c4043"), 60, 9.2)


def s_proto(c):
    heading(c, "Interactive Prototype", "Click-through prototype of the MVP flow. Try it at the link below.")
    W_, H_ = 112, 224
    top = 122
    caps = [("proto/p1.jpg", RED, "1  Safety first", "Gemini Live identifies the fan from the camera and locks every repair step until the technician confirms the power is off."),
            ("proto/p2.jpg", BLUE, "2  Diagnosis", "Likely causes ranked with confidence; the faulty part is marked on the image. One tap to start the guided fix or escalate."),
            ("proto/p3.jpg", GRN, "3  Auto report", "Service report with root cause, parts, safety checks and photos, sent straight to the service-centre dashboard.")]
    for i, (img, col, t, b) in enumerate(caps):
        x = 39 + i * 213.7
        c.drawImage(img, x, T(top + H_), W_, H_, mask="auto")
        px = x + W_ + 10
        c.setFillColor(col); c.roundRect(px, T(top + 36), 3, 26, 1.5, stroke=0, fill=1)
        text(c, px + 8, top + 10, t, "M", 8.2, INK, 70, 10)
        text(c, px + 8, top + 42, b, "R", 6.9, HexColor("#3c4043"), 72, 9.2)
    c.setFillColor(HexColor("#E8F0FE")); c.roundRect(39, T(392), 631, 20, 6, stroke=0, fill=1)
    url = D["proto_url"]
    c.setFillColor(INK); c.setFont("M", 8); c.drawString(49, T(384.5), "Try the prototype:")
    c.setFillColor(BLUE); c.setFont("M", 8); c.drawString(128, T(384.5), url)
    c.linkURL(url, (128, T(389), 128 + pdfmetrics.stringWidth(url, "M", 8), T(378)), relative=0)
    c.setFillColor(GREY); c.setFont("R", 6.6); c.drawRightString(662, T(384.5), "AI responses are scripted in the prototype; the MVP runs them on Gemini Live.")


def s_proof(c):
    heading(c, "Early Proof: Tested on Gemini", "We gave Gemini real photos of our own appliances with the FixSaathi prompt. Summary of its answers:")
    cols = [BLUE, RED, GRN]
    n = len(D["proof"]); cw = (631 - 10 * (n - 1)) / n; ih = (cw - 12) / (2.6 if n == 2 else 2.3)
    for i, (img, title, rows) in enumerate(D["proof"]):
        x = 39 + i * (cw + 10); top = 128
        c.setFillColor(HexColor(TINT[cols[i]])); c.roundRect(x, T(top + 212), cw, 212, 7, stroke=0, fill=1)
        c.drawImage(img, x + 6, T(top + 6 + ih), cw - 12, ih, preserveAspectRatio=False)
        y = text(c, x + 9, top + ih + 12, title, "M", 9, INK, cw - 18)
        for lab, val in rows:
            y = text(c, x + 9, y + 2, lab + ": " + val, "R", 6.8, HexColor("#3c4043"), cw - 18, 8.6)
    c.setFillColor(HexColor("#F1F3F4")); c.roundRect(39, T(386), 631, 40, 6, stroke=0, fill=1)
    text(c, 49, 351, "What this shows: " + D["proof_learn"], "R", 7.6, INK, 612, 9.8)
    text(c, 39, 391, D["proof_note"], "L", 5.8, GREY, 640, 7)



def s_product(c):
    heading(c, "Working Product: Live MVP", "Deployed on Cloud Run. What the technician and the manager see during a real repair.")
    W_, H_ = 104, 208
    top = 122
    shots = [("shots/a_live.png", RED, "Sees + safety", "Gemini Live sees the fan, hears the complaint and blocks repair steps until power is off."),
             ("shots/b_steps.png", BLUE, "Diagnose + guide", "Ranked causes, one step at a time, Nano Banana picture card on any step."),
             ("shots/c_report.png", GRN, "Report + rating", "Service report written by the report agent; technician rates the guidance.")]
    for i, (img, col, t, b) in enumerate(shots):
        x = 39 + i * 132
        c.drawImage(img, x, T(top + H_), W_, H_, preserveAspectRatio=True, anchor='n', mask='auto')
        c.setFillColor(col); c.roundRect(x, T(top + H_ + 12), W_, 3, 1.5, stroke=0, fill=1)
        text(c, x, top + H_ + 16, t, "M", 8, INK, W_)
        text(c, x, top + H_ + 28, b, "R", 6.4, HexColor("#3c4043"), W_ + 18, 8.2)
    dx = 435
    c.drawImage("shots/d_dashboard.png", dx, T(top + 132), 235, 132, preserveAspectRatio=True, anchor='n', mask='auto')
    c.setFillColor(YEL); c.roundRect(dx, T(top + 144), 235, 3, 1.5, stroke=0, fill=1)
    text(c, dx, top + 148, "Manager dashboard (live)", "M", 8, INK, 235)
    text(c, dx, top + 160, "Every job appears as it happens: safety confirmed, unsafe steps blocked, first-time fix, technician-rated accuracy, measured AI cost per repair and reply time.", "R", 6.8, HexColor("#3c4043"), 235, 9)
    text(c, 39, 388, "[FILL] Replace these with screenshots from a real Gemini run on a real fan (tonight).", "M", 7, INK, 630)


def s_traction(c):
    heading(c, "Validation & Traction", "Measured on the live app and tested with real technicians.")
    cols = [BLUE, RED, YEL, GRN]
    cw, gap = 151, 9
    for i, (big, lab) in enumerate(D["traction"]):
        x = 39 + i * (cw + gap)
        c.setFillColor(HexColor(TINT[cols[i]])); c.roundRect(x, T(214), cw, 86, 7, stroke=0, fill=1)
        c.setFillColor(cols[i]); c.roundRect(x, T(132), cw, 4, 2, stroke=0, fill=1)
        text(c, x + 10, 142, big, "B", 19, INK, cw - 20)
        text(c, x + 10, 172, lab, "R", 7.6, HexColor("#3c4043"), cw - 20, 10.2)
    text(c, 39, 230, "In the field", "M", 10)
    y = 248
    for b in D["field"]:
        c.setFillColor(GRN); c.circle(45, T(y + 5.5), 2.4, stroke=0, fill=1)
        y = text(c, 53, y, b, "R", 8.4, HexColor("#3c4043"), 615, 11.4) + 6
    c.setFillColor(HexColor("#F1F3F4")); c.roundRect(39, T(386), 631, 40, 6, stroke=0, fill=1)
    text(c, 49, 352, "How we measure: AI cost from Gemini's token usage at Google's published rates; reply time from end of speech to first audio; accuracy from the technician's thumbs up / down after each job. All shown live on the dashboard.", "R", 7.4, INK, 612, 9.6)


# page plan: (template page index, drawer)
PLAN = [(1, s_cover), (2, s_problem), (3, s_solution), (7, s_product), (7, s_traction), (7, s_proof), (4, s_arch), (5, s_tools), (6, s_models),
        (7, s_market), (7, s_business), (7, s_comp), (7, s_team), (8, None)]

reader = PdfReader("src/template.pdf")
out = PdfWriter()
for idx, fn in PLAN:
    tmp = PdfReader("src/template.pdf")  # fresh copy so duplicated pages are independent
    page = tmp.pages[idx]
    if fn:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(W, H))
        fn(c)
        c.save(); buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
    out.add_page(page)
out.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
with open(sys.argv[2], "wb") as f:
    out.write(f)
print("ok")
