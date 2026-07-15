"""Runtime configuration from environment (T009).

No secrets are hard-coded or committed. Secrets live in a repo-local `.env`
(git-ignored, see `.env.example`) that is loaded into this process only — they
are deliberately NOT exported from the shell profile, because a shell-wide
`ANTHROPIC_API_KEY` outranks the Claude Code subscription login and silently
bills API credits for every `claude` invocation.

An explicitly-set environment variable still wins over `.env`, so a one-off
`ANTHROPIC_API_KEY=... webmcp-instrument draft ...` keeps working.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    """Load the repo-local `.env` (searching upward from the cwd), if present."""
    load_dotenv(find_dotenv(usecwd=True), override=False)


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    anthropic_model: str
    sink_url: str | None
    crawl_timeout_s: float

    @classmethod
    def from_env(cls) -> Config:
        load_env()
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            # Sonnet is sufficient for schema drafting (research D3).
            anthropic_model=os.environ.get("WEBMCP_DRAFT_MODEL", "claude-sonnet-5"),
            sink_url=os.environ.get("WEBMCP_SINK_URL"),
            crawl_timeout_s=float(os.environ.get("WEBMCP_CRAWL_TIMEOUT_S", "30")),
        )

    def require_anthropic_key(self) -> str:
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set — required for the `draft` stage. "
                "Copy .env.example to .env and put the key there (do not export it "
                "from your shell profile: that would override your Claude Code login)."
            )
        return self.anthropic_api_key
