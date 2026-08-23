"""Anchor Browser cloud provider — plugin form.

Subclasses :class:`agent.browser_provider.BrowserProvider`. Creates a cloud
Chromium session via ``POST /v1/sessions`` and returns the CDP websocket URL
Hermes already drives through ``agent-browser``.

Auth::

    ANCHOR_API_KEY=...              # https://app.anchorbrowser.io/api-keys
    ANCHORBROWSER_API_KEY=...       # SDK alias, also accepted
    ANCHOR_IDENTITY_TOKEN=...       # optional; Agent Access identity header

No dashboard account? Obtain a key through Agent Access (token TTL ~120s)::

    hermes anchorbrowser challenge
    hermes anchorbrowser submit <token> <answer>

    Docs: https://docs.anchorbrowser.io/quickstart/agent-access

Optional session knobs (env, default off — proxy traffic is billed)::

    ANCHOR_PROXY=true
    ANCHOR_STEALTH=true             # requires proxy; enabled automatically
    ANCHOR_CAPTCHA=true             # requires proxy; enabled automatically
    ANCHOR_SESSION_TIMEOUT_MINUTES  # default 20; Agent Access keys cap at 60
    ANCHOR_BASE_URL                 # default https://api.anchorbrowser.io
    ANCHOR_IDENTITY_ID              # attach a managed identity at create
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

from agent.browser_provider import BrowserProvider
from agent.secret_scope import get_secret

from .agent_access import _DOCS

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.anchorbrowser.io"
_DEFAULT_TIMEOUT_MINUTES = 20
_AGENT_ACCESS_MAX_MINUTES = 60
_API_KEY_HINT = (
    "Anchor Browser requires ANCHOR_API_KEY. Get one at "
    "https://app.anchorbrowser.io/api-keys or as an agent: "
    f"hermes anchorbrowser challenge  (then submit). Docs: {_DOCS}"
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _read_api_key() -> Optional[str]:
    try:
        return get_secret("ANCHOR_API_KEY") or get_secret("ANCHORBROWSER_API_KEY")
    except Exception:
        return None


class AnchorBrowserProvider(BrowserProvider):
    """Anchor Browser (https://anchorbrowser.io) cloud Chromium backend."""

    @property
    def name(self) -> str:
        return "anchorbrowser"

    @property
    def display_name(self) -> str:
        return "Anchor Browser"

    def is_available(self) -> bool:
        return bool(_read_api_key())

    def _get_config_or_none(self) -> Optional[Dict[str, Any]]:
        api_key = _read_api_key()
        if not api_key:
            return None
        try:
            identity = get_secret("ANCHOR_IDENTITY_TOKEN")
        except Exception:
            identity = None
        return {
            "api_key": api_key,
            "identity_token": identity,
            "base_url": os.environ.get("ANCHOR_BASE_URL", _DEFAULT_BASE_URL).rstrip("/"),
        }

    def _get_config(self) -> Dict[str, Any]:
        config = self._get_config_or_none()
        if config is None:
            raise ValueError(_API_KEY_HINT)
        return config

    def _headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "anchor-api-key": config["api_key"],
        }
        if config.get("identity_token"):
            headers["anchor-identity-token"] = config["identity_token"]
        return headers

    def create_session(self, task_id: str) -> Dict[str, object]:
        config = self._get_config()

        enable_proxy = _truthy("ANCHOR_PROXY")
        enable_stealth = _truthy("ANCHOR_STEALTH")
        enable_captcha = _truthy("ANCHOR_CAPTCHA")
        if (enable_stealth or enable_captcha) and not enable_proxy:
            logger.info(
                "Anchor stealth/captcha require proxy; enabling ANCHOR_PROXY for this session"
            )
            enable_proxy = True

        try:
            timeout_minutes = int(
                os.environ.get("ANCHOR_SESSION_TIMEOUT_MINUTES", _DEFAULT_TIMEOUT_MINUTES)
            )
        except (TypeError, ValueError):
            timeout_minutes = _DEFAULT_TIMEOUT_MINUTES
        timeout_minutes = max(1, min(timeout_minutes, _AGENT_ACCESS_MAX_MINUTES))

        session_block: Dict[str, Any] = {
            "tags": ["hermes", str(task_id)[:48]],
            "recording": {"active": False},
            "timeout": {
                "max_duration": timeout_minutes,
                "idle_timeout": min(5, timeout_minutes),
            },
        }
        if enable_proxy:
            session_block["proxy"] = {"active": True}

        browser_block: Dict[str, Any] = {}
        if enable_stealth:
            browser_block["extra_stealth"] = {"active": True}
        if enable_captcha:
            browser_block["captcha_solver"] = {"active": True}

        body: Dict[str, Any] = {"session": session_block}
        if browser_block:
            body["browser"] = browser_block
        identity_id = os.environ.get("ANCHOR_IDENTITY_ID", "").strip()
        if identity_id:
            body["identities"] = [{"id": identity_id}]

        try:
            response = requests.post(
                f"{config['base_url']}/v1/sessions",
                headers=self._headers(config),
                json=body,
                timeout=60,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Anchor Browser API connection failed: {exc}") from exc

        if not response.ok:
            raise RuntimeError(
                f"Failed to create Anchor Browser session: "
                f"{response.status_code} {response.text}"
            )

        payload = response.json()
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        session_id = data.get("id") or data.get("session_id")
        cdp_url = data.get("cdp_url") or data.get("cdpUrl") or ""
        if not session_id or not cdp_url:
            raise RuntimeError(
                f"Anchor Browser session response missing id/cdp_url: {payload!r}"
            )

        session_name = f"hermes_{task_id}_{uuid.uuid4().hex[:8]}"
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
        ).isoformat()
        features = {
            "anchorbrowser": True,
            "proxy": enable_proxy,
            "extra_stealth": enable_stealth,
            "captcha_solver": enable_captcha,
        }
        logger.info(
            "Created Anchor Browser session %s (%s)",
            session_name,
            ", ".join(k for k, v in features.items() if v),
        )
        return {
            "session_name": session_name,
            "bb_session_id": session_id,
            "cdp_url": cdp_url,
            "expires_at": expires_at,
            "features": features,
        }

    def close_session(self, session_id: str) -> bool:
        try:
            config = self._get_config()
        except ValueError:
            logger.warning(
                "Cannot close Anchor Browser session %s — missing credentials",
                session_id,
            )
            return False
        try:
            response = requests.delete(
                f"{config['base_url']}/v1/sessions/{session_id}",
                headers=self._headers(config),
                timeout=10,
            )
            if response.status_code in {200, 201, 204}:
                logger.debug("Closed Anchor Browser session %s", session_id)
                return True
            logger.warning(
                "Failed to close Anchor Browser session %s: HTTP %s - %s",
                session_id,
                response.status_code,
                response.text[:200],
            )
            return False
        except Exception as exc:
            logger.error("Exception closing Anchor Browser session %s: %s", session_id, exc)
            return False

    def emergency_cleanup(self, session_id: str) -> None:
        config = self._get_config_or_none()
        if config is None:
            logger.warning(
                "Cannot emergency-cleanup Anchor Browser session %s — missing credentials",
                session_id,
            )
            return
        try:
            requests.delete(
                f"{config['base_url']}/v1/sessions/{session_id}",
                headers=self._headers(config),
                timeout=5,
            )
        except Exception as exc:
            logger.debug(
                "Emergency cleanup failed for Anchor Browser session %s: %s",
                session_id,
                exc,
            )

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Anchor Browser",
            "badge": "paid",
            "tag": "Cloud Chromium (CDP). Key via dashboard or hermes anchorbrowser challenge",
            "env_vars": [
                {
                    "key": "ANCHOR_API_KEY",
                    "prompt": "Anchor API key",
                    "url": "https://app.anchorbrowser.io/api-keys",
                },
            ],
            # Shared cloud-CLI hook id so Desktop's allowlist accepts the
            # button. register() wraps _run_post_setup so this cannot
            # succeed unless ANCHOR_API_KEY is present and accepted.
            "post_setup": "browserbase",
        }
