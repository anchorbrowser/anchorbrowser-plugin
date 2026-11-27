"""Anchor Agent Access — unauthenticated API-key onboarding.

Docs: https://docs.anchorbrowser.io/quickstart/agent-access

State machine (follow ``next`` on every response)::

    GET /v1/agent-access              # optional guide
    GET /v1/agent-access/challenge    # puzzle + token (+ often a GET appendix)
    GET /v1/agent-access/appendix/…   # inventory the prompt tells you to fetch
    POST /v1/agent-access             # {token, answer} → api_key

Challenge tokens expire in ~120s. This module never tries to solve the
puzzle — it fetches, follows GET ``next`` hops, and submits the caller's
answer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

_API_ROOT = "https://api.anchorbrowser.io"
_DOCS = "https://docs.anchorbrowser.io/quickstart/agent-access"
_KEY_NAMES = ("ANCHOR_API_KEY", "ANCHORBROWSER_API_KEY")
_MAX_GET_HOPS = 6


def _url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(_API_ROOT + "/", path.lstrip("/"))


def api_request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> Dict[str, Any]:
    """Unauthenticated Agent Access HTTP call. Raises RuntimeError on failure."""
    try:
        response = requests.request(
            method.upper(),
            _url(path),
            json=json_body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Anchor Agent Access request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text[:500]}

    if not isinstance(payload, dict):
        payload = {"data": payload}

    if not response.ok:
        err = payload.get("error")
        if isinstance(err, dict):
            message = err.get("message") or json.dumps(err)
        else:
            message = err or response.text[:300]
        raise RuntimeError(
            f"Anchor Agent Access {method.upper()} {path} failed "
            f"({response.status_code}): {message}\nDocs: {_DOCS}"
        )
    return payload


def follow_get_nexts(
    payload: Dict[str, Any],
    *,
    max_hops: int = _MAX_GET_HOPS,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Follow GET ``next`` hops. Stop before any POST (caller supplies the answer).

    Returns ``(original_payload, extras)`` so the challenge token is never
    overwritten by an appendix response.
    """
    extras: List[Dict[str, Any]] = []
    seen: set[str] = set()
    nxt = payload.get("next") if isinstance(payload, dict) else None
    hops = 0
    while (
        isinstance(nxt, dict)
        and str(nxt.get("method") or "").upper() == "GET"
        and hops < max_hops
    ):
        path = str(nxt.get("path") or "").strip()
        if not path or path in seen:
            break
        seen.add(path)
        extra = api_request("GET", path)
        extras.append({"path": path, "data": extra})
        hops += 1
        nxt = extra.get("next") if isinstance(extra, dict) else None
    return payload, extras


def fetch_guide() -> Dict[str, Any]:
    return api_request("GET", "/v1/agent-access")


def fetch_challenge() -> Dict[str, Any]:
    """GET the puzzle, then any GET appendix ``next`` hops."""
    payload, extras = follow_get_nexts(api_request("GET", "/v1/agent-access/challenge"))
    out = dict(payload)
    if extras:
        out["fetched"] = extras
    return out


