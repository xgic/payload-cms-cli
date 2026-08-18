# AI Agent Instructions — XGIC Payload CMS CLI

Public repository. Follow https://github.com/xgic/ai for multi-repo standards.

## Product

- **Package:** `xgic.cli.payload` (distribution `xgic-payload-cms-cli`)  
- **Depends on:** `xgic-cli`, `xgic-dev-cli`  
- **Architecture:** [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md)

## Scope

- Payload CMS project ensure/create helpers  
- Product config (`create-payload-config.json`) and template Docker Compose defaults  
- Nested `xgic` subcommands under **`payload`**: `dev`, `setup`, `env`, `schema`, `reset`  

## Out of scope

- Thin CLI framework → https://github.com/xgic/cli  
- Generic Docker Compose lifecycle (`up`/`down`/`check`/`env`) → https://github.com/xgic/dev-cli  

## Rules


**Public GitHub writes:** Before `gh issue create|edit`, `gh pr create|edit`, or any public comment on this repository, complete the **mandatory public-safe draft gate** in https://github.com/xgic/ai/blob/main/docs/BASE-STANDARDS-FOR-ORCHESTRATED-REPOS.md (fictional placeholders only; never name private hosts, private projects, or private tracker IDs). Optional helper from the hub clone: `python scripts/public-safe-scan.py path/to/draft.md`.
- Public-safe content only  
- Human UI review before merge to `main`  
- Dedicated issue-number branches; Conventional Commits  
- Labels required on issues/PRs  
- Python 3.14+; Apache-2.0; root `CODEOWNERS` (`@xgic`)  
- Use full product name **Payload CMS** in prose  
- Product commands use space hierarchy: `xgic payload <action>` (not hyphenated top-level)  
- Do not re-register generic `xgic env`; use `xgic payload env` for product secrets  
- `xgic payload env --regenerate --yes` writes `.devcontainer/.env` (`DATABASE_URL`, Compose `POSTGRES_*` / `MONGO_*`, `PAYLOAD_SECRET`) and syncs the app `.env` under `projectDir` (`DATABASE_URL`, `PAYLOAD_SECRET`, `CRON_SECRET`, `PREVIEW_SECRET`). File rewrite does not change a pre-existing Compose DB volume password.  
- **PyPI releases:** https://github.com/xgic/ai/blob/main/docs/python-package-release.md (OIDC + PyPA action; `uv` build/smoke)  

