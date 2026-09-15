"""
Deployment hardening: configuration/secret validation, shared HTTP Basic auth on every
browser-facing route, secret redaction, and the small runtime limits a 1 vCPU VM needs.
No LLM calls; the MCP server and runtime are real (fixture data).
"""
import base64
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from phase3 import config as cfg
from phase3.agent import base
from phase3.agent.base import server_params
from phase3.auth import BasicAuthMiddleware
from phase3.config import ConfigError, Settings, redact
from phase3.server import create_app

PHASE3 = Path(__file__).resolve().parents[1]
FIXTURE_DATA = PHASE3.parent / "phase2" / "tests" / "fixtures" / "data"

KEY = "sk-ant-api03-EXAMPLEEXAMPLEEXAMPLE"
PASSWORD = "correct-horse-battery-staple"
DEPLOY_ENV = {"NORDFLOW_MODE": "deploy", "ANTHROPIC_API_KEY": KEY,
              "NORDFLOW_AUTH_USER": "board", "NORDFLOW_AUTH_PASSWORD": PASSWORD}
CREDS = {"Authorization": "Basic " + base64.b64encode(f"board:{PASSWORD}".encode()).decode()}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("NORDFLOW_DATA_DIR", str(FIXTURE_DATA))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NORDFLOW_AUTH_PASSWORD", raising=False)
    monkeypatch.setattr(base, "LOG_DIR", tmp_path / "logs")


class FakeAgent:
    def __init__(self, boom=None):
        self.boom = boom

    def info(self):
        return {"mode": "fake", "model": "none", "effort": "none"}

    async def ask(self, conv, turn, emit):
        if self.boom:
            raise RuntimeError(self.boom)
        turn.answer = {"headline": "ok", "evidence": []}
        return base.finish_turn(conv, turn, self.info())


def app_with(env, agent=None):
    return create_app(agent_factory=lambda mcp: agent or FakeAgent(), settings=Settings.from_env(env))


# -- configuration validation ------------------------------------------------

def test_deploy_mode_requires_api_mode_key_and_credentials():
    problems = " ".join(Settings.from_env({"NORDFLOW_MODE": "deploy"}).problems())
    assert "No model provider is configured" in problems and "OPENAI_API_KEY" in problems
    assert any(p.startswith("ANTHROPIC_API_KEY is not set")
               for p in Settings.from_env({"NORDFLOW_MODE": "deploy", "NORDFLOW_AGENT": "api"}).problems())
    assert "NORDFLOW_AUTH_USER is not set" in problems and "NORDFLOW_AUTH_PASSWORD is not set" in problems

    cli = Settings.from_env({**DEPLOY_ENV, "NORDFLOW_AGENT": "cli"})
    assert any("NORDFLOW_AGENT=cli is not supported" in p for p in cli.problems())

    good = Settings.from_env(DEPLOY_ENV)
    assert good.problems() == [] and good.agent == "api" and good.auth_required


def test_deploy_mode_refuses_weak_password_public_bind_and_bad_values():
    weak = Settings.from_env({**DEPLOY_ENV, "NORDFLOW_AUTH_PASSWORD": "short"})
    assert any("shorter than 12 characters" in p for p in weak.problems())

    public = Settings.from_env({**DEPLOY_ENV, "NORDFLOW_HOST": "0.0.0.0"})
    assert any("clear text" in p for p in public.problems())
    assert Settings.from_env({**DEPLOY_ENV, "NORDFLOW_HOST": "0.0.0.0",
                              "NORDFLOW_ALLOW_PUBLIC_BIND": "1"}).problems() == []

    bad = Settings.from_env({**DEPLOY_ENV, "NORDFLOW_EFFORT": "turbo", "NORDFLOW_PORT": "eight"})
    assert len(bad.problems()) == 2

    with pytest.raises(ConfigError) as exc:
        Settings.from_env({"NORDFLOW_MODE": "deploy"}).check()
    assert "OPENAI_API_KEY" in exc.value.report() and "phase3/DEPLOY.md" in exc.value.report()


def test_local_mode_still_runs_without_secrets_but_half_credentials_are_rejected():
    local = Settings.from_env({"NORDFLOW_AGENT": "cli"})
    assert local.problems() == [] and local.auth_required is False
    assert any("NORDFLOW_AUTH_PASSWORD is not set" in p
               for p in Settings.from_env({"NORDFLOW_AUTH_USER": "board", "NORDFLOW_AGENT": "cli"}).problems())


def test_secrets_never_appear_in_summary_repr_or_messages(monkeypatch):
    s = Settings.from_env(DEPLOY_ENV)
    assert KEY not in repr(s) and PASSWORD not in repr(s)
    assert json.dumps(s.summary()) == json.dumps(s.summary()).replace(KEY, "!").replace(PASSWORD, "!")
    assert s.summary()["api_key"] == "ANTHROPIC_API_KEY set" and s.summary()["auth"] == "basic"
    assert s.without_secrets().api_key is None and s.without_secrets().auth_password is None
    assert s.redact(f"401 from api: key {KEY} rejected") == "401 from api: key [redacted] rejected"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "other-key-value-1234")
    assert "other-key-value-1234" not in redact("connect failed with other-key-value-1234")


