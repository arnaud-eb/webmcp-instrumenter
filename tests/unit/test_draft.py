"""US2 unit tests (T021): draft validation, human-gate default, robustness.

Uses an injected fake provider so no live API call is needed.
"""

from webmcp_instrumenter.draft import _finalize, draft_contracts
from webmcp_instrumenter.io import save_json
from webmcp_instrumenter.llm.base import DraftedContract, LLMProvider
from webmcp_instrumenter.models import (
    Api,
    Candidate,
    CandidateType,
    Confidence,
    ReviewStatus,
)


def _cand(cid="c1", confidence=Confidence.HIGH):
    return Candidate(
        id=cid, type=CandidateType.FORM, confidence=confidence,
        page_url="https://ex.com/", html_snippet="<form>", visible=True,
    )


def _drafted(**kw):
    base = dict(tool_name="submit_contact_form", description="Send a contact message.",
                input_schema={"type": "object", "properties": {"email": {"type": "string"}}},
                api=Api.DECLARATIVE, ambiguous=False, note=None)
    return DraftedContract(**{**base, **kw})


class FakeProvider(LLMProvider):
    def __init__(self, drafted):
        self._drafted = drafted

    def draft(self, candidate):
        return self._drafted


def test_draft_never_auto_approves():
    c = _finalize(_cand(), _drafted())
    assert c.review_status is ReviewStatus.NEEDS_REVIEW
    assert c.tool_name == "submit_contact_form"
    assert c.note is None  # clean draft, no warnings


def test_ambiguous_is_noted():
    c = _finalize(_cand(), _drafted(ambiguous=True, note="'name' could be full or first/last"))
    assert c.review_status is ReviewStatus.NEEDS_REVIEW
    assert "name" in (c.note or "")


def test_malformed_output_is_handled_not_crashed():
    c = _finalize(
        _cand(),
        _drafted(tool_name="Submit Form!!", description="", input_schema={"type": "bogus"}),
    )
    assert c.tool_name == "submit_form"  # coerced to snake_case
    assert c.description  # filled with a TODO placeholder
    assert c.input_schema == {"type": "object", "properties": {}}  # reset invalid schema
    assert "invalid input_schema" in c.note
    assert "empty description" in c.note


def test_low_confidence_candidate_is_flagged():
    c = _finalize(_cand(confidence=Confidence.LOW), _drafted())
    assert "low-confidence" in (c.note or "")


def test_draft_contracts_orchestration(tmp_path):
    candidates = {
        "_meta": {"page_url": "https://ex.com/", "origin_trial_advertised": False,
                  "origin_trial_source": None},
        "candidates": [_cand().to_dict()],
    }
    path = tmp_path / "candidates.json"
    save_json(path, candidates)
    result = draft_contracts(path, provider_impl=FakeProvider(_drafted()))
    assert len(result) == 1
    assert result[0].review_status is ReviewStatus.NEEDS_REVIEW
