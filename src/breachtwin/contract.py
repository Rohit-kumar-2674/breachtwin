"""Strict, portable contracts. No scripts or factory imports in contract files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnvRef(StrictModel):
    env: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")


class Actor(StrictModel):
    headers: dict[str, str | EnvRef] = Field(default_factory=dict)

    @field_validator("headers")
    @classmethod
    def safe_headers(cls, values):
        for name, value in values.items():
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                raise ValueError("Invalid HTTP header name")
            if name.lower() in {"host", "content-length", "transfer-encoding"}:
                raise ValueError("Transport headers cannot be overridden")
            if isinstance(value, str):
                if "\r" in value or "\n" in value:
                    raise ValueError("Header values cannot contain newlines")
                if any(k in name.lower() for k in ("authorization", "cookie", "token", "api-key", "apikey", "secret")):
                    raise ValueError("Credential headers must use an environment reference")
        return values


class Assertion(StrictModel):
    status: list[int] = Field(default_factory=list)
    json_equals: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.status and not self.json_equals:
            raise ValueError("An assertion needs status codes or JSON equality checks")
        if any(s < 100 or s > 599 for s in self.status):
            raise ValueError("Invalid HTTP status code")
        if any(not k or any(not part for part in k.split('.')) for k in self.json_equals):
            raise ValueError("JSON paths use nonempty dot-separated keys")
        return self


class Step(StrictModel):
    name: str = Field(min_length=1, max_length=180)
    kind: Literal["control", "setup", "probe"]
    actor: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    path: str = Field(min_length=1, max_length=2048)
    body: dict | list | None = None
    expect: Assertion
    violation: Assertion | None = None

    @field_validator("path")
    @classmethod
    def local_path(cls, path):
        if not path.startswith('/') or path.startswith('//') or '\\' in path:
            raise ValueError("Only application-relative paths beginning with / are allowed")
        if any(ord(c) < 32 or ord(c) == 127 for c in path) or '#' in path:
            raise ValueError("Path contains a control character or fragment")
        return path

    @model_validator(mode="after")
    def probe_proof(self):
        if (self.kind == "probe") != (self.violation is not None):
            raise ValueError("Exactly probe steps must define a violation assertion")
        if self.kind == "probe" and not self.violation.json_equals:
            raise ValueError("A probe requires JSON evidence; a success status alone is insufficient")
        return self


class Experiment(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=180)
    rule: str = Field(min_length=1, max_length=1000)
    cwe: str = Field(pattern=r"^CWE-[0-9]+$")
    remediation: str = Field(min_length=1, max_length=2000)
    steps: list[Step] = Field(min_length=2, max_length=32)

    @model_validator(mode="after")
    def controls_first(self):
        kinds = [s.kind for s in self.steps]
        if kinds[0] != "control" or "probe" not in kinds or kinds[-1] != "control":
            raise ValueError("Start and end with a positive control; include a probe between them")
        if len({s.name for s in self.steps}) != len(self.steps):
            raise ValueError("Step names must be unique within an experiment")
        return self


class Contract(StrictModel):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(max_length=2000)
    actors: dict[str, Actor] = Field(min_length=1, max_length=64)
    experiments: list[Experiment] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def relationships(self):
        ids = [e.id for e in self.experiments]
        if len(ids) != len(set(ids)):
            raise ValueError("Experiment IDs must be unique")
        for exp in self.experiments:
            for step in exp.steps:
                if step.actor not in self.actors:
                    raise ValueError("Step refers to an undefined actor")
        return self


def load_contract(path: str | Path) -> Contract:
    raw = Path(path).read_bytes()
    if len(raw) > 1_048_576:
        raise ValueError("Contract exceeds the 1 MiB limit")
    return Contract.model_validate(json.loads(raw))