def submit_answer(
    token: str,
    answer: str,
    *,
    identity_token: Optional[str] = None,
    identity_provider: Optional[str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"token": token, "answer": str(answer)}
    if identity_token:
        body["identity_token"] = identity_token
        if identity_provider:
            body["identity_provider"] = identity_provider
    return api_request("POST", "/v1/agent-access", json_body=body)


def current_api_key() -> Optional[str]:
    try:
        from agent.secret_scope import get_secret

        return get_secret("ANCHOR_API_KEY") or get_secret("ANCHORBROWSER_API_KEY")
    except Exception:
        return (
            os.environ.get("ANCHOR_API_KEY")
            or os.environ.get("ANCHORBROWSER_API_KEY")
            or None
        )


def persist_pasted_key(api_key: str) -> str:
    key = str(api_key or "").strip()
    if not key:
        raise RuntimeError("No API key provided.")
    from hermes_cli.config import save_env_value

    for name in _KEY_NAMES:
        save_env_value(name, key)
        os.environ[name] = key
    return key


def verify_api_key(api_key: str, *, base_url: Optional[str] = None) -> None:
    """Reject missing/invalid keys. A 404 on list is fine — we only fail auth."""
    url = (base_url or _API_ROOT).rstrip("/") + "/v1/sessions"
    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "anchor-api-key": api_key,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not verify ANCHOR_API_KEY: {exc}") from exc
    if response.status_code in (401, 403):
        raise RuntimeError(
            "ANCHOR_API_KEY was rejected by Anchor. Get a new one at "
            "https://app.anchorbrowser.io/api-keys or run: "
            "hermes anchorbrowser setup"
        )


def _tty() -> bool:
    return bool(
        getattr(sys.stdin, "isatty", lambda: False)()
        and getattr(sys.stdout, "isatty", lambda: False)()
    )


def run_setup() -> None:
    """Require a live ANCHOR_API_KEY. Used by ``hermes anchorbrowser setup``.

    Without a TTY a missing key fails instead of reporting success. A terminal
    can paste a key or finish Agent Access.
    """
    print("Anchor Browser setup requires a valid ANCHOR_API_KEY.")
    key = current_api_key()
    if not key and _tty():
        try:
            print("Dashboard keys: https://app.anchorbrowser.io/api-keys")
            print(f"Agent Access:   {_DOCS}")
            print("1) Paste a dashboard API key")
            print("2) Obtain a key via Agent Access (challenge, token TTL ~120s)")
            choice = input("Choice [1/2]: ").strip() or "1"
            if choice == "2":
                payload = fetch_challenge()
                challenge = (
                    payload.get("challenge")
                    if isinstance(payload.get("challenge"), dict)
                    else {}
                )
                token = payload.get("token")
                print(f"token: {token}")
                print(f"prompt: {challenge.get('prompt')}")
                extras = payload.get("fetched") or []
                if extras:
                    _print_json({"fetched": extras})
                answer = input("Answer (integer): ").strip()
                persist_api_key(submit_answer(str(token or ""), answer))
            else:
                persist_pasted_key(input("ANCHOR_API_KEY: ").strip())
        except EOFError as exc:
            raise RuntimeError("Setup cancelled — no API key entered.") from exc
        key = current_api_key()

    if not key:
        raise RuntimeError(
            "Setup cannot finish without ANCHOR_API_KEY. "
            "Paste it in Browser Automation → Anchor Browser, or run "
            f"in a terminal: hermes anchorbrowser setup\nDocs: {_DOCS}"
        )
    verify_api_key(key)
    print("ANCHOR_API_KEY is set and accepted by Anchor.")


def persist_api_key(result: Dict[str, Any]) -> str:
    """Write ``api_key`` (and optional identity token) to the profile ``.env``."""
    api_key = result.get("api_key")
    if not api_key:
        raise RuntimeError(
            f"Agent Access POST succeeded but no api_key in response: {result!r}"
        )

    from hermes_cli.config import save_env_value

    for name in _KEY_NAMES:
        save_env_value(name, str(api_key))
        os.environ[name] = str(api_key)

    auth = result.get("auth") if isinstance(result.get("auth"), dict) else {}
    identity = result.get("agent_identity_token") or auth.get("agent_identity_token")
    if identity:
        save_env_value("ANCHOR_IDENTITY_TOKEN", str(identity))
        os.environ["ANCHOR_IDENTITY_TOKEN"] = str(identity)
    return str(api_key)


# ---------------------------------------------------------------------------
# CLI — hermes anchorbrowser {guide,challenge,submit}
# ---------------------------------------------------------------------------


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="anchor_command")

    subs.add_parser("guide", help="GET /v1/agent-access (does not issue a key)")
    subs.add_parser(
        "challenge",
        help="GET puzzle + follow GET next hops (appendix). Token TTL ~120s.",
    )

    subs.add_parser(
        "setup",
        help="Require ANCHOR_API_KEY (paste or Agent Access). Fails if none is stored.",
    )

    submit_p = subs.add_parser(
        "submit",
        help="POST {token, answer} and save ANCHOR_API_KEY to the profile .env",
    )
    submit_p.add_argument("token", help="Challenge token (not the answer)")
    submit_p.add_argument("answer", help="Final integer from the puzzle")
    submit_p.add_argument(
        "--identity-token",
        default=os.environ.get("ANCHOR_IDENTITY_TOKEN") or None,
        help="Optional OIDC JWT for extra credits (or set ANCHOR_IDENTITY_TOKEN)",
    )
    submit_p.add_argument(
        "--identity-provider",
        default=None,
        help="Optional provider hint: google, github, vercel",
    )

    subparser.set_defaults(func=anchor_command)


def _print_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def anchor_command(args: argparse.Namespace) -> int:
    sub = getattr(args, "anchor_command", None)
    if not sub:
        print(
            "usage: hermes anchorbrowser {setup,guide,challenge,submit}\n"
            f"Agent Access docs: {_DOCS}\n"
            "  hermes anchorbrowser setup              # required: paste or challenge\n"
            "  hermes anchorbrowser challenge\n"
            "  hermes anchorbrowser submit TOKEN ANSWER",
            file=sys.stderr,
        )
        return 2
    try:
        if sub == "setup":
            run_setup()
            return 0
        if sub == "guide":
            _print_json(fetch_guide())
            return 0
        if sub == "challenge":
            payload = fetch_challenge()
            challenge = payload.get("challenge") if isinstance(payload.get("challenge"), dict) else {}
            _print_json({
                "token": payload.get("token"),
                "prompt": challenge.get("prompt"),
                "challenge": challenge,
                "fetched": payload.get("fetched") or [],
                "instructions": payload.get("instructions"),
                "submit": "hermes anchorbrowser submit <token> <answer>",
                "docs": _DOCS,
            })
            return 0
        if sub == "submit":
            result = submit_answer(
                args.token,
                args.answer,
                identity_token=getattr(args, "identity_token", None),
                identity_provider=getattr(args, "identity_provider", None),
            )
            persist_api_key(result)
            _print_json({
                "ok": True,
                "stored_as": "ANCHOR_API_KEY",
                "credits_granted": result.get("credits_granted"),
                "project_id": result.get("project_id"),
                "limits": result.get("limits"),
                "docs": _DOCS,
            })
            return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"unknown subcommand: {sub}", file=sys.stderr)
    return 2


# ponytail: fake-session check for follow_get_nexts hop/stop rules
if __name__ == "__main__":
    class _Fake:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def __call__(self, method: str, path: str, **_kw: Any) -> Dict[str, Any]:
            self.calls.append(f"{method}:{path}")
            if path.endswith("/appendix/x"):
                return {"inventory": [1], "next": {"method": "POST", "path": "/v1/agent-access"}}
            raise AssertionError(path)

    _orig = api_request
    try:
        fake = _Fake()
        globals()["api_request"] = fake  # type: ignore[assignment]
        payload = {
            "token": "t",
            "challenge": {"prompt": "p"},
            "next": {"method": "GET", "path": "/v1/agent-access/appendix/x"},
        }
        kept, extras = follow_get_nexts(payload)
        assert kept["token"] == "t"
        assert extras[0]["data"]["inventory"] == [1]
        assert fake.calls == ["GET:/v1/agent-access/appendix/x"]
        print("ok")
    finally:
        globals()["api_request"] = _orig  # type: ignore[assignment]
