# mbkit — Personal Engineering Kit

A small, dependency-free Python toolkit of the patterns I reach for in every
project — so I stop re-writing logging, config, and resilience code from
scratch each time.

> **Standardize patterns. Accelerate development. Document the thinking.**

Standard library only. Typed. Tested. One import path across all my projects
(Ground Stasis, Mitig8, NorthReserve, MachineWorth, …).

```python
from mbkit import get_logger, load_config, retry, CircuitBreaker, Ok, Err, Timer
```

> The import name is `mbkit` (short, memorable, typed often). It's a one-line
> rename if you'd prefer `marcelobayon` — see *Renaming* below.

---

## Install

From a local checkout (editable, while developing the kit):

```bash
pip install -e ".[dev]"
```

Directly from GitHub (to reuse it in another project):

```bash
pip install "git+https://github.com/marcelobayon/personal_engineering_kit.git"
```

Requires Python 3.10+. No runtime dependencies.

## Quick tour

Run the whole thing: `python examples/quickstart.py`.

### Logging — configured once, never doubled

```python
from mbkit import get_logger

log = get_logger("myapp", level="INFO")       # human-readable to stderr
log.info("server starting", extra={"port": 8080})

api = get_logger("myapp.api", json=True)       # structured one-line JSON
api.info("request", extra={"request_id": "abc123"})
# {"time": "...", "level": "INFO", "logger": "myapp.api", "message": "request", "request_id": "abc123"}
```

Calling `get_logger("myapp")` again returns the *same* logger with no extra
handlers — no more lines printing two or three times.

### Config — one precedence rule everywhere

`defaults < file < environment`. The file may be `.json`, `.toml`, or `.env`.

```python
from mbkit import load_config

cfg = load_config(
    defaults={"port": 8080, "debug": False},
    file="settings.json",     # missing file? ignored, so dev == prod
    env_prefix="MYAPP_",      # MYAPP_PORT=9090 wins and becomes `port`
)
cfg.get_int("port")     # 9090
cfg.get_bool("debug")   # coerces "true"/"1"/"yes" -> True
cfg.require("api_key")  # raises ConfigError if unset
```

### Resilience — survive partial failure, on purpose

```python
from mbkit import retry, CircuitBreaker, fallback

@retry(attempts=3, exceptions=(ConnectionError,))   # bounded backoff + jitter
def fetch(): ...

breaker = CircuitBreaker(failure_threshold=5, reset_timeout=30)
breaker.call(fetch)   # stops hammering a dead dependency, then tests recovery

value, source = fallback(                            # approved alternatives
    ("primary", fetch_primary),
    ("cache", read_cache),
    validate=lambda v: bool(v),                      # reject empty/stale results
)
```

These come from `docs/biology-to-software.md` — resilience patterns translated
from biology into **bounded, verifiable** code. The rule throughout:
*self-healing means verified recovery, not silently swallowing errors.*

### Result — expected failures as values

```python
from mbkit import Ok, Err, Result

def parse_port(raw: str) -> Result[int, str]:
    return Ok(int(raw)) if raw.isdigit() else Err(f"bad port: {raw!r}")

parse_port("9000").map(lambda p: p + 1).unwrap_or(8080)   # 9001
parse_port("oops").unwrap_or(8080)                        # 8080
```

### Timing — measure before you optimize

```python
from mbkit import Timer, timed

with Timer("load", logger=log):
    load_everything()

@timed(log, label="render")
def render(): ...
```

## Layout

```
personal_engineering_kit/
├── pyproject.toml          # packaging + tool config, single source of truth
├── src/mbkit/
│   ├── __init__.py         # public API + __version__
│   ├── log.py              # get_logger, bind, JsonFormatter
│   ├── config.py           # load_config, Config
│   ├── result.py           # Result, Ok, Err
│   ├── timing.py           # Timer, timed
│   └── resilience/
│       ├── retry.py         # retry, RetryError
│       ├── circuit_breaker.py  # CircuitBreaker, CircuitOpenError
│       └── fallback.py      # FallbackChain, fallback
├── tests/                  # pytest suite
├── examples/quickstart.py  # runnable tour
└── docs/biology-to-software.md
```

Uses the **src layout** so tests run against the *installed* package, not the
working tree — the thing that prevents "works on my machine."

## Develop

```bash
pip install -e ".[dev]"
pytest            # run tests
ruff check .      # lint
mypy              # type-check (strict)
```

## Versioning

[SemVer](https://semver.org/). Pin it in downstream projects so an upgrade
can't silently break them, e.g. `mbkit>=0.2.0,<0.3.0`. See `CHANGELOG.md`.

## Renaming

Prefer `from marcelobayon import ...`? Rename the folder and update two lines:

```bash
git mv src/mbkit src/marcelobayon
# in pyproject.toml: name = "marcelobayon", and [tool.setuptools.package-data] key
```

Nothing else imports by the hard-coded name internally (all intra-package
imports are relative).

## License

MIT © 2026 Marcelo Bayon
