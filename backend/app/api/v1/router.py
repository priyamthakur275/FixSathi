from fastapi import APIRouter
from . import auth, demo, evaluation, live, lookup, records, sessions, workflow

api = APIRouter(prefix='/api/v1')
for r in (auth.router, auth.users, sessions.router, workflow.router, records.router, live.router, demo.router, lookup.router, evaluation.router):
    api.include_router(r)