def test_mcp_subprocess_does_not_inherit_credentials(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("NORDFLOW_AUTH_PASSWORD", PASSWORD)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-EXAMPLEexample0123456789")
    env = server_params().env
    assert not {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "NORDFLOW_AUTH_PASSWORD"} & env.keys()
    assert KEY not in json.dumps(env) and env["NORDFLOW_DATA_DIR"] == str(FIXTURE_DATA)


# -- HTTP Basic auth ---------------------------------------------------------

def test_basic_auth_guards_every_browser_facing_route():
    with TestClient(app_with(DEPLOY_ENV)) as client:
        for path in ("/", "/static/app.js", "/api/config", "/api/conversations/x"):
            res = client.get(path)
            assert res.status_code == 401, path
            assert res.headers["www-authenticate"].startswith('Basic realm="NordFlow demo"')
        assert client.post("/api/conversations").status_code == 401
        assert client.get("/", headers={"Authorization": "Basic " + base64.b64encode(b"board:wrong").decode()}).status_code == 401
        assert client.get("/", headers={"Authorization": "Bearer " + PASSWORD}).status_code == 401
        assert client.get("/", headers={"Authorization": "Basic not-base64!"}).status_code == 401

        assert client.get("/healthz").status_code == 200          # open for the reverse proxy
        assert client.get("/healthz").json() == {"status": "ok"}
        assert "board" not in client.get("/healthz").text

        assert client.get("/", headers=CREDS).status_code == 200
        body = client.get("/api/config", headers=CREDS).text
        assert "e-conomic" in body and KEY not in body and PASSWORD not in body


def test_no_auth_middleware_in_local_mode():
    with TestClient(app_with({"NORDFLOW_AGENT": "cli"})) as client:
        assert client.get("/").status_code == 200 and client.get("/api/config").status_code == 200


def test_auth_comparison_accepts_only_the_exact_pair():
    mw = BasicAuthMiddleware(lambda *a: None, "board", PASSWORD)
    assert mw.authorized("Basic " + base64.b64encode(f"board:{PASSWORD}".encode()).decode())
    assert not mw.authorized("Basic " + base64.b64encode(f"Board:{PASSWORD}".encode()).decode())
    assert not mw.authorized("Basic " + base64.b64encode(f"board:{PASSWORD}x".encode()).decode())
    assert not mw.authorized(None) and not mw.authorized("Basic")
    with pytest.raises(ValueError):
        BasicAuthMiddleware(lambda *a: None, "board", "")


# -- runtime limits and leak-proof errors ------------------------------------

def test_errors_reaching_the_browser_and_the_log_are_redacted():
    app = app_with(DEPLOY_ENV, agent=FakeAgent(boom=f"upstream refused key {KEY}"))
    with TestClient(app) as client:
        cid = client.post("/api/conversations", headers=CREDS).json()["id"]
        with client.stream("POST", f"/api/conversations/{cid}/ask", headers=CREDS, json={"question": "hi"}) as r:
            body = "".join(r.iter_text())
    assert KEY not in body and "[redacted]" in body


def test_turn_errors_are_redacted_before_logging():
    conv, turn = base.Conversation(), base.Turn("q")
    turn.errors.append(f"APIStatusError: invalid x-api-key {KEY}")
    record = base.finish_turn(conv, turn, {"mode": "fake"})
    log = (base.LOG_DIR / f"{conv.id}.jsonl").read_text()
    assert KEY not in record["errors"][0] and KEY not in log and "[redacted]" in log


def test_runtime_limits_keep_a_small_vm_bounded():
    app = app_with({**DEPLOY_ENV, "NORDFLOW_MAX_CONVERSATIONS": "2", "NORDFLOW_MAX_QUESTION_CHARS": "60"})
    with TestClient(app) as client:
        ids = [client.post("/api/conversations", headers=CREDS).json()["id"] for _ in range(3)]
        assert client.get(f"/api/conversations/{ids[0]}", headers=CREDS).status_code == 404   # oldest evicted
        assert client.get(f"/api/conversations/{ids[2]}", headers=CREDS).status_code == 200
        long = client.post(f"/api/conversations/{ids[2]}/ask", headers=CREDS, json={"question": "x" * 61})
        assert long.status_code == 413
        assert client.post(f"/api/conversations/{ids[2]}/ask", headers=CREDS, content=b"not json").status_code == 400
        assert client.get("/api/config", headers=CREDS).headers["cache-control"] == "no-store"


def test_create_app_refuses_to_start_without_the_api_key():
    with pytest.raises(ConfigError) as exc:
        create_app(settings=Settings.from_env({k: v for k, v in DEPLOY_ENV.items() if k != "ANTHROPIC_API_KEY"}))
    assert "No model provider is configured" in str(exc.value)
    assert cfg.MIN_PASSWORD_CHARS == 12
