"""
Configuration and secret handling for the demo server.

Everything comes from environment variables; no secret is ever read from the
repository, written to a log, or returned in a response.

    NORDFLOW_MODE=local    single user on a laptop (default). Auth optional, CLI agent allowed.
    NORDFLOW_MODE=deploy   small private remote deployment: an API agent (Anthropic `api` or
                           `openai`), its key and HTTP Basic auth are all required, and the
                           checks below refuse to start without them.
"""
import os
import re
import shutil
from dataclasses import dataclass, field, replace

EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODES = ("local", "deploy")
AGENTS = ("auto", "api", "openai", "cli")
DEFAULT_MODELS = {"api": "claude-opus-5", "cli": "claude-opus-5", "openai": "gpt-5.6-sol"}
KEY_VARS = {"api": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
MIN_PASSWORD_CHARS = 12
LOOPBACK = ("127.0.0.1", "::1", "localhost")
# Anthropic (sk-ant-...) and OpenAI (sk-proj-..., sk-svcacct-..., sk-...) key shapes
SECRET_PATTERN = re.compile(r"(?<![A-Za-z0-9])sk-(?:ant-|proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{16,}")
MASK = "[redacted]"


class ConfigError(RuntimeError):
    """Raised when required configuration or secrets are missing or unusable."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))

    def report(self):
        lines = ["Cannot start the NordFlow demo - configuration problems:"]
        lines += [f"  * {p}" for p in self.problems]
        lines.append("See phase3/DEPLOY.md for the required environment variables.")
        return "\n".join(lines)


@dataclass(frozen=True)
class Settings:
    mode: str = "local"
    requested_agent: str = "auto"
    agent: str = "api"
    model: str = "claude-opus-5"
    effort: str = "medium"
    host: str = "127.0.0.1"
    port: int = 8765
    max_conversations: int = 50
    max_question_chars: int = 2000
    allow_public_bind: bool = False
    data_dir: str | None = None
    auth_user: str | None = field(default=None, repr=False)
    auth_password: str | None = field(default=None, repr=False)
    api_key: str | None = field(default=None, repr=False)          # key of the selected provider
    other_secrets: tuple = field(default=(), repr=False)           # every provider key found, for redaction
    openai_key_seen: bool = False
    parse_problems: tuple = ()

    # -- construction ----------------------------------------------------

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        problems = []

        def integer(name, default, low, high):
            raw = env.get(name, "").strip()
            if not raw:
                return default
            try:
                value = int(raw)
            except ValueError:
                problems.append(f"{name} must be a whole number, got '{raw}'.")
                return default
            if not low <= value <= high:
                problems.append(f"{name} must be between {low} and {high}, got {value}.")
                return default
            return value

        mode = (env.get("NORDFLOW_MODE") or "local").strip().lower()
        requested = (env.get("NORDFLOW_AGENT") or "auto").strip().lower()
        anthropic_key = (env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or "").strip() or None
        openai_key = (env.get("OPENAI_API_KEY") or "").strip() or None
        agent = requested
        if agent == "auto":  # openai is never picked implicitly: a stray OPENAI_API_KEY must not start paid calls
            agent = "api" if (anthropic_key or mode == "deploy" or not shutil.which("claude")) else "cli"
        password = env.get("NORDFLOW_AUTH_PASSWORD") or None
        return cls(
            mode=mode, requested_agent=requested, agent=agent,
            model=(env.get("NORDFLOW_MODEL") or DEFAULT_MODELS.get(agent, DEFAULT_MODELS["api"])).strip(),
            effort=(env.get("NORDFLOW_EFFORT") or "medium").strip().lower(),
            host=(env.get("NORDFLOW_HOST") or "127.0.0.1").strip(),
            port=integer("NORDFLOW_PORT", 8765, 1, 65535),
            max_conversations=integer("NORDFLOW_MAX_CONVERSATIONS", 50, 1, 10_000),
            max_question_chars=integer("NORDFLOW_MAX_QUESTION_CHARS", 2000, 50, 20_000),
            allow_public_bind=(env.get("NORDFLOW_ALLOW_PUBLIC_BIND") or "").strip().lower() in ("1", "true", "yes"),
            data_dir=(env.get("NORDFLOW_DATA_DIR") or "").strip() or None,
            auth_user=(env.get("NORDFLOW_AUTH_USER") or "").strip() or None,
            auth_password=password,
            api_key=openai_key if agent == "openai" else anthropic_key,
            other_secrets=tuple(k for k in (anthropic_key, openai_key) if k),
            openai_key_seen=openai_key is not None,
            parse_problems=tuple(problems),
        )

    # -- validation ------------------------------------------------------

    @property
    def auth_required(self):
        return self.mode == "deploy" or self.auth_user is not None or self.auth_password is not None

    def problems(self, check_agent_credentials=True):
        """Every configuration problem at once, so one restart shows all of them."""
        out = list(self.parse_problems)
        if self.mode not in MODES:
            out.append(f"NORDFLOW_MODE must be one of {', '.join(MODES)}, got '{self.mode}'.")
        if self.requested_agent not in AGENTS:
            out.append(f"NORDFLOW_AGENT must be one of {', '.join(AGENTS)}, got '{self.requested_agent}'.")
        if self.effort not in EFFORTS:
            out.append(f"NORDFLOW_EFFORT must be one of {', '.join(EFFORTS)}, got '{self.effort}'.")

        deploy = self.mode == "deploy"
        if deploy and self.requested_agent == "cli":
            out.append("NORDFLOW_AGENT=cli is not supported for a deployment: the CLI agent depends on an "
                       "interactive Claude Code login on the machine. Use NORDFLOW_AGENT=openai or api.")
        if check_agent_credentials and self.agent in KEY_VARS and not self.api_key:
            where = ("keep it in the server's environment file only (never in the repository, the browser "
                     "or a log).")
            if self.requested_agent == "auto":
                hint = (" OPENAI_API_KEY is set, but the OpenAI agent is only used when chosen explicitly."
                        if self.openai_key_seen else "")
                out.append("No model provider is configured. Set NORDFLOW_AGENT=openai with OPENAI_API_KEY, or "
                           f"NORDFLOW_AGENT=api with ANTHROPIC_API_KEY; {where}{hint}")
            else:
                out.append(f"{KEY_VARS[self.agent]} is not set. NORDFLOW_AGENT={self.agent} needs it; {where}")

        if self.auth_required:
            if not self.auth_user:
                out.append("NORDFLOW_AUTH_USER is not set. Browser access requires HTTP Basic credentials.")
            if not self.auth_password:
                out.append("NORDFLOW_AUTH_PASSWORD is not set. Browser access requires HTTP Basic credentials.")
            elif len(self.auth_password) < MIN_PASSWORD_CHARS:
                out.append(f"NORDFLOW_AUTH_PASSWORD is shorter than {MIN_PASSWORD_CHARS} characters. "
                           "The demo is shared-credential only, so use a long random password.")
        if deploy and self.host not in LOOPBACK and not self.allow_public_bind:
            out.append(f"NORDFLOW_HOST={self.host} would expose the demo directly. HTTP Basic credentials are sent "
                       "in clear text, so bind 127.0.0.1 and terminate TLS in a reverse proxy. Set "
                       "NORDFLOW_ALLOW_PUBLIC_BIND=1 only if TLS is already terminated in front of this process.")
        if self.data_dir and not os.path.isdir(self.data_dir):
            out.append(f"NORDFLOW_DATA_DIR={self.data_dir} is not a directory.")
        return out

    def check(self, check_agent_credentials=True):
        problems = self.problems(check_agent_credentials)
        if problems:
            raise ConfigError(problems)
        return self

    # -- safe output -----------------------------------------------------

    def secret_values(self):
        return tuple(v for v in (self.api_key, *self.other_secrets, self.auth_password) if v)

    def summary(self):
        """Redacted view, safe to print at startup. Secrets appear only as present/missing."""
        return {
            "mode": self.mode, "agent": self.agent, "model": self.model, "effort": self.effort,
            "bind": f"{self.host}:{self.port}",
            "auth": "basic" if self.auth_required else "none",
            "auth_user": self.auth_user or "-",
            "api_key": (f"{KEY_VARS[self.agent]} set" if self.api_key else f"{KEY_VARS[self.agent]} missing")
            if self.agent in KEY_VARS else "-",
            "data_dir": self.data_dir or "data/ (default)",
            "max_conversations": self.max_conversations,
        }

    def without_secrets(self):
        return replace(self, auth_password=None, api_key=None, other_secrets=())

    def redact(self, text):
        return redact(text, self.secret_values())


def env_secrets(env=None):
    env = os.environ if env is None else env
    return tuple(v for v in (env.get("ANTHROPIC_API_KEY"), env.get("ANTHROPIC_AUTH_TOKEN"),
                             env.get("OPENAI_API_KEY"), env.get("NORDFLOW_AUTH_PASSWORD")) if v)


def redact(text, extra=()):
    """Remove anything that looks like a credential before it reaches a log or a response."""
    out = str(text)
    for value in (*extra, *env_secrets()):
        if value and len(value) >= 4:
            out = out.replace(value, MASK)
    return SECRET_PATTERN.sub(MASK, out)


def load_settings(env=None):
    return Settings.from_env(env)
