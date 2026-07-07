"""Runtime configuration from environment (T009).

No secrets are hard-coded or committed. The Anthropic key is read from the
environment only when `draft` actually needs it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    anthropic_model: str
    sink_url: str | None
    crawl_timeout_s: float

    @classmethod
    def from_env(cls) -> Config:
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
                "Export it or pass a different --provider."
            )
        return self.anthropic_api_key
