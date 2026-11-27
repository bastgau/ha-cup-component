"""Constants for HA Cup Component."""

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "cup_component"

DEFAULT_NAME: Final[str] = "Cup server name"
DEFAULT_URL: Final[str] = "http://<YOUR_IP>:8000"

CONF_UPDATE_INTERVAL: Final[str] = "update_interval"
CONF_EXCLUDE_PATTERNS: Final[str] = "exclude_patterns"
CONF_UPDATE_ENTITIES: Final[str] = "update_entities"

# Update entities are opt-in: an entry without the option behaves as if it were off.
DEFAULT_UPDATE_ENTITIES: Final[bool] = False

DEFAULT_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=300)
MIN_SELECTED_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=15)
