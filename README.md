# XGIC Payload CMS CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/xgic-payload-cms-cli.svg)](https://pypi.org/project/xgic-payload-cms-cli/)
[![Python](https://img.shields.io/pypi/pyversions/xgic-payload-cms-cli.svg)](https://pypi.org/project/xgic-payload-cms-cli/)
[![CI](https://github.com/xgic/payload-cms-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/xgic/payload-cms-cli/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/xgic/payload-cms-cli)](https://github.com/xgic/payload-cms-cli/releases)
[![Producer](https://img.shields.io/github/v/release/xgic/payload-cms-dev?label=payload-cms-dev)](https://github.com/xgic/payload-cms-dev/releases)

**Payload CMS product commands for the modular [XGIC CLI](https://github.com/xgic/cli).**

Namespace: **`xgic.cli.payload`** · Console group: **`xgic payload …`** · Brand: **XGIC CLI only** ([ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md))

Standards hub: [xgic/ai](https://github.com/xgic/ai)

---

## Vision

Payload application teams—and the AI agents that help them—need a **small, stable command surface** for project ensure, environment status, smart dev start, and safe reset. This module owns that **product** surface. Generic Compose lifecycle stays in [dev-cli](https://github.com/xgic/dev-cli); the Dev Container **image** is built in [payload-cms-dev](https://github.com/xgic/payload-cms-dev); applications start from [payload-cms](https://github.com/xgic/payload-cms).

One brand (`xgic`), clear ownership, and dry-run-friendly destructive paths.

---

## Why this module exists

| Benefit | Detail |
|---------|--------|
| **Domain clarity** | Nested under `xgic payload`—no clash with generic `xgic up` / `down` |
| **AI + human parity** | Same commands in READMEs and [AGENTS.md](AGENTS.md) |
| **Safe operations** | Reset and regenerate paths support explicit confirmation / dry-run patterns |
| **Composable stack** | Depends on `xgic-cli` + `xgic-dev-cli`; ships on PyPI for image and host installs |
| **Open-source rigor** | Apache-2.0, Python 3.14+, RC → TestPyPI → PyPI |

---

## Ecosystem

| Package / repo | Role |
|----------------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/dev-cli](https://github.com/xgic/dev-cli) | Dev Container / Docker Compose lifecycle |
| **This repo** | Payload CMS product module (`xgic.cli.payload`) |
| [xgic/payload-cms-dev](https://github.com/xgic/payload-cms-dev) | Dev Container **image producer** (`ghcr.io/xgic/payload-cms-dev`) |
| [xgic/payload-cms](https://github.com/xgic/payload-cms) | End-user **template** (recommended app start) |

---

## Quick start

### Install (PyPI)

```bash
uv pip install \
  "xgic-cli>=0.2.0,<0.3" \
  "xgic-dev-cli>=0.2.0,<0.3" \
  "xgic-payload-cms-cli>=0.2.1,<0.3"
xgic payload --help
```

### Development (editable)

```bash
uv pip install -e ../cli
uv pip install -e ../dev-cli
uv pip install -e ".[dev]"
xgic payload --help
```

### Typical Payload session (inside a Dev Container)

**First session** (one setup command — creates `.devcontainer/.env` if missing, starts the DB profile, scaffolds the app):

```bash
xgic payload setup
xgic payload dev
```

**Daily** (after the app exists):

```bash
xgic payload dev
```

Optional: `xgic payload env` (status), `xgic payload env --regenerate --yes` (rotate credentials only — not required for first setup).

Prefer the end-user template for application work: [payload-cms](https://github.com/xgic/payload-cms).

---

## Console commands

All product commands nest under **`xgic payload`**:

| Command | Purpose |
|---------|---------|
| `xgic payload dev` | **Primary daily command** — smart start (up if needed, DB check, `pnpm dev`) |
| `xgic payload setup [--quiet]` | **First-run one-shot:** env (if missing) + DB profile + scaffold (idempotent) |
| `xgic payload env [--json]` | Product env status (project name, `.env`, services) |
| `xgic payload env --regenerate --yes` | Rotate credentials in `.devcontainer/.env` (optional; setup creates env when absent) |
| `xgic payload schema` | Run template schema generator when present |
| `xgic payload reset` | Fast targeted reset (project folder + active DB volume) |

**Generic lifecycle** (`xgic up` / `down` / `check` / `env`) lives in **dev-cli**. Use **`xgic payload env`** for Payload credentials and product status.

### Setup: automatic vs manual

| Mode | Guidance |
|------|----------|
| **Automatic** | Producer/image `postStart` may call `xgic payload setup` via a thin shell wrapper (idempotent). |
| **Manual / testing** | After `xgic payload reset --yes`, or when validating scaffold config—not a “daily” app ritual. |

Always prefer **`xgic payload reset --dry-run`** before destructive reset.

### Historical command map (`xde` → XGIC CLI)

Living brand is **XGIC CLI only**. Historical map for agents migrating old notes:

| Historical (`xde`) | XGIC CLI |
|--------------------|----------|
| `xde dev` | `xgic payload dev` |
| `xde setup payloadcms` | `xgic payload setup` |
| `xde schema` | `xgic payload schema` |
| `xde env --regenerate` | `xgic payload env --regenerate --yes` |
| `xde reset` | `xgic payload reset` |
| `xde up` / `down` / … | `xgic up` / `down` / … (dev-cli) |

---

## Library API

```python
from xgic.cli.payload import (
    ensure_payload_project,
    generate_fresh_env_content,
    make_payload_docker_controller,
    get_payload_project_name,
)
```

---

## Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0
- `xgic-dev-cli` ≥ 0.2.0

---

## Publishing

Follow [python-package-release.md](https://github.com/xgic/ai/blob/main/docs/python-package-release.md).

Publish **after** `xgic-cli` and `xgic-dev-cli` for stack releases. Tags: `vX.Y.ZrcN` → TestPyPI; `vX.Y.Z` → PyPI.

---

## Working with AI assistants

High-signal prompts:

- “Run `xgic payload env` (no secrets) and recommend whether to start Postgres.”  
- “Start with `xgic payload dev` and report the listen URL.”  
- “Show `xgic payload reset --dry-run` before any reset.”  

Ownership:

| Change | Repository |
|--------|------------|
| `xgic payload …` behavior | **This repo** |
| `xgic up` / `down` / `check` | [dev-cli](https://github.com/xgic/dev-cli) |
| Image / Dockerfile | [payload-cms-dev](https://github.com/xgic/payload-cms-dev) |
| App template pin / docs | [payload-cms](https://github.com/xgic/payload-cms) |

Public-safe gate: [BASE-STANDARDS](https://github.com/xgic/ai/blob/main/docs/BASE-STANDARDS-FOR-ORCHESTRATED-REPOS.md).

---

## Contributing

PRs with human UI review only. Conventional Commits; labels required. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

---

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.

---

**XGIC** — Modular CLI for open-source platforms: thin core, domain modules, and AI-operable Payload workflows.
