"""CLI default-path behavior (contracts/cli.md — per-site run directories)."""

from pathlib import Path

from webmcp_instrumenter.cli import run_dir_for


def test_run_dir_uses_hostname():
    assert run_dir_for("https://example.com/contact") == Path("runs/example.com")
    assert run_dir_for("https://shop.example.co.uk/cart?x=1") == Path("runs/shop.example.co.uk")


def test_run_dir_ignores_port_and_scheme():
    assert run_dir_for("http://localhost:8099/") == Path("runs/localhost")


def test_run_dir_falls_back_to_local_without_a_host():
    assert run_dir_for("file:///tmp/page.html") == Path("runs/local")
