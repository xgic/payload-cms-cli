# XGIC Payload CMS CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**XGIC Payload CMS CLI** (`xgic.cli.payload`) provides **Payload CMS–specific** helpers and **`xgic` subcommands** for the modular [XGIC CLI](https://github.com/xgic/cli).

Architecture: [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md).

| Package | Role |
|---------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/dev-cli](https://github.com/xgic/dev-cli) | Dev Container / Compose + generic lifecycle |
| **This repo** | Payload CMS product module (`xgic.cli.payload`) |

## Status

**0.2.0 — B4 product commands.** Library helpers + registered `xgic` subcommands. Transitional in-tree `xde` may still ship until hard cutover (B5).

## Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0
- `xgic-dev-cli` ≥ 0.2.0

## Install (development)

```bash
python -m pip install -e ../cli
python -m pip install -e ../dev-cli
python -m pip install -e ".[dev]"
xgic --help
```

## Console commands

| Command | Purpose |
|---------|---------|
| `xgic dev` | Smart start: compose up if needed, DB check, `pnpm dev` |
| `xgic setup payloadcms [--quiet]` | Ensure Payload CMS project directory |
| `xgic schema` | Run template schema generator when present |
| `xgic payload-env [--json]` | Product env status (project name, .env, services) |
| `xgic payload-env --regenerate --yes` | Fresh credentials in `.devcontainer/.env` |

**Note:** Generic lifecycle (`xgic up`/`down`/`check`/`env`) lives in **dev-cli**.  
`payload-env` is separate so both modules can install without clashing on `env`.

### Command map (transitional `xde` → XGIC CLI)

| Today (`xde`) | Target |
|---------------|--------|
| `xde dev` | `xgic dev` |
| `xde setup payloadcms` | `xgic setup payloadcms` |
| `xde schema` | `xgic schema` |
| `xde env --regenerate` | `xgic payload-env --regenerate --yes` |
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
