import json
from pathlib import Path


SETTINGS_FILE = Path("settings.json")

DEFAULT_SETTINGS = {
    "target_name": "suba",
    "cooldown_seconds": 5,
    "socket_port": 5000,
    "camera_width": 640,
    "camera_height": 480
}


def load_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        for key, value in DEFAULT_SETTINGS.items():
            settings.setdefault(key, value)

        return settings

    except Exception:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)