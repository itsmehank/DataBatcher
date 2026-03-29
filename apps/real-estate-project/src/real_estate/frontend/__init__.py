from pathlib import Path


def get_template_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "web_ui" / "templates"


def get_static_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "web_ui" / "static"
