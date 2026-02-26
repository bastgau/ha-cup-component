"""Constants for HA Cup Component."""

from datetime import timedelta

DOMAIN = "cup_component"
DEFAULT_NAME = "Cup server name"
DEFAULT_URL = "http://<YOUR_IP>:8000"

CONF_UPDATE_INTERVAL = "update_interval"
CONF_EXCLUDE_PATTERNS = "exclude_patterns"

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=300)
MIN_SELECTED_UPDATE_INTERVAL = timedelta(seconds=15)
