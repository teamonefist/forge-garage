import json
from pathlib import Path

_strings: dict = {}
_current_lang: str = "uk"
_i18n_dir: Path = Path()


def init(garage_home: Path, lang: str = "uk"):
    global _i18n_dir
    _i18n_dir = garage_home / "i18n"
    set_language(lang)


def set_language(lang: str):
    global _strings, _current_lang
    path = _i18n_dir / f"{lang}.json"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as fh:
        _strings = json.load(fh)
    _current_lang = lang


def t(key: str, **kwargs) -> str:
    template = _strings.get(key, f"[{key}]")
    return template.format(**kwargs) if kwargs else template


def current() -> str:
    return _current_lang
