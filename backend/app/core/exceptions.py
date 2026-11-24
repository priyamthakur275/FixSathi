import logging
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status = 400
    code = 'BAD_REQUEST'

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.status = status or self.status
        self.details = details or {}


class NotFound(AppError): status, code = 404, 'NOT_FOUND'
class Forbidden(AppError): status, code = 403, 'FORBIDDEN'
class Unauthorized(AppError): status, code = 401, 'UNAUTHORIZED'
class Conflict(AppError): status, code = 409, 'CONFLICT'
class RateLimited(AppError): status, code = 429, 'RATE_LIMITED'
class AIUnavailable(AppError): status, code = 503, 'AI_NOT_CONFIGURED'
class AIError(AppError): status, code = 502, 'AI_ERROR'


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {'error': {'code': code, 'message': message, 'details': details or {}}}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app(_: Request, e: AppError):
        return JSONResponse(error_body(e.code, e.message, e.details), status_code=e.status)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, e: IntegrityError):
        # e.g. two registrations with the same email at the same moment: a clean 409, never a 500
        logging.getLogger('app').warning('integrity_error: %s', str(e.orig).splitlines()[0] if e.orig else e)
        return JSONResponse(error_body('CONFLICT', 'That conflicts with existing data. Refresh and try again.'), status_code=409)

    @app.exception_handler(OperationalError)
    async def _db_down(_: Request, e: OperationalError):
        logging.getLogger('app').error('database_unavailable: %s', str(e.orig).splitlines()[0] if e.orig else e)
        return JSONResponse(error_body('DATABASE_UNAVAILABLE', 'The database is not reachable right now. Try again in a moment.'), status_code=503)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, e: Exception):
        # Always JSON, never a stack trace or a plain-text page the app cannot read.
        logging.getLogger('app').exception('unhandled_error path=%s', request.url.path)
        return JSONResponse(error_body('INTERNAL_ERROR', 'Something went wrong on the server. Please try again.'), status_code=500)

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        errs = [{'loc': list(x.get('loc', [])), 'msg': x.get('msg')} for x in e.errors()]
        return JSONResponse(error_body('VALIDATION_ERROR', 'Invalid request', {'errors': errs}), status_code=422)
