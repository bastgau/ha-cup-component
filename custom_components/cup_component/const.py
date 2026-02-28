"""Constants for HA Cup Component."""

from datetime import timedelta
import json
from pathlib import Path
import time
from typing import Final

DOMAIN: Final[str] = "cup_component"

# Integration version read from manifest.json — used to version Lovelace resources.
_MANIFEST_PATH: Final[Path] = Path(__file__).parent / "manifest.json"
with _MANIFEST_PATH.open(encoding="utf-8") as _f:
    # Fallback to a Unix timestamp if version is missing or set to the default placeholder (dev environment only).
    _version: str = json.load(_f).get("version", "")
    INTEGRATION_VERSION: Final[str] = _version if _version and _version != "0.0.0" else str(int(time.time()))

# URL path used to serve JS files via a registered static HTTP route.
URL_BASE: Final[str] = "/cup_component"
LOVELACE_CARD_JS: Final[str] = "cup-images-card.js"
LOVELACE_CARD_NAME: Final[str] = "Cup Images Card"
LOVELACE_MODULE_URL: Final[str] = f"{URL_BASE}/{LOVELACE_CARD_JS}"

DEFAULT_NAME: Final[str] = "Cup server name"
DEFAULT_URL: Final[str] = "http://<YOUR_IP>:8000"

CONF_UPDATE_INTERVAL: Final[str] = "update_interval"
CONF_EXCLUDE_PATTERNS: Final[str] = "exclude_patterns"

DEFAULT_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=300)
MIN_SELECTED_UPDATE_INTERVAL: Final[timedelta] = timedelta(seconds=15)
