import yaml
from pathlib import Path

_config = None


def load_config() -> dict:
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    return _config


def get_all_sources() -> list[dict]:
    cfg = load_config()
    sources = []
    for group in cfg["sources"].values():
        sources.extend(group)
    return sources


def get_event_categories() -> list[dict]:
    return load_config()["event_categories"]


def get_category_by_slug(slug: str) -> dict | None:
    for c in get_event_categories():
        if c["slug"] == slug:
            return c
    return None


def get_currency_pairs() -> list[dict]:
    return load_config()["currency_pairs"]


def get_regions() -> list[dict]:
    return load_config()["regions"]
