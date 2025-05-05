"""Constants for HA Cup Component."""

from datetime import timedelta

DOMAIN = "cup_component"
DEFAULT_NAME = "Cup server name"
DEFAULT_URL = "http://<YOUR_IP>:8000"
# DEFAULT_URL = "http://nipogi.local:8765"

CONF_UPDATE_INTERVAL = "update_interval"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)
