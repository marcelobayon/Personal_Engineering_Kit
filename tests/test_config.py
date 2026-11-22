import json

import pytest

from mbkit import Config, load_config
from mbkit.config import ConfigError


def test_typed_getters():
    cfg = Config({"port": "8080", "debug": "true", "ratio": "0.5", "name": 42})
    assert cfg.get_int("port") == 8080
    assert cfg.get_bool("debug") is True
    assert cfg.get_float("ratio") == 0.5
    assert cfg.get_str("name") == "42"


def test_defaults_and_missing():
    cfg = Config({"a": 1})
    assert cfg.get_int("missing", 99) == 99
    assert cfg.get("missing") is None
    with pytest.raises(ConfigError):
        cfg.require("missing")


def test_bad_coercion_raises():
    cfg = Config({"port": "not-a-number"})
    with pytest.raises(ConfigError):
        cfg.get_int("port")
    with pytest.raises(ConfigError):
        Config({"flag": "maybe"}).get_bool("flag")


def test_precedence_env_over_file_over_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "settings.json"
    cfg_file.write_text(json.dumps({"port": 3000, "debug": False}))

    monkeypatch.setenv("APP_PORT", "9090")  # env should win over file
    cfg = load_config(
        defaults={"port": 1000, "debug": False, "region": "us"},
        file=cfg_file,
        env_prefix="APP_",
    )
    assert cfg.get_int("port") == 9090        # from env
    assert cfg.get_bool("debug") is False     # from file
    assert cfg.get_str("region") == "us"      # from defaults


def test_missing_file_is_ignored(tmp_path):
    cfg = load_config(defaults={"x": 1}, file=tmp_path / "nope.json", env=False)
    assert cfg.get_int("x") == 1


def test_dotenv_parsing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('# comment\nexport TOKEN="secret"\nPORT=8000\n')
    cfg = load_config(file=env_file, env=False)
    assert cfg.get_str("TOKEN") == "secret"
    assert cfg.get_int("PORT") == 8000
