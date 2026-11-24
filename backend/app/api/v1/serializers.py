from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import Media, RepairSession, RepairStep, ServiceReport
from ...schemas.repair import MediaOut, SessionOut, StepOut
from ...services.sessions import APPLIANCE_LABELS


def session_out(db: Session, s: RepairSession) -> SessionOut:
    rid = db.scalar(select(ServiceReport.id).where(ServiceReport.session_id == s.id))
    return SessionOut(id=s.id, reference=s.reference, title=s.title, appliance_type=s.appliance_type, appliance_label=APPLIANCE_LABELS.get(s.appliance_type, s.appliance_type),
                      issue_description=s.issue_description, status=s.status, technician_id=s.technician_id, technician_name=s.technician.full_name if s.technician else None,
                      first_time_fix=s.first_time_fix, started_at=s.started_at, completed_at=s.completed_at, report_id=rid,
                      demo=bool((s.appliance_details or {}).get('demo_scenario')))


def media_out(m: Media) -> MediaOut:
    return MediaOut(id=m.id, kind=m.kind, mime_type=m.mime_type, size_bytes=m.size_bytes, width=m.width, height=m.height,
                    url=f'/api/v1/media/{m.id}', meta=m.meta or {}, created_at=m.created_at)


def step_out(x: RepairStep, unlocked: bool) -> StepOut:
    locked = x.requires_power_off and not unlocked and x.status != 'completed'
    return StepOut(id=x.id, step_number=x.step_number, title=x.title, instruction=None if locked else x.instruction, kind=x.kind,
                   requires_power_off=x.requires_power_off, status=x.status, locked=locked, visual_media_id=x.visual_media_id, completed_at=x.completed_at)
