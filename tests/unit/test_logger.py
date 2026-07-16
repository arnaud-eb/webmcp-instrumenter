"""US4 logger-template guarantees (T033): the generated logger.js must record param KEY
names only (Constitution II) and fail open (Constitution III / FR-010).

The logger is client-side JS, so these are static guarantees over the *rendered* template —
enough to catch a regression that would either leak values or throw into the host page.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "webmcp_instrumenter" / "templates"


def _render(sink_url: str = '"https://sink.example/events"') -> str:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=False)
    return env.get_template("logger.js.j2").render(sink_url=sink_url)


def test_logger_sends_only_the_five_allowed_fields():
    js = _render()
    for field in ("site", "tool_name", "timestamp", "success", "param_keys"):
        assert field in js
    # The sink URL is injected verbatim.
    assert "https://sink.example/events" in js


def test_declarative_logging_uses_form_keys_not_values():
    # The one place form data is touched, it must take .keys() — never values.
    js = _render()
    assert "new FormData(f).keys()" in js
    # A regression that logged values would reference .entries()/.values()/.get(.
    assert ".values()" not in js
    assert ".entries()" not in js


def test_logger_is_fire_and_forget_and_swallows_errors():
    js = _render()
    # Fire-and-forget transport.
    assert "sendBeacon" in js
    assert "keepalive" in js
    # Errors on the logging path are swallowed so they never reach host-page code.
    assert "catch" in js
    assert js.count("catch") >= 2  # around the transport AND the submit handler
