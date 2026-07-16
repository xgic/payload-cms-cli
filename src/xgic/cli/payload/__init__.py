"""XGIC CLI Payload CMS module (``xgic.cli.payload``)."""

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_PROJECT,
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIMARY_SERVICE,
    get_db_config,
    get_db_profile,
    get_payload_project_name,
    make_payload_docker_controller,
)
from xgic.cli.payload.project import (
    build_create_payload_command,
    ensure_payload_project,
    load_create_payload_config,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_COMPOSE_PROJECT",
    "DEFAULT_CONFIG_FILE",
    "DEFAULT_PRIMARY_SERVICE",
    "build_create_payload_command",
    "ensure_payload_project",
    "get_db_config",
    "get_db_profile",
    "get_payload_project_name",
    "load_create_payload_config",
    "make_payload_docker_controller",
    "__version__",
]
