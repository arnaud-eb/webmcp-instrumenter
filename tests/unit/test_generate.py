"""US3 unit tests (T027): approved-only gate (Principle I) + no secrets (FR-007)."""

import json

from webmcp_instrumenter.generate import generate
from webmcp_instrumenter.io import save_json
from webmcp_instrumenter.models import Api, Contract, ReviewStatus


def _contract(name, api, status, cid="c1"):
    return Contract(
        candidate_id=cid,
        tool_name=name,
        description=f"{name} description.",
        input_schema={"type": "object", "properties": {"email": {"type": "string"}}},
        api=api,
        review_status=status,
    )


def _write(tmp_path, contracts):
    path = tmp_path / "contracts.json"
    save_json(path, [c.to_dict() for c in contracts])
    return path


def test_only_approved_contracts_are_emitted(tmp_path):
    contracts = [
        _contract("submit_contact_form", Api.DECLARATIVE, ReviewStatus.APPROVED, "c1"),
        _contract("add_to_cart", Api.IMPERATIVE, ReviewStatus.APPROVED, "c2"),
        _contract("search_site", Api.DECLARATIVE, ReviewStatus.NEEDS_REVIEW, "c3"),
    ]
    out = tmp_path / "out"
    summary = generate(_write(tmp_path, contracts), out)

    assert (summary.approved, summary.declarative, summary.imperative) == (2, 1, 1)
    assert (out / "submit_contact_form.declarative.html").exists()
    assert (out / "add_to_cart.imperative.js").exists()
    # The needs_review tool must NOT be emitted (human gate).
    assert not (out / "search_site.declarative.html").exists()
    assert (out / "logger.js").exists()


def test_manifest_lists_exactly_approved_tools(tmp_path):
    contracts = [
        _contract("submit_contact_form", Api.DECLARATIVE, ReviewStatus.APPROVED, "c1"),
        _contract("add_to_cart", Api.IMPERATIVE, ReviewStatus.APPROVED, "c2"),
        _contract("search_site", Api.DECLARATIVE, ReviewStatus.NEEDS_REVIEW, "c3"),
    ]
    out = tmp_path / "out"
    generate(_write(tmp_path, contracts), out)
    manifest = json.loads((out / ".well-known" / "webmcp").read_text())
    names = {t["name"] for t in manifest["tools"]}
    assert names == {"submit_contact_form", "add_to_cart"}


def test_no_secrets_in_generated_output(tmp_path):
    contracts = [_contract("submit_contact_form", Api.DECLARATIVE, ReviewStatus.APPROVED)]
    out = tmp_path / "out"
    generate(_write(tmp_path, contracts), out)
    needles = ("sk-ant", "api_key", "anthropic_api_key", "secret", "authorization")
    for f in out.rglob("*"):
        if f.is_file():
            text = f.read_text().lower()
            assert not any(n in text for n in needles), f"possible secret in {f.name}"


def test_nothing_approved_emits_nothing(tmp_path):
    contracts = [_contract("search_site", Api.DECLARATIVE, ReviewStatus.NEEDS_REVIEW)]
    out = tmp_path / "out"
    summary = generate(_write(tmp_path, contracts), out)
    assert summary.approved == 0
    assert not out.exists() or not any(out.iterdir())
