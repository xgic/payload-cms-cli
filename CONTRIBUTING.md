# Contributing to XGIC Payload CMS CLI

Thank you for contributing.

## Standards

- Multi-repo policy: https://github.com/xgic/ai  
- Community health: https://github.com/xgic/ai/blob/main/docs/community-health.md  
- Architecture: [ADR-0005](https://github.com/xgic/ai/blob/main/docs/adr/0005-modular-xgic-cli-and-retirement-of-xde.md)
- Core: https://github.com/xgic/cli · Dev: https://github.com/xgic/dev-cli

## Workflow

1. Open an issue (use the templates).  
2. Branch from `main` with the issue number in the name.  
3. Use detailed Conventional Commits.  
4. Open a PR to `main` with appropriate **labels**.  
5. Human review and approval in the GitHub UI before merge.

## Development

```bash
python -m pip install -e ../cli
python -m pip install -e ../dev-cli
python -m pip install -e ".[dev]"
pytest
ruff check src tests
```

## Public safety

Do not include private infrastructure details, private tracker IDs, or internal paths in issues, PRs, or code.
