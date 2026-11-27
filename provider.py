"""Anchor Browser cloud browser provider for Hermes.

``create_session`` starts one Anchor browser session per task and returns its CDP URL; Hermes
drives the page from there. The API key is sent only to the configured Anchor API host.

Every setting is read as ``ANCHOR_<NAME>``, with ``ANCHORBROWSER_<NAME>`` accepted as an alias.
The full list is in ``docs/hermes.md``. No dashboard account? ``hermes anchorbrowser setup``
obtains a key through Agent Access.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.browser_provider import BrowserProvider
from agent.secret_scope import get_secret

from .agent_access import _DOCS

logger = logging.getLogger(__name__)

_DEFAULT_BASE = "https://api.anchorbrowser.io"
_KEY_URL = "https://app.anchorbrowser.io/api-keys"
_EXPIRY_MARGIN_S = 5
_DEFAULT_MAX_DURATION = 20
_DEFAULT_IDLE_TIMEOUT = 5
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")
_PLAN_FEATURES: Tuple[Tuple[str, str], ...] = (
    ("extra_stealth", "Extra stealth is not available on this Anchor plan; retrying without it."),
    ("captcha_solver", "Captcha solving is not available on this Anchor plan; retrying without it."),
)
_SCOPED_ACCESS = (("scoped_access", "Scoped access tokens were refused; retrying with a plain session URL."),)
_FALLBACKS = {402: _PLAN_FEATURES, 403: _PLAN_FEATURES, 400: _SCOPED_ACCESS}


class AnchorAPIError(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(request: urllib.request.Request, timeout: float):
    try:
        from hermes_cli.urllib_security import open_credentialed_url
    except Exception:
        return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)
    return open_credentialed_url(request, timeout=timeout)


_LEGACY_NAMES = {
    "CAPTCHA_SOLVER": ("ANCHOR_CAPTCHA",),
    "EXTRA_STEALTH": ("ANCHOR_STEALTH",),
    "MAX_DURATION": ("ANCHOR_SESSION_TIMEOUT_MINUTES",),
    "IDENTITIES": ("ANCHOR_IDENTITY_ID",),
}


def setting_names(suffix: str) -> Tuple[str, ...]:
    return (f"ANCHOR_{suffix}", f"ANCHORBROWSER_{suffix}", *_LEGACY_NAMES.get(suffix, ()))


def _setting(suffix: str, default: Optional[str] = None) -> Optional[str]:
    for name in setting_names(suffix):
        try:
            value = get_secret(name, None)
        except Exception:
            value = None
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _bool_setting(name: str, default: Optional[bool]) -> Optional[bool]:
    value = _setting(name)
    if value is None:
        return default
    lowered = value.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    logger.warning("Ignoring ANCHOR_%s=%r: expected true or false", name, value)
    return default


def _int_setting(name: str) -> Optional[int]:
    value = _setting(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        logger.warning("Ignoring ANCHOR_%s=%r: expected a whole number", name, value)
        return None


def _plugin_version() -> str:
    try:
        text = (Path(__file__).parent / "plugin.yaml").read_text(encoding="utf-8")
        return re.search(r"^version:\s*['\"]?([^'\"\s]+)", text, re.M).group(1)
    except Exception:
        return "unknown"


def redact(text: str) -> str:
    text = re.sub(r"sk-[A-Za-z0-9]{8,}", "sk-<redacted>", str(text))
    return re.sub(r"((?:token|apiKey|sessionId|rt|viewerId)=)[^&\s\"']+", r"\1<redacted>", text)


def _list_setting(name: str) -> List[str]:
    return [part.strip() for part in (_setting(name) or "").split(",") if part.strip()]


def _merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _extra_payload() -> Dict[str, Any]:
    raw = _setting("SESSION_JSON")
    if not raw:
        return {}
    try:
        extra = json.loads(raw)
    except ValueError:
        extra = None
    if not isinstance(extra, dict):
        logger.warning("Ignoring ANCHOR_SESSION_JSON: expected a JSON object")
        return {}
    return extra


_BROWSER_SWITCHES = (
    ("POPUP_BLOCKER", "popup_blocker"),
    ("FULLSCREEN", "fullscreen"),
    ("PDF_VIEWER", "pdf_viewer"),
    ("P2P_DOWNLOAD", "p2p_download"),
    ("DISABLE_WEB_SECURITY", "disable_web_security"),
)


def build_session_payload(task_id: str = "") -> Tuple[Dict[str, Any], Dict[str, bool]]:
    tags = ["hermes"]
    if task_id:
        tags.append(str(task_id)[:48])
    tags += [tag for tag in _list_setting("TAGS") if tag not in tags]
    session: Dict[str, Any] = {"tags": tags}
    browser: Dict[str, Any] = {}

    country = (_setting("PROXY_COUNTRY") or "").lower()
    region = _setting("PROXY_REGION")
    city = _setting("PROXY_CITY")
    custom_server = _setting("PROXY_SERVER")
    captcha = bool(_bool_setting("CAPTCHA_SOLVER", False))
    extra_stealth = bool(_bool_setting("EXTRA_STEALTH", False))
    anchor_proxy = not custom_server and (
        bool(_bool_setting("PROXY", False)) or bool(country or region or city)
    )
    if (captcha or extra_stealth) and not custom_server and not anchor_proxy:
        logger.info("Anchor captcha solving and extra stealth need a proxy; turning the Anchor proxy on for this session")
        anchor_proxy = True
    if custom_server:
        session["proxy"] = {
            "active": True,
            "type": "custom",
            "server": custom_server,
            "username": _setting("PROXY_USERNAME", "") or "",
            "password": _setting("PROXY_PASSWORD", "") or "",
        }
    elif anchor_proxy:
        proxy_config: Dict[str, Any] = {"active": True, "type": "anchor_proxy"}
        if country:
            proxy_config["country_code"] = country
        if region:
            proxy_config["region"] = region
        if city:
            proxy_config["city"] = city
        session["proxy"] = proxy_config
    if extra_stealth and not anchor_proxy:
        logger.warning("ANCHOR_EXTRA_STEALTH needs the Anchor proxy, not your own proxy server. Leaving it off.")
        extra_stealth = False
    if captcha:
        browser["captcha_solver"] = {"active": True}
    if extra_stealth:
        browser["extra_stealth"] = {"active": True}

    headless = bool(_bool_setting("HEADLESS", False))
    if headless:
        browser["headless"] = {"active": True}

    adblock = _bool_setting("ADBLOCK", None)
    if adblock is not None:
        browser["adblock"] = {"active": adblock}
        if not adblock:
            browser["popup_blocker"] = {"active": False}
    for name, key in _BROWSER_SWITCHES:
        value = _bool_setting(name, None)
        if value is not None and not (key == "popup_blocker" and adblock is False):
            browser[key] = {"active": value}

    viewport = re.fullmatch(r"(\d{2,5})\s*[xX]\s*(\d{2,5})", _setting("VIEWPORT") or "")
    if viewport:
        browser["viewport"] = {"width": int(viewport.group(1)), "height": int(viewport.group(2))}
    elif _setting("VIEWPORT"):
        logger.warning("Ignoring ANCHOR_VIEWPORT: expected WIDTHxHEIGHT, for example 1440x900")

    extensions = _list_setting("EXTENSIONS")
    if extensions:
        browser["extensions"] = extensions
    volume = _setting("VOLUME_ID")
    if volume:
        browser["volume"] = {"id": volume, "read_only": bool(_bool_setting("VOLUME_READ_ONLY", False))}

    profile = _setting("PROFILE")
    persist = bool(_bool_setting("PROFILE_PERSIST", False))
    if profile:
        browser["profile"] = {"name": profile, "persist": persist}

    initial_url = _setting("INITIAL_URL")
    if initial_url:
        session["initial_url"] = initial_url
    allowlist = _list_setting("DOMAIN_ALLOWLIST")
    if allowlist:
        session["domain_allowlist"] = allowlist
    session["recording"] = {"active": bool(_bool_setting("RECORDING", False))}
    live_view_read_only = _bool_setting("LIVE_VIEW_READ_ONLY", None)
    if live_view_read_only is not None:
        session["live_view"] = {"read_only": live_view_read_only}

    max_duration = _int_setting("MAX_DURATION")
    if max_duration is None or max_duration == 0:
        max_duration = _DEFAULT_MAX_DURATION
    idle_timeout = _int_setting("IDLE_TIMEOUT")
    if idle_timeout is None or idle_timeout == 0:
        idle_timeout = min(_DEFAULT_IDLE_TIMEOUT, max_duration) if max_duration > 0 else _DEFAULT_IDLE_TIMEOUT
    session["timeout"] = {"max_duration": max_duration, "idle_timeout": idle_timeout}

    scoped = bool(_bool_setting("SCOPED_ACCESS", True)) and not headless
    if scoped:
        session["scoped_access"] = {"active": True}

    payload: Dict[str, Any] = {"session": session}
    if browser:
        payload["browser"] = browser
    identities = _list_setting("IDENTITIES")
    if identities:
        payload["identities"] = [{"id": identity} for identity in identities]
        validate = _bool_setting("IDENTITY_VALIDATE", None)
        if validate is not None:
            payload["identity_skip_validation"] = not validate

    extra = _extra_payload()
    if extra:
        _merge(payload, extra)
        payload.setdefault("session", {})
    merged_session = payload["session"] if isinstance(payload.get("session"), dict) else {}
    merged_browser = payload["browser"] if isinstance(payload.get("browser"), dict) else {}

    def active(section: Dict[str, Any], key: str) -> bool:
        value = section.get(key)
        return isinstance(value, dict) and bool(value.get("active"))

    features = {
        "anchorbrowser": True,
        "proxy": active(merged_session, "proxy"),
        "captcha_solver": active(merged_browser, "captcha_solver"),
        "extra_stealth": active(merged_browser, "extra_stealth"),
        "profile": bool((merged_browser.get("profile") or {}).get("name")),
        "profile_persist": bool((merged_browser.get("profile") or {}).get("persist")),
        "identities": bool(payload.get("identities")),
        "headless": active(merged_browser, "headless"),
        "scoped_access": active(merged_session, "scoped_access"),
        "custom_config": bool(extra),
    }
    return payload, features


def _drop_feature(payload: Dict[str, Any], feature: str) -> bool:
    section = payload.get("session") if feature == "scoped_access" else payload.get("browser")
    return isinstance(section, dict) and section.pop(feature, None) is not None


def _explain(error: Exception) -> str:
    if isinstance(error, AnchorAPIError):
        if error.status == 401:
            return f"Anchor Browser rejected the API key (HTTP 401). Check ANCHOR_API_KEY ({_KEY_URL}) or run: hermes anchorbrowser setup"
        if error.status == 429:
            return "Anchor Browser rate or concurrency limit reached (HTTP 429). Close other sessions or retry shortly."
        return f"Anchor Browser refused the session: {error}"
    return f"{type(error).__name__}: {error}"


class AnchorBrowserProvider(BrowserProvider):
    @property
    def name(self) -> str:
        return "anchorbrowser"

    @property
    def display_name(self) -> str:
        return "Anchor Browser"

    def is_available(self) -> bool:
        return bool(_setting("API_KEY"))

    def _base_url(self) -> str:
        base = (_setting("BASE_URL", _DEFAULT_BASE) or _DEFAULT_BASE).rstrip("/")
        if not base.startswith("https://"):
            raise ValueError("ANCHOR_BASE_URL must start with https://")
        return base

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]], timeout: float) -> Dict[str, Any]:
        api_key = _setting("API_KEY")
        if not api_key:
            raise ValueError(
                f"Anchor Browser requires ANCHOR_API_KEY. Get one at {_KEY_URL} or as an agent: "
                f"hermes anchorbrowser setup. Docs: {_DOCS}"
            )
        headers = {
            "anchor-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"hermes-anchorbrowser/{_plugin_version()}",
        }
        identity_token = _setting("IDENTITY_TOKEN")
        if identity_token:
            headers["anchor-identity-token"] = identity_token
        request = urllib.request.Request(
            f"{self._base_url()}{path}",
            method=method,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
        )
        try:
            with _open(request, timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300] if error.fp else ""
            error.close()
            raise AnchorAPIError(error.code, redact(detail)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"Anchor Browser API connection failed: {redact(str(error))}") from None
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            raise RuntimeError("Anchor Browser API returned a reply that is not JSON") from None

    def _create(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        dropped: List[str] = []
        while True:
            try:
                return self._request("POST", "/v1/sessions", payload, timeout=45), dropped
            except AnchorAPIError as error:
                candidates = _FALLBACKS.get(error.status, ())
                if error.status == 400 and "scoped" not in error.detail.lower():
                    candidates = ()
                for feature, warning in candidates:
                    if _drop_feature(payload, feature):
                        logger.warning("%s (%s)", warning, error)
                        dropped.append(feature)
                        break
                else:
                    raise

    def create_session(self, task_id: str) -> Dict[str, object]:
        payload, features = build_session_payload(task_id)
        started = datetime.now(timezone.utc)
        try:
            reply, dropped = self._create(payload)
        except ValueError:
            raise
        except Exception as error:
            raise RuntimeError(redact(_explain(error))) from None

        data = reply.get("data") or {}
        session_id, cdp_url = data.get("id"), data.get("cdp_url")
        if not session_id or not cdp_url:
            if session_id:
                self.close_session(str(session_id))
            raise RuntimeError("Anchor Browser did not return a session id and CDP URL")
        for feature in dropped:
            features[feature] = False

        session_name = f"hermes_{task_id}_{uuid.uuid4().hex[:8]}"
        enabled = ", ".join(key for key, value in features.items() if value)
        logger.info("Created Anchor Browser session %s (%s) with features: %s", session_name, session_id, enabled)
        if _bool_setting("SHOW_LIVE_VIEW", False):
            live_view = data.get("live_view_read_only_url") or data.get("live_view_url")
            if live_view:
                logger.info("Anchor Browser live view for %s: %s", session_name, live_view)

        result: Dict[str, object] = {
            "session_name": session_name,
            "bb_session_id": str(session_id),
            "cdp_url": str(cdp_url),
            "features": features,
        }
        max_duration = (payload.get("session", {}).get("timeout") or {}).get("max_duration")
        if isinstance(max_duration, int) and max_duration > 0:
            result["expires_at"] = (started + timedelta(minutes=max_duration, seconds=-_EXPIRY_MARGIN_S)).isoformat()
        return result

    def _delete(self, session_id: str, timeout: float) -> bool:
        try:
            self._request("DELETE", f"/v1/sessions/{session_id}", None, timeout=timeout)
            return True
        except AnchorAPIError as error:
            if error.status == 404:
                return True
            raise

    def close_session(self, session_id: str) -> bool:
        try:
            closed = self._delete(session_id, timeout=15)
            logger.debug("Closed Anchor Browser session %s", session_id)
            return closed
        except Exception as error:
            logger.warning("Failed to close Anchor Browser session %s: %s", session_id, redact(str(error)))
            return False

    def emergency_cleanup(self, session_id: str) -> None:
        try:
            self._delete(session_id, timeout=5)
        except Exception as error:
            logger.debug("Emergency cleanup failed for Anchor Browser session %s: %s", session_id, redact(str(error)))

    def get_setup_schema(self) -> Optional[Dict[str, Any]]:
        return {
            "name": self.display_name,
            "badge": "paid",
            "tag": "Cloud Chromium (CDP). Key via dashboard or hermes anchorbrowser setup",
            "env_vars": [{"key": "ANCHOR_API_KEY", "prompt": "Anchor API key", "url": _KEY_URL}],
            "post_setup": "browserbase",
        }
