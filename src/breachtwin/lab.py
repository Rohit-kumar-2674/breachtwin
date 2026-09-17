"""Synthetic lab. Factories only: no globally exposed ASGI app or network server."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException


def create_app(*, fixed: bool) -> FastAPI:
    app = FastAPI(title="BreachTwin synthetic lab", docs_url=None, redoc_url=None)
    members = {
        "alice": {"organization": "alpha", "role": "member", "active": True},
        "bob": {"organization": "bravo", "role": "member", "active": True},
        "maya": {"organization": "alpha", "role": "member", "active": True},
        "admin": {"organization": "alpha", "role": "admin", "active": True},
    }
    records = {
        "doc-alpha": {"id": "doc-alpha", "organization": "alpha", "content": "SYNTHETIC ALPHA RECORD"},
        "doc-bravo": {"id": "doc-bravo", "organization": "bravo", "content": "SYNTHETIC BRAVO RECORD"},
    }
    reports = []

    def principal(name):
        user = members.get(name)
        if user is None:
            raise HTTPException(401, "Unknown synthetic user")
        # Fix BT-002: consult current membership on each protected request.
        if fixed and not user["active"]:
            raise HTTPException(403, "Membership revoked")
        return user

    @app.get("/records/{record_id}")
    def get_record(record_id: str, x_lab_user: str = Header(default="")):
        user = principal(x_lab_user)
        record = records.get(record_id)
        if record is None:
            raise HTTPException(404, "Record not found")
        # Fix BT-001: scope access to the principal's organization.
        if fixed and record["organization"] != user["organization"]:
            raise HTTPException(403, "Outside organization")
        return record

    @app.post("/admin/members/{name}/revoke")
    def revoke(name: str, x_lab_user: str = Header(default="")):
        user = principal(x_lab_user)
        if user["role"] != "admin":
            raise HTTPException(403, "Administrator required")
        if name not in members:
            raise HTTPException(404, "Member not found")
        members[name]["active"] = False
        return {"revoked": True, "member": name}

    @app.post("/admin/reports", status_code=201)
    def create_report(x_lab_user: str = Header(default="")):
        user = principal(x_lab_user)
        # Fix BT-003: authorize the action on the server.
        if fixed and user["role"] != "admin":
            raise HTTPException(403, "Administrator required")
        reports.append({"created_by": x_lab_user})
        return {"created": True, "created_by": x_lab_user, "count": len(reports)}

    return app


def create_vulnerable_app() -> FastAPI:
    return create_app(fixed=False)


def create_fixed_app() -> FastAPI:
    return create_app(fixed=True)
