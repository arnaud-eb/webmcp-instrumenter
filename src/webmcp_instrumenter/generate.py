"""US3 generate stage (T022–T026).

Emits code ONLY for contracts with review_status == "approved" (Constitution
Principle I — the human gate). Produces, per approved contract, a declarative
attribute snippet or an imperative registerTool() block; plus a `.well-known/webmcp`
manifest of exactly the approved tools and a non-blocking `logger.js`.
No secrets are ever embedded (FR-007).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import Config
from .io import load_json
from .models import Api, Contract

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(  # noqa: S701 - output is JS/JSON, not HTML; autoescape off intentionally
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=False,
    keep_trailing_newline=True,
)


@dataclass
class GenerateSummary:
    approved: int
    declarative: int
    imperative: int


def _attr_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _declarative_snippet(c: Contract) -> str:
    props = (c.input_schema or {}).get("properties", {})
    lines = [
        f"<!-- Declarative WebMCP tool for candidate {c.candidate_id}. "
        "Apply these attributes to your REAL <form>/inputs (match inputs by name). -->",
        f'<form toolname="{c.tool_name}"',
        f'      tooldescription="{_attr_escape(c.description)}">',
    ]
    for name, spec in props.items():
        desc = spec.get("description", name) if isinstance(spec, dict) else name
        lines.append(f'  <input name="{name}" toolparamdescription="{_attr_escape(str(desc))}">')
    lines.append('  <button type="submit">Submit</button>')
    lines.append("</form>")
    return "\n".join(lines) + "\n"


def _imperative_snippet(c: Contract) -> str:
    name = json.dumps(c.tool_name)
    return f"""// Imperative WebMCP tool for candidate {c.candidate_id}.
navigator.modelContext.registerTool({{
  name: {name},
  description: {json.dumps(c.description)},
  inputSchema: {json.dumps(c.input_schema, indent=2)},
  async execute(params) {{
    var keys = Object.keys(params || {{}});  // key names only
    try {{
      // TODO: perform the real action for this tool using `params`.
      window.webmcpLog && window.webmcpLog({name}, true, keys);
      return {{ success: true }};
    }} catch (e) {{
      window.webmcpLog && window.webmcpLog({name}, false, keys);
      throw e;
    }}
  }}
}});
"""


def generate(contracts_path: str | Path, out_dir: str | Path) -> GenerateSummary:
    contracts = [Contract.from_dict(d) for d in load_json(contracts_path)]
    approved = [c for c in contracts if c.is_approved]
    if not approved:
        return GenerateSummary(0, 0, 0)  # human gate: nothing approved → nothing emitted

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_decl = n_imp = 0
    for c in approved:
        if c.api is Api.DECLARATIVE:
            (out / f"{c.tool_name}.declarative.html").write_text(_declarative_snippet(c))
            n_decl += 1
        else:
            (out / f"{c.tool_name}.imperative.js").write_text(_imperative_snippet(c))
            n_imp += 1

    # Manifest of exactly the approved tools.
    tools = [
        {"name": c.tool_name, "description": c.description, "inputSchema": c.input_schema}
        for c in approved
    ]
    manifest = _env.get_template("manifest.json.j2").render(tools_json=json.dumps(tools, indent=2))
    well_known = out / ".well-known"
    well_known.mkdir(parents=True, exist_ok=True)
    (well_known / "webmcp").write_text(manifest)

    # Non-blocking logger (public sink URL only — no secrets).
    sink = Config.from_env().sink_url or "https://REPLACE_WITH_YOUR_SINK_URL/events"
    logger = _env.get_template("logger.js.j2").render(sink_url=json.dumps(sink))
    (out / "logger.js").write_text(logger)

    return GenerateSummary(approved=len(approved), declarative=n_decl, imperative=n_imp)
