"""XGIC CLI Payload CMS module (``xgic.cli.payload``)."""

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_PROJECT,
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIMARY_SERVICE,
    db_ready,
    get_db_config,
    get_db_profile,
    get_payload_project_name,
    make_payload_docker_controller,
)
from xgic.cli.payload.env_helpers import (
    generate_fresh_env_content,
    perform_env_regenerate,
)
from xgic.cli.payload.project import (
    build_create_payload_command,
    ensure_payload_project,
    load_create_payload_config,
)

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_COMPOSE_PROJECT",
    "DEFAULT_CONFIG_FILE",
    "DEFAULT_PRIMARY_SERVICE",
    "build_create_payload_command",
    "db_ready",
    "ensure_payload_project",
    "generate_fresh_env_content",
    "get_db_config",
    "get_db_profile",
    "get_payload_project_name",
    "load_create_payload_config",
    "make_payload_docker_controller",
    "perform_env_regenerate",
    "__version__",
]
