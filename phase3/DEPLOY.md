# Deploying the demo on a small private VM

For showing the demo to a handful of people over the internet: one 1 vCPU / 2 GB
Linux VM, one shared password, HTTPS in front. Everything below has been prepared
in the repository but **nothing has been deployed** — these are the steps to run.

**What this is not.** It is a demo on synthetic data, not a product. One shared
credential for everyone, no user accounts, no roles, no audit trail, no rate
limiting. Do not put real company data behind it, and keep the URL private.

---

## 1. What you need

- A VM with Ubuntu 24.04 (1 vCPU, 2 GB RAM, ~5 GB disk), ports 80 and 443 reachable.
- A DNS name pointing at it, e.g. `demo.example.com` (needed for a TLS certificate).
- An Anthropic API key. The demo's `api` agent mode is required for deployment;
  `cli` mode depends on an interactive Claude Code login and is refused at startup.

Rough cost drivers: the VM, plus one Anthropic API call chain per question
(typically 20–40 tool calls, 30–60 s at `medium` effort).

## 2. Install

```bash
sudo apt update && sudo apt install -y python3-venv git
sudo useradd --system --create-home --home-dir /opt/nordflow nordflow
sudo -u nordflow git clone <your-repo-url> /opt/nordflow/app
cd /opt/nordflow/app
sudo -u nordflow python3 -m venv .venv
sudo -u nordflow .venv/bin/pip install -r phase3/requirements.txt
```

The dataset is committed under `data/`, so there is nothing to generate on the VM.
Optionally confirm it is the released Phase 1 dataset:

```bash
sudo -u nordflow .venv/bin/python src/manifest.py      # checksums of data/
```

## 3. Configuration and secrets

All configuration is environment variables; nothing is read from the repository.
Put them in a root-owned file that only the service can read:

```bash
sudo install -d -m 750 -o root -g nordflow /etc/nordflow
sudo install -m 640 -o root -g nordflow /dev/null /etc/nordflow/demo.env
sudo -e /etc/nordflow/demo.env
```

```ini
NORDFLOW_MODE=deploy
NORDFLOW_AGENT=api
ANTHROPIC_API_KEY=sk-ant-...
NORDFLOW_AUTH_USER=nordflow
NORDFLOW_AUTH_PASSWORD=<long random password>
# optional
NORDFLOW_MODEL=claude-opus-5
NORDFLOW_EFFORT=medium
NORDFLOW_PORT=8765
```

Generate the password on the VM, never by hand:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `NORDFLOW_MODE` | – | `local` | `deploy` enforces API mode, an API key and Basic auth |
| `NORDFLOW_AGENT` | – | `auto` | `api` \| `cli` \| `auto`; `cli` is rejected in deploy mode |
| `ANTHROPIC_API_KEY` | deploy | – | Server-side only. Never sent to the browser, never logged |
| `NORDFLOW_AUTH_USER` | deploy | – | Shared HTTP Basic user |
| `NORDFLOW_AUTH_PASSWORD` | deploy | – | Shared HTTP Basic password, at least 12 characters |
| `NORDFLOW_MODEL` | – | `claude-opus-5` | Model for the agent |
| `NORDFLOW_EFFORT` | – | `medium` | `low` … `max`; higher means slower and dearer |
| `NORDFLOW_HOST` | – | `127.0.0.1` | Keep the loopback default and let the proxy terminate TLS |
| `NORDFLOW_PORT` | – | `8765` | Port the app listens on |
| `NORDFLOW_MAX_CONVERSATIONS` | – | `50` | In-memory conversations kept; oldest are evicted |
| `NORDFLOW_MAX_QUESTION_CHARS` | – | `2000` | Longer questions are rejected with 413 |
| `NORDFLOW_DATA_DIR` | – | `data/` | Alternative dataset directory |
| `NORDFLOW_ALLOW_PUBLIC_BIND` | – | – | `1` only if TLS is terminated in front of the process |
| `NORDFLOW_FORWARDED_ALLOW_IPS` | – | `127.0.0.1` | Proxy addresses trusted for `X-Forwarded-*` |

Check the configuration before starting anything. It validates secrets, starts the
MCP server, reads the dataset, and exits — no port is opened and no model is called:

```bash
sudo -u nordflow env $(sudo cat /etc/nordflow/demo.env | grep -v '^#' | xargs) \
  /opt/nordflow/app/.venv/bin/python -m phase3.server --check
```

