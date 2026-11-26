"""Constants for HA Cup Component."""

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "cup_component"

DEFAULT_NAME: Final[str] = "Cup server name"
DEFAULT_URL: Final[str] = "http://<YOUR_IP>:8000"

CONF_UPDATE_INTERVAL: Final[str] = "update_interval"
CONF_EXCLUDE_PATTERNS: Final[str] = "exclude_patterns"

DEFAULT_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=300)
MIN_SELECTED_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=15)
