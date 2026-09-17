"""Controlled failure modes used to challenge the verdict engine."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from breachtwin.lab import create_fixed_app

STARTUPS = 0
SHUTDOWNS = 0


def create_outage():
    app = FastAPI()

    @app.api_route('/{path:path}', methods=['GET', 'POST'])
    def down(path: str):
        return JSONResponse({'detail': 'Service unavailable'}, status_code=503)

    return app


def create_deny_everything():
    app = FastAPI()

    @app.api_route('/{path:path}', methods=['GET', 'POST'])
    def deny(path: str):
        return JSONResponse({'detail': 'Forbidden'}, status_code=403)

    return app


def modified_app(mode):
    app = create_fixed_app()

    @app.middleware('http')
    async def alter(request: Request, call_next):
        probe = request.url.path == '/records/doc-bravo' and request.headers.get('x-lab-user') == 'alice'
        if probe and mode == 'error':
            return JSONResponse({'detail': 'Unexpected database failure'}, status_code=500)
        if probe and mode == 'wrong':
            return JSONResponse({'id': 'doc-alpha', 'organization': 'alpha'})
        if probe and mode == 'leak':
            return JSONResponse({'id': 'doc-bravo', 'organization': 'bravo', 'content': 'SYNTHETIC BRAVO RECORD'}, status_code=403)
        if probe and mode == 'redirect':
            return JSONResponse({}, status_code=302, headers={'Location': 'https://example.invalid'})
        if mode == 'setup' and request.url.path.endswith('/revoke'):
            return JSONResponse({'detail': 'Revocation service failed'}, status_code=500)
        response = await call_next(request)
        if mode == 'cookies' and request.url.path == '/admin/reports' and request.headers.get('x-lab-user') == 'admin':
            response.set_cookie('session', 'admin-SESSION-SECRET')
        if mode == 'cookies' and request.headers.get('x-lab-user') == 'alice' and request.cookies.get('session'):
            return JSONResponse({'created': True, 'created_by': 'alice'}, status_code=201)
        return response

    return app


def create_error():
    return modified_app('error')


def create_wrong_record():
    return modified_app('wrong')


def create_leak_with_denial():
    return modified_app('leak')


def create_failed_setup():
    return modified_app('setup')


def create_redirect():
    return modified_app('redirect')


def create_cookie_fixture():
    return modified_app('cookies')


def create_lifecycle_app():
    @asynccontextmanager
    async def lifecycle(app):
        global STARTUPS, SHUTDOWNS
        STARTUPS += 1
        yield
        SHUTDOWNS += 1
    app = create_fixed_app()
    app.router.lifespan_context = lifecycle
    return app


def create_credential_fixture():
    app = create_fixed_app()

    @app.middleware('http')
    async def check(request, call_next):
        if request.headers.get('authorization') != 'Bearer synthetic-SECRET-947':
            return JSONResponse({'detail': 'Missing token'}, status_code=401)
        response = await call_next(request)
        response.headers['X-Secret'] = 'response-SECRET-947'
        return response

    return app


def create_lifecycle_failure():
    @asynccontextmanager
    async def fail(app):
        raise RuntimeError('This text might contain a secret and must not be recorded')
        yield
    return FastAPI(lifespan=fail)
