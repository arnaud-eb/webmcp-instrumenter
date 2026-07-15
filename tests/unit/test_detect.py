"""Fast, browser-free unit tests for the detection logic (US1)."""

from webmcp_instrumenter.detect import (
    build_candidates,
    detect_origin_trial,
    detect_page_language,
    is_cross_origin,
)
from webmcp_instrumenter.models import CandidateType, Confidence

URL = "https://example.com/"


def _form(**kw):
    base = {
        "kind": "form",
        "outerHTML": "<form>",
        "displayNone": False,
        "visible": True,
        "role": "",
        "classId": "",
        "hasVisibleInputs": True,
    }
    return {**base, **kw}


def _button(**kw):
    base = {
        "kind": "button",
        "outerHTML": "<button>",
        "displayNone": False,
        "visible": True,
        "role": "",
        "classId": "",
        "text": "",
    }
    return {**base, **kw}


def test_hidden_elements_are_excluded():
    raw = [_form(displayNone=True), _button(displayNone=True, text="Add to cart")]
    assert build_candidates(raw, URL) == []


def test_cosmetic_form_is_low_confidence_but_surfaced():
    raw = [_form(role="search", classId="site-search")]
    cands = build_candidates(raw, URL)
    assert len(cands) == 1
    assert cands[0].confidence is Confidence.LOW  # surfaced, not dropped


def test_real_form_is_high_confidence():
    cands = build_candidates([_form(classId="contact")], URL)
    assert cands[0].confidence is Confidence.HIGH
    assert cands[0].type is CandidateType.FORM


def test_form_without_visible_inputs_is_low():
    assert build_candidates([_form(hasVisibleInputs=False)], URL)[0].confidence is Confidence.LOW


def test_action_button_high_cosmetic_button_low():
    raw = [
        _button(text="Add to cart", classId="add-to-cart"),
        _button(text="Accept cookies", classId="cookie-accept"),
    ]
    cands = build_candidates(raw, URL)
    assert cands[0].confidence is Confidence.HIGH
    assert cands[1].confidence is Confidence.LOW


def test_ids_are_sequential_over_included_only():
    raw = [_form(), _form(displayNone=True), _button(text="Buy")]
    ids = [c.id for c in build_candidates(raw, URL)]
    assert ids == ["c1", "c2"]  # hidden one consumed no id


def _ot_token(feature: str, sig: bytes = b"\x00" * 64) -> str:
    """Build a realistic origin-trial token whose payload names `feature`.

    `sig` overrides the 64-byte signature region so tests can reproduce real tokens whose
    signature bytes happen to contain `{`/`}` (which broke a naive brace search).
    """
    import base64
    import json

    payload = json.dumps({"feature": feature, "origin": "https://ex.com"}).encode()
    raw = b"\x03" + sig[:64].ljust(64, b"\x00") + len(payload).to_bytes(4, "big") + payload
    return base64.b64encode(raw).decode()


def test_origin_trial_decode_ignores_braces_in_signature():
    # Regression: the 64-byte signature can contain `{`/`}`; the decoder must skip it and
    # parse only the JSON payload (a live reCAPTCHA token exposed this).
    token = _ot_token("WebMCP", sig=b"\x03\xbb#{noise}\x7d" + b"\xff" * 40)
    _, _, features, is_webmcp = detect_origin_trial(
        f'<meta http-equiv="origin-trial" content="{token}">', {}
    )
    assert features == ["WebMCP"] and is_webmcp is True


def test_no_origin_trial():
    assert detect_origin_trial("", {}) == (False, None, [], False)


def test_origin_trial_decodes_webmcp_feature():
    html = f'<meta http-equiv="origin-trial" content="{_ot_token("WebMCP")}">'
    advertised, source, features, is_webmcp = detect_origin_trial(html, {})
    assert (advertised, source, is_webmcp) == (True, "meta", True)
    assert features == ["WebMCP"]


def test_origin_trial_non_webmcp_feature_not_flagged():
    # e.g. a token injected by an embedded reCAPTCHA widget — present but unrelated.
    token = _ot_token("DisableThirdPartyStoragePartitioning3")
    advertised, source, features, is_webmcp = detect_origin_trial("", {"Origin-Trial": token})
    assert (advertised, source, is_webmcp) == (True, "header", False)
    assert features == ["DisableThirdPartyStoragePartitioning3"]


def test_origin_trial_webmcp_match_is_exact_not_substring():
    # A feature that merely contains "webmcp" must NOT be flagged (guards the exact match).
    token = _ot_token("MyWebMCPExtension")
    _, _, features, is_webmcp = detect_origin_trial(
        f'<meta http-equiv="origin-trial" content="{token}">', {}
    )
    assert features == ["MyWebMCPExtension"] and is_webmcp is False


def test_origin_trial_undecodable_token_is_advertised_but_undetermined():
    html = '<meta content="not-a-real-token" http-equiv="origin-trial">'  # attr order reversed
    advertised, source, features, is_webmcp = detect_origin_trial(html, {})
    assert (advertised, source, features, is_webmcp) == (True, "meta", [], False)


def test_page_language_from_html_lang():
    assert detect_page_language('<html lang="en">', {}) == "en"
    assert detect_page_language("<html LANG='NL-BE'>", {}) == "nl-be"
    assert detect_page_language('<html class="x" lang="fr">', {}) == "fr"


def test_page_language_falls_back_to_content_language_header():
    assert detect_page_language("<html>", {"Content-Language": "nl-BE, fr"}) == "nl-be"
    assert detect_page_language("<html>", {"content-language": "de"}) == "de"


def test_html_lang_wins_over_header():
    assert detect_page_language('<html lang="en">', {"Content-Language": "fr"}) == "en"


def test_page_language_none_when_undeterminable():
    assert detect_page_language("<html>", {}) is None
    assert detect_page_language("", {}) is None


def test_is_cross_origin():
    base = "https://gct.lu/reservations/"
    assert is_cross_origin(base, "https://bookings.zenchef.com/results") is True
    assert is_cross_origin(base, "https://gct.lu/other") is False  # same origin
    assert is_cross_origin(base, "https://sub.gct.lu/x") is True  # different host
    assert is_cross_origin(base, "about:srcdoc") is False  # part of the page
    assert is_cross_origin(base, "") is False


def test_owner_instrumentable_reflects_cross_origin():
    same = _form(frameUrl="https://gct.lu/", crossOrigin=False)
    third = _form(frameUrl="https://bookings.zenchef.com/", crossOrigin=True)
    cands = build_candidates([same, third], "https://gct.lu/")
    assert cands[0].owner_instrumentable is True
    assert cands[1].owner_instrumentable is False
    assert cands[1].frame_url == "https://bookings.zenchef.com/"
