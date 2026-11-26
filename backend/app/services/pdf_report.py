"""Repair report PDF for one conversation (repair session).

Built only from what is recorded for the session: the reported problem, the latest diagnosis, generated steps, the technician's safety
statements, identified components, escalations, the service report (if one was created) and the conversation itself.
Nothing is invented: a section with no data says so. Power-sensitive step instructions follow the same server rule as the API:
they are printed only when the session's technician has recorded both safety statements (or the step was already completed).
"""
import os, re
from datetime import datetime, timezone
from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..api.v1.serializers import step_out
from ..db.models import Conversation, DiagnosisResult, EscalationRequest, IdentifiedComponent, RepairSession, RepairStep, ServiceReport, User
from . import safety
from .sessions import APPLIANCE_LABELS

EMBLEM = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'emblem.png')
NAVY, TEAL, INK, MUTED, LINE, SOFT = (14, 27, 48), (13, 148, 136), (24, 32, 45), (98, 110, 128), (218, 224, 232), (244, 247, 250)
CRIT, OK, WARN = (190, 50, 50), (22, 128, 82), (166, 104, 0)
STATUS_TEXT = {'created': 'Open', 'active': 'Open', 'diagnosing': 'Diagnosing', 'awaiting_confirmation': 'Awaiting safety confirmation',
               'guidance_in_progress': 'Repair in progress', 'escalated': 'Escalated to a senior technician', 'completed': 'Completed', 'cancelled': 'Closed'}
OUTCOME_TEXT = {'resolved': 'Resolved', 'not_resolved': 'Not resolved', 'escalated': 'Escalated'}
GENERAL_SAFETY = [
    'Switch off the supply at the MCB or isolator before opening any cover, and verify with your own tester that no live line is present.',
    'Capacitors (fans, AC outdoor units, microwaves) can hold a dangerous charge after power-off. Discharge them safely before touching terminals.',
    'Do not bypass safety devices, thermal fuses or earthing. Replace damaged wiring rather than taping it.',
    'Stop and escalate to a senior technician if you see burn marks, smell burning, or are unsure of any step.',
]

_UNICODE = {'‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '...', '•': '-', '→': '->',
            ' ': ' ', '≤': '<=', '≥': '>=', '≈': '~', '×': 'x', '₹': 'Rs ', '✓': 'Yes', '✗': 'No', '°': ' deg '}
_CITATION = re.compile(r'\[([a-z]+:[^\]\s]{1,110})\]')


def clean(text: str | None) -> str:
    """Plain text the PDF's built-in font can print. Text written mostly in a non-Latin script is pointed back to the app instead of printed as '?'."""
    if not text:
        return ''
    t = _CITATION.sub('', str(text))
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'^\s*#{1,6}\s+', '', t, flags=re.M)
    t = ''.join(_UNICODE.get(c, c) for c in t)
    letters = [c for c in t if c.isalpha()]
    foreign = sum(1 for c in letters if ord(c) > 0xFF)
    if letters and foreign / len(letters) > 0.3:
        return '(Written in a non-Latin script. Open this conversation in FixSaathi to read it.)'
    t = t.encode('latin-1', 'replace').decode('latin-1')
    return re.sub(r'[ \t]+([.,;:!?)])', r'\1', re.sub(r'[ \t]{2,}', ' ', t)).strip()


def _date(dt: datetime | str | None) -> str:
    if not dt:
        return '-'
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.astimezone(timezone.utc).strftime('%d %b %Y, %H:%M UTC')


