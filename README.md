# XGIC Payload CMS CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**XGIC Payload CMS CLI** (`xgic.cli.payload`) provides **Payload CMS–specific** helpers and **`xgic payload …` subcommands** for the modular [XGIC CLI](https://github.com/xgic/cli).

Architecture: [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md).

| Package | Role |
|---------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/dev-cli](https://github.com/xgic/dev-cli) | Dev Container / Compose + generic lifecycle |
| **This repo** | Payload CMS product module (`xgic.cli.payload`) |

## Status

**0.2.0 — B4 product commands.** Library helpers + nested `xgic payload` command group. Transitional in-tree `xde` may still ship until hard cutover (B5).

## Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0
- `xgic-dev-cli` ≥ 0.2.0

## Install (development)

```bash
python -m pip install -e ../cli
python -m pip install -e ../dev-cli
python -m pip install -e ".[dev]"
xgic payload --help
```

## Console commands

All product commands are nested under **`xgic payload`** (domain ownership; no clash with generic lifecycle).

| Command | Purpose |
|---------|---------|
| `xgic payload dev` | Smart start: compose up if needed, DB check, `pnpm dev` |
| `xgic payload setup [--quiet]` | Ensure Payload CMS project directory |
| `xgic payload env [--json]` | Product env status (project name, .env, services) |
| `xgic payload env --regenerate --yes` | Fresh credentials in `.devcontainer/.env` |
| `xgic payload schema` | Run template schema generator when present |

**Note:** Generic lifecycle (`xgic up` / `down` / `check` / `env`) lives in **dev-cli**.  
Use `xgic payload env` for Payload CMS credentials and product status.

### Command map (transitional `xde` → XGIC CLI)

| Today (`xde`) | Target |
|---------------|--------|
| `xde dev` | `xgic payload dev` |
| `xde setup payloadcms` | `xgic payload setup` |
| `xde schema` | `xgic payload schema` |
| `xde env --regenerate` | `xgic payload env --regenerate --yes` |
| `xde up` / `down` / … | `xgic up` / `down` / … (dev-cli) |

## Library API

```python
from xgic.cli.payload import (
    ensure_payload_project,
    generate_fresh_env_content,
    make_payload_docker_controller,
    get_payload_project_name,
)
```

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.
