# AI Agent Instructions — XGIC Payload CMS CLI

Public repository. Follow https://github.com/xgic/ai for multi-repo standards.

## Product

- **Package:** `xgic.cli.payload` (distribution `xgic-payload-cms-cli`)  
- **Depends on:** `xgic-cli`, `xgic-dev-cli`  
- **Architecture:** [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md)

## Scope

- Payload CMS project ensure/create helpers  
- Product config (`create-payload-config.json`) and template Compose defaults  
- Nested `xgic` subcommands under **`payload`**: `dev`, `setup`, `env`, `schema`  

## Out of scope

- Thin CLI framework → https://github.com/xgic/cli  
- Generic Compose lifecycle (`up`/`down`/`check`/`env`) → https://github.com/xgic/dev-cli  

## Rules

- Public-safe content only  
- Human UI review before merge to `main`  
- Dedicated issue-number branches; Conventional Commits  
- Labels required on issues/PRs  
- Python 3.14+; Apache-2.0; root `CODEOWNERS` (`@xgic`)  
- Use full product name **Payload CMS** in prose  
- Product commands use space hierarchy: `xgic payload <action>` (not hyphenated top-level)  
- Do not re-register generic `xgic env`; use `xgic payload env` for product secrets  
