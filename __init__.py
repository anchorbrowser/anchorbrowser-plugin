"""Hermes plugin — cloud browser backend + bundled skill."""

from __future__ import annotations

from pathlib import Path

from .agent_access import (
    anchor_command,
    install_post_setup_hook,
    register_cli,
)
from .provider import AnchorBrowserProvider


def register(ctx) -> None:
    install_post_setup_hook()
    ctx.register_browser_provider(AnchorBrowserProvider())
    ctx.register_cli_command(
        name="anchorbrowser",
        help="Anchor Browser Agent Access (obtain ANCHOR_API_KEY without a dashboard account)",
        setup_fn=register_cli,
        handler_fn=anchor_command,
        description=(
            "Self-serve Anchor API key via Agent Access, then use "
            "browser.cloud_provider: anchorbrowser. "
            "See https://docs.anchorbrowser.io/quickstart/agent-access"
        ),
    )
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)
