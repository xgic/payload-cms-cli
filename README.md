# XGIC Payload CMS CLI

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**XGIC Payload CMS CLI** (`xgic.cli.payload`) holds **Payload CMS–specific** helpers for the modular [XGIC CLI](https://github.com/xgic/cli): project ensure/create, product config, and template defaults.

Architecture: [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md).

| Package | Role |
|---------|------|
| [xgic/cli](https://github.com/xgic/cli) | Thin core framework (`xgic`) |
| [xgic/dev-cli](https://github.com/xgic/dev-cli) | Dev Container / Compose library |
| **This repo** | Payload CMS product module (`xgic.cli.payload`) |

## Status

**0.1.0 — library extract.** Project ensure/create helpers and product config. Console subcommands (`setup`, smart `dev`, schema, …) land in later releases.

## Requirements

- Python **3.14+**
- `xgic-cli` ≥ 0.2.0
- `xgic-dev-cli` ≥ 0.1.0

## Install (development)

```bash
python -m pip install -e ../cli
python -m pip install -e ../dev-cli
python -m pip install -e ".[dev]"
```

## Library API

```python
from xgic.cli.payload import (
    ensure_payload_project,
    load_create_payload_config,
    get_payload_project_name,
    make_payload_docker_controller,  # from xgic.cli.payload.config
)
from xgic.cli.payload.config import make_payload_docker_controller
from xgic.cli.core import EnvironmentContext

env = EnvironmentContext.detect()
docker = make_payload_docker_controller(env)
ensure_payload_project(quiet=True)
```

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright form: `Copyright 2026 XGIC`.