class ReportPDF(FPDF):
    def __init__(self, reference: str):
        super().__init__(format='A4')
        self.reference = reference
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(True, margin=20)
        self.set_title(f'FixSaathi repair report {reference}')
        self.set_author('FixSaathi')
        self.set_creator('FixSaathi')

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('Helvetica', 'B', 8.5); self.set_text_color(*TEAL)
        self.cell(0, 6, 'FixSaathi', new_x=XPos.LMARGIN, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 8.5); self.set_text_color(*MUTED)
        self.cell(0, 6, f'Repair report  |  {self.reference}', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*LINE); self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', '', 8); self.set_text_color(*MUTED)
        self.cell(0, 6, 'AI suggestions are estimates. Verify isolation with your own tester before opening any appliance.', new_x=XPos.LMARGIN, new_y=YPos.TOP)
        self.cell(0, 6, f'Page {self.page_no()} of {{nb}}', align='R')

    # ---- building blocks ----
    def section(self, title: str):
        if self.get_y() > self.h - 50:
            self.add_page()
        self.ln(4)
        self.set_fill_color(*TEAL); self.rect(self.l_margin, self.get_y() + 1.2, 1.4, 5.2, style='F')
        self.set_x(self.l_margin + 4)
        self.set_font('Helvetica', 'B', 12.5); self.set_text_color(*NAVY)
        self.cell(0, 7.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def para(self, text: str, size: float = 10, color=INK, style: str = '', h: float = 5.2):
        self.set_font('Helvetica', style, size); self.set_text_color(*color)
        self.multi_cell(0, h, clean(text), align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def label(self, text: str):
        self.ln(1.5)
        self.set_font('Helvetica', 'B', 9); self.set_text_color(*MUTED)
        self.cell(0, 5.5, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def bullets(self, items: list[str], color=INK):
        self.set_font('Helvetica', '', 10); self.set_text_color(*color)
        for it in items:
            if not clean(it):
                continue
            self.set_x(self.l_margin + 2)
            self.cell(5, 5.2, '-')
            self.multi_cell(0, 5.2, clean(it), align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def none(self, text: str):
        self.para(text, size=9.5, color=MUTED, style='I')

    def table(self, headings: list[str], rows: list[list[str]], widths: tuple):
        head = FontFace(emphasis='BOLD', color=NAVY, fill_color=SOFT, size_pt=9)
        self.set_font('Helvetica', '', 9.5); self.set_text_color(*INK); self.set_draw_color(*LINE); self.set_fill_color(255, 255, 255)
        with super().table(col_widths=widths, headings_style=head, line_height=5.4, padding=(1.6, 2.2), borders_layout='HORIZONTAL_LINES',
                           text_align='LEFT', v_align='TOP', first_row_as_headings=True) as t:
            r = t.row()
            for h in headings:
                r.cell(h)
            for row in rows:
                r = t.row()
                for c in row:
                    r.cell(clean(c) or '-')
        self.ln(2)


def render_session_pdf(db: Session, s: RepairSession, viewer: User) -> bytes:
    diag = db.scalars(select(DiagnosisResult).where(DiagnosisResult.session_id == s.id).order_by(DiagnosisResult.created_at.desc()).limit(1)).first()
    steps = db.scalars(select(RepairStep).where(RepairStep.session_id == s.id).order_by(RepairStep.step_number)).all()
    comps = [c for c in db.scalars(select(IdentifiedComponent).where(IdentifiedComponent.session_id == s.id).order_by(IdentifiedComponent.created_at)) if c.result.get('found')]
    escs = db.scalars(select(EscalationRequest).where(EscalationRequest.session_id == s.id).order_by(EscalationRequest.created_at)).all()
    report = db.scalars(select(ServiceReport).where(ServiceReport.session_id == s.id)).first()
    msgs = [m for m in db.scalars(select(Conversation).where(Conversation.session_id == s.id).order_by(Conversation.created_at))
            if (m.meta or {}).get('action') != 'pdf_report']
    st = safety.current_state(db, s)
    unlocked = st.unlocked and viewer.id == s.technician_id
    appliance = APPLIANCE_LABELS.get(s.appliance_type, s.appliance_type)
    demo = bool((s.appliance_details or {}).get('demo_scenario'))

    pdf = ReportPDF(s.reference)
    pdf.add_page()

    # ---- cover header ----
    pdf.set_fill_color(*NAVY); pdf.rect(0, 0, pdf.w, 46, style='F')
    pdf.set_fill_color(*TEAL); pdf.rect(0, 46, pdf.w, 1.2, style='F')
    if os.path.exists(EMBLEM):
        pdf.set_fill_color(255, 255, 255); pdf.rect(18, 11, 24, 24, style='F', round_corners=True, corner_radius=4)
        pdf.image(EMBLEM, x=20.5, y=13.5, h=19)
    pdf.set_xy(48, 12); pdf.set_font('Helvetica', 'B', 20); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, 'FixSaathi', new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 11); pdf.set_text_color(186, 230, 225)
    pdf.cell(0, 6, 'Appliance Repair Report', new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9); pdf.set_text_color(170, 184, 204)
    pdf.cell(0, 6, f'Generated {_date(datetime.now(timezone.utc))}', new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_y(54)
    pdf.set_font('Helvetica', 'B', 16); pdf.set_text_color(*INK)
    pdf.multi_cell(0, 8, clean(s.title) or f'{appliance} repair', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    if demo:
        pdf.para('Demo scenario: the diagnosis, steps and replies in this session are scripted sample content, not live AI.', size=9.5, color=WARN, style='B')
        pdf.ln(1)

    status = OUTCOME_TEXT.get(report.resolution_status, report.resolution_status) if report else STATUS_TEXT.get(s.status, s.status)
    pdf.table(['Detail', 'Value'], [
        ['Session ID', f'{s.reference}  ({s.id})'], ['Appliance', appliance], ['Technician', s.technician.full_name if s.technician else '-'],
        ['Started', _date(s.started_at)], ['Status', status],
        *([['Service report', f'{report.reference}, created {_date(report.created_at)}']] if report else []),
    ], widths=(32, 130))

    # ---- 1. problem ----
    pdf.section('Reported problem')
    first_user = next((m.message for m in msgs if m.role == 'user' and m.message.strip()), '')
    if s.issue_description or first_user:
        pdf.para(s.issue_description or first_user)
    else:
        pdf.none('No problem description was recorded.')

    # ---- 2. diagnosis ----
    pdf.section('AI diagnosis and suspected causes')
    if diag:
        pdf.para(diag.problem_summary)
        coverage = {'grounded': 'Backed by FixSaathi repair records.', 'partial': 'Partly backed by FixSaathi repair records.',
                    'none': 'No matching repair record: treat as unverified.'}.get(diag.knowledge_coverage, '')
        if coverage:
            pdf.para(coverage, size=9, color=MUTED, style='I')
        if diag.faults:
            pdf.ln(1)
            basis = {'supported_by_records': 'From repair records', 'possible_cause': 'Possible cause', 'unverified_hypothesis': 'Unverified'}
            pdf.table(['Suspected cause', 'AI estimate', 'Basis', 'Why'], [
                [f.get('fault', ''), f"{round(float(f.get('confidence', 0)) * 100)}%", basis.get(f.get('status', ''), '-'), f.get('explanation', '')]
                for f in diag.faults], widths=(42, 22, 28, 82))
        if diag.confirmed_findings:
            pdf.label('Confirmed findings'); pdf.bullets(diag.confirmed_findings)
        if diag.recommended_checks:
            pdf.label('Recommended checks'); pdf.bullets(diag.recommended_checks)
        if diag.missing_information:
            pdf.label('Still unknown'); pdf.bullets(diag.missing_information)
        pdf.para(f'Diagnosed {_date(diag.created_at)} by {diag.model_identifier}. Confidence values are model estimates, not measurements.', size=8.5, color=MUTED)
    else:
        latest = next((m.message for m in reversed(msgs) if m.role == 'assistant' and m.message.strip()), '')
        if latest:
            pdf.none('No structured diagnosis was run. The latest guidance from the conversation:')
            pdf.ln(1); pdf.para(latest)
        else:
            pdf.none('No diagnosis has been made in this conversation yet.')

    # ---- 3. procedure ----
    pdf.section('Recommended repair procedure')
    if steps:
        rows = []
        for x in steps:
            o = step_out(x, unlocked)
            text = o.instruction if not o.locked else ('Withheld: this step needs the power off. Record both safety statements in FixSaathi '
                                                         '(power off at the MCB, tester shows no live line) to see it.')
            rows.append([str(x.step_number), f'{x.title}{"  [POWER OFF]" if x.requires_power_off else ""}\n{text}',
                         {'completed': 'Done', 'skipped': 'Skipped'}.get(x.status, 'Not done')])
        pdf.table(['#', 'Step', 'Status'], rows, widths=(9, 140, 25))
        pdf.para('Steps marked "Not done" were not confirmed as performed by the technician.', size=8.5, color=MUTED)
    else:
        pdf.none('No repair steps were generated for this conversation. Open the repair workspace in FixSaathi to generate them after a diagnosis.')

    # ---- 4. safety warnings ----
    pdf.section('Safety warnings')
    if diag and diag.safety_requirements:
        pdf.label('For this fault'); pdf.bullets(diag.safety_requirements, color=CRIT)
    if s.appliance_type == 'microwave_oven':
        pdf.bullets(['Microwave ovens hold lethal voltage in the high-voltage capacitor even when unplugged. Cabinet-open work is for authorised service only.'], color=CRIT)
    pdf.label('General'); pdf.bullets(GENERAL_SAFETY)

    # ---- 5. safety status ----
    pdf.section('Safety verification status')
    yes = lambda b: 'Stated by technician' if b else 'Not recorded'  # noqa: E731
    pdf.table(['Safety statement', 'Status'], [
        ['Power switched off at the MCB or isolator', yes(st.power_off_confirmed)],
        ['Own tester showed no live line', yes(st.tester_checked)],
        ['Power-sensitive steps', 'Unlocked' if st.unlocked else ('Locked (statements expired)' if st.expired else 'Locked')],
        *([['Statements recorded at', _date(st.confirmed_at)]] if st.confirmed_at else []),
    ], widths=(100, 74))
    pdf.para(safety.DISCLAIMER, size=8.5, color=MUTED)

    # ---- 6. parts ----
    pdf.section('Parts and components')
    if comps or (diag and diag.required_tools):
        if comps:
            pdf.table(['Component identified on a photo', 'Notes'], [[c.result.get('component_name') or '-', c.result.get('explanation') or ''] for c in comps], widths=(60, 114))
            pdf.para('Identified visually from photos only; not measured or tested.', size=8.5, color=MUTED)
        if diag and diag.required_tools:
            pdf.label('Tools needed'); pdf.bullets(diag.required_tools)
    else:
        pdf.none('No parts or components were identified in this conversation.')

    # ---- 7. escalation ----
    pdf.section('Escalation')
    if escs or (diag and diag.requires_escalation):
        if diag and diag.requires_escalation:
            pdf.para(f'The AI recommended a senior technician for this fault.{(" " + diag.escalation_reason) if diag.escalation_reason else ""}', color=WARN)
        if escs:
            pdf.table(['Requested', 'Reason', 'Priority', 'Status'], [[_date(e.created_at), e.reason, e.priority.capitalize(), e.status.replace('_', ' ').capitalize()]
                                                                     for e in escs], widths=(38, 86, 22, 28))
    else:
        pdf.none('No escalation was requested.')

    # ---- 8. final notes ----
    pdf.section('Final notes')
    if report:
        r = report.report_data or {}
        res = r.get('resolution') or {}
        pdf.para(f"Outcome: {OUTCOME_TEXT.get(res.get('outcome', ''), res.get('outcome') or '-')}"
                 f"{'. Fixed on the first visit.' if res.get('first_time_fix') else ''}")
        if res.get('notes'):
            pdf.para(f"Technician notes: {res['notes']}")
    else:
        pdf.para('This is a snapshot of an open conversation. It does not confirm that the repair was completed, and no service report has been '
                 'finalised yet.', color=MUTED)
    pdf.para('FixSaathi uses Google Gemini grounded in curated repair records. AI suggestions can be wrong: check every step before acting.', size=8.5, color=MUTED)

    sources = (diag.sources if diag else None) or []
    if sources:
        pdf.label('Repair record sources')
        pdf.bullets([f"{x.get('source_name', '')} ({x.get('record_id', '')})" for x in sources[:8]], color=MUTED)

    # ---- appendix: conversation ----
    talk = [m for m in msgs if m.role in ('user', 'assistant') and m.message.strip()][-40:]
    if talk:
        pdf.add_page()
        pdf.section('Conversation')
        for m in talk:
            who = 'Technician' if m.role == 'user' else 'FixSaathi'
            pdf.set_font('Helvetica', 'B', 9); pdf.set_text_color(*(INK if m.role == 'user' else TEAL))
            pdf.cell(pdf.get_string_width(who) + 3, 5.5, who, new_x=XPos.END, new_y=YPos.TOP)
            pdf.set_font('Helvetica', '', 8); pdf.set_text_color(*MUTED)
            pdf.cell(0, 5.5, _date(m.created_at), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.para(m.message, size=9.5, h=4.9)
            pdf.ln(2.5)
    return bytes(pdf.output())
