"""Layered configuration loader: defaults < file < environment variables.

One predictable precedence rule for every project, so you stop re-inventing
"where does this setting come from?" in each repo:

1. ``defaults`` you pass in code (lowest priority),
2. a config **file** (``.json``, ``.toml``, or a ``.env``-style file),
3. **environment variables** (highest priority), optionally namespaced by a
   prefix like ``MYAPP_``.

Values are exposed through typed getters that coerce strings sensibly, because
environment variables always arrive as strings.

Example
-------
>>> cfg = Config({"port": 8080, "debug": False})
>>> cfg.get_int("port")
8080
>>> import os; os.environ["APP_DEBUG"] = "true"
>>> cfg = load_config(defaults={"debug": False}, env_prefix="APP_")
>>> cfg.get_bool("debug")
True
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, Union

__all__ = ["Config", "load_config", "ConfigError"]

_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f"}

PathLike = Union[str, "os.PathLike[str]"]


class ConfigError(Exception):
    """Raised for missing required keys or values that will not coerce."""


class Config:
    """An immutable-ish view over a merged configuration mapping."""

    def __init__(self, data: Mapping[str, Any] | None = None):
        self._data: dict[str, Any] = dict(data or {})

    # -- raw access -------------------------------------------------------
    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError as exc:
            raise ConfigError(f"missing config key: {key!r}") from exc

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

    # -- typed getters ----------------------------------------------------
    def require(self, key: str) -> Any:
        """Return ``key`` or raise :class:`ConfigError` if it is absent."""
        if key not in self._data:
            raise ConfigError(f"required config key not set: {key!r}")
        return self._data[key]

    def get_str(self, key: str, default: str | None = None) -> str | None:
        value = self._data.get(key, default)
        return None if value is None else str(value)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        value = self._data.get(key, default)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"config key {key!r} is not an int: {value!r}") from exc

    def get_float(self, key: str, default: float | None = None) -> float | None:
        value = self._data.get(key, default)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"config key {key!r} is not a float: {value!r}") from exc

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        value = self._data.get(key, default)
        if isinstance(value, bool) or value is None:
            return value
        text = str(value).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ConfigError(f"config key {key!r} is not a bool: {value!r}")

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Config({self._data!r})"


# -- loading ---------------------------------------------------------------
def _load_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ConfigError(f"{path} must contain a JSON object at the top level")
        return loaded
    if suffix in {".toml"}:
        return _load_toml(text, path)
    if suffix in {".env", ""} or path.name.startswith(".env"):
        return _load_dotenv(text)
    raise ConfigError(f"unsupported config file type: {path.name}")


def _toml_module(path: Path) -> Any:
    try:
        import tomllib  # type: ignore[import-not-found]  # Python 3.11+

        return tomllib
    except ModuleNotFoundError:  # pragma: no cover - exercised on <3.11
        pass
    try:
        import tomli  # type: ignore[import-not-found]

        return tomli
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ConfigError(
            f"reading {path.name} needs TOML support: use Python 3.11+ "
            "or `pip install tomli`"
        ) from exc


def _load_toml(text: str, path: Path) -> dict[str, Any]:
    return dict(_toml_module(path).loads(text))


def _load_dotenv(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        out[key.strip()] = value
    return out


def _collect_env(prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in os.environ.items():
        if prefix and not key.startswith(prefix):
            continue
        local = key[len(prefix) :] if prefix else key
        out[local.lower()] = value
    return out


def load_config(
    defaults: Mapping[str, Any] | None = None,
    *,
    file: PathLike | None = None,
    env_prefix: str = "",
    env: bool = True,
) -> Config:
    """Build a :class:`Config` by merging defaults, a file, and the environment.

    Parameters
    ----------
    defaults:
        Baseline values defined in code (lowest precedence).
    file:
        Optional path to a ``.json``, ``.toml``, or ``.env`` file. Missing files
        are ignored so the same call works in dev and prod.
    env_prefix:
        Only environment variables starting with this prefix are read, and the
        prefix is stripped (``APP_PORT`` -> ``port``). Empty reads all of them.
    env:
        Set ``False`` to ignore environment variables entirely (useful in tests).
    """
    merged: MutableMapping[str, Any] = dict(defaults or {})

    if file is not None:
        path = Path(file)
        if path.exists():
            merged.update(_load_file(path))

    if env:
        merged.update(_collect_env(env_prefix))

    return Config(merged)