Missing or unusable settings are reported in one block with exit code 2, for example:

```
Cannot start the NordFlow demo - configuration problems:
  * ANTHROPIC_API_KEY is not set. The API agent needs it; keep it in the server's environment file only ...
  * NORDFLOW_AUTH_PASSWORD is not set. Browser access requires HTTP Basic credentials.
```

## 4. Run it as a service

`/etc/systemd/system/nordflow-demo.service`:

```ini
[Unit]
Description=NordFlow executive demo
After=network-online.target
Wants=network-online.target

[Service]
User=nordflow
WorkingDirectory=/opt/nordflow/app
EnvironmentFile=/etc/nordflow/demo.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/nordflow/app/.venv/bin/python -m phase3.server
Restart=on-failure
RestartSec=5
# the service only needs to read the repo and write phase3/logs
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/nordflow/app/phase3/logs
MemoryMax=1500M
TasksMax=200

[Install]
WantedBy=multi-user.target
```

```bash
sudo -u nordflow mkdir -p /opt/nordflow/app/phase3/logs
sudo systemctl daemon-reload && sudo systemctl enable --now nordflow-demo
systemctl status nordflow-demo && curl -s localhost:8765/healthz
```

A bad configuration stops the unit with exit code 2 and the reason in
`journalctl -u nordflow-demo`; systemd will not retry a config error indefinitely
if you leave `Restart=on-failure` (it retries, but the log keeps saying why).

## 5. TLS and the reverse proxy

HTTP Basic credentials travel in clear text, so the app must not be exposed
directly — it binds `127.0.0.1` and refuses any other bind in deploy mode unless
`NORDFLOW_ALLOW_PUBLIC_BIND=1` is set deliberately. Caddy gets a certificate
automatically:

```bash
sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```
demo.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8765 {
        flush_interval -1          # stream server-sent events without buffering
        transport http {
            read_timeout 300s      # a question can take a minute or more
        }
    }
}
```

```bash
sudo systemctl reload caddy
sudo ufw allow 22,80,443/tcp && sudo ufw enable
```

`flush_interval -1` matters: without it the progress events are buffered and the
page looks frozen until the answer is complete.

## 6. Verify

```bash
curl -si https://demo.example.com/            | head -3   # 401 + WWW-Authenticate
curl -s  https://demo.example.com/healthz                 # {"status":"ok"}
curl -su nordflow:<password> https://demo.example.com/api/config | head -c 120
```

Then open the site in a browser, enter the shared credentials, and ask one
question end to end.

## 7. Operations

- **Logs.** Service output goes to journald. Each answered question appends one
  JSON line to `phase3/logs/<conversation>.jsonl` with the question, the answer,
  the MCP calls, timings and token usage — no model reasoning, no secrets.
  Those files grow slowly but forever; clean them up with a cron job or
  `find phase3/logs -mtime +30 -delete` if the demo stays up.
- **Rotating credentials.** Edit `/etc/nordflow/demo.env`, then
  `sudo systemctl restart nordflow-demo`. Conversations are in memory, so a
  restart clears them; that is the intended way to wipe the demo's state.
- **Updating.** `git pull`, `pip install -r phase3/requirements.txt`,
  `python -m phase3.server --check`, `systemctl restart nordflow-demo`.
- **Resource use.** The process is idle while waiting for the model, so 1 vCPU is
  enough; memory is dominated by the Python process plus the MCP subprocess, well
  under the 1500 M cap. Concurrency is limited by design: one question at a time
  per conversation. A handful of simultaneous viewers is fine; a crowd is not the
  point of this demo.

## 8. What the hardening does and does not cover

Covered: shared Basic auth on every browser-facing route (`/`, `/static/*`,
`/api/*`; only `/healthz` is open), configuration validated at startup with clear
failures, the API key kept server-side and stripped from the MCP subprocess's
environment, credential-shaped strings redacted from errors, responses and logs,
`Cache-Control: no-store` on pages and API responses, and bounded memory and
request sizes.

Not covered: per-user identity, rate limiting or quota control, brute-force
lockout, CSRF tokens (there is no cookie session; the browser sends Basic
credentials), audit logging, backups, or any protection of the Anthropic spend
beyond keeping the password private. Treat the credential as shared knowledge
among everyone you give it to.
