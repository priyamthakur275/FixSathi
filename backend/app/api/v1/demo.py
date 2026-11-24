"""Labelled demo scenarios. A demo session is a normal session (same auth, safety gate, steps and reports) whose AI
responses are scripted sample content. It is offered so the product can be shown when Gemini is unavailable."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from ...core.exceptions import NotFound
from ...db.models import Media, User
from ...db.session import get_db
from ...demo.scenarios import HERE, SCENARIOS, public_list
from ...dependencies import current_user
from ...integrations.storage.local import get_storage, inspect_image
from ...schemas.repair import SessionOut
from ...services import ai
from ...services.sessions import add_message, create_session
from .serializers import session_out

router = APIRouter(tags=['demo'])


class DemoIn(BaseModel):
    scenario: str


@router.get('/demo/scenarios')
def scenarios(_: User = Depends(current_user)):
    return {'label': 'Demo scenarios use scripted sample content written by the FixSaathi team. They are not live AI output.', 'items': public_list()}


@router.post('/demo/sessions', response_model=SessionOut, status_code=201)
async def start(body: DemoIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    sc = SCENARIOS.get(body.scenario)
    if sc is None:
        raise NotFound('Unknown demo scenario.')
    s = create_session(db, u, sc['appliance'], sc['issue'], f"Demo: {sc['title']}")
    s.appliance_details = {**(s.appliance_details or {}), 'demo_scenario': body.scenario}; flag_modified(s, 'appliance_details'); db.flush()
    media_ids = []
    if sc['photo']:
        data = (HERE / sc['photo']).read_bytes(); mime, ext, w, h = inspect_image(data)
        m = Media(session_id=s.id, uploaded_by=u.id, kind='upload', storage_key=get_storage().put(data, ext, f'sessions/{s.id}'), mime_type=mime,
                  size_bytes=len(data), width=w, height=h, meta={'demo': True}); db.add(m); db.flush(); media_ids.append(m.id)
    um = add_message(db, s, 'user', sc['issue'], 'text', {'media_ids': [str(i) for i in media_ids], 'demo': True})
    await ai.chat_reply(db, s, u, sc['issue'], media_ids, exclude_id=um.id)
    db.commit()
    return session_out(db, s)
