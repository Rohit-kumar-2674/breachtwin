"""A minimal, trusted integration factory with no external database or credentials."""
from fastapi import FastAPI, Header, HTTPException


def create_app():
    app = FastAPI()
    fixtures = {'alice': {'id': 'alice-note', 'owner': 'alice'}, 'bob': {'id': 'bob-note', 'owner': 'bob'}}

    @app.get('/notes/{owner}')
    def read_note(owner: str, x_fixture_user: str = Header(default='')):
        if x_fixture_user not in fixtures:
            raise HTTPException(401)
        if owner != x_fixture_user:
            raise HTTPException(403)
        return fixtures[owner]

    return app
