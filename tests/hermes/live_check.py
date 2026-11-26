"""Live check against the real Anchor Browser API. Needs ANCHOR_API_KEY (or ANCHORBROWSER_API_KEY) and
the Hermes interpreter. Opens real sessions and always closes them."""
import asyncio
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "anchorbrowser_plugin", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
)
package = importlib.util.module_from_spec(spec)
sys.modules["anchorbrowser_plugin"] = package
spec.loader.exec_module(package)
provider_module = sys.modules["anchorbrowser_plugin.provider"]

KEY_NAMES = ("ANCHOR_API_KEY", "ANCHOR_API_KEY")
SETTINGS = [name for name in os.environ if name.startswith(("ANCHOR_", "ANCHOR_")) and name not in KEY_NAMES]
results = []


def record(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL"), name, "|", detail)


async def cdp(url, expression, goto=None):
    async with websockets.connect(url, max_size=None, open_timeout=30) as ws:
        counter = 0

        async def call(method, params=None, session=None):
            nonlocal counter
            counter += 1
            message = {"id": counter, "method": method, "params": params or {}}
            if session:
                message["sessionId"] = session
            await ws.send(json.dumps(message))
            while True:
                reply = json.loads(await asyncio.wait_for(ws.recv(), 60))
                if reply.get("id") == counter:
                    return reply

        targets = (await call("Target.getTargets"))["result"]["targetInfos"]
        page = next(t for t in targets if t["type"] == "page")
        session = (await call("Target.attachToTarget", {"targetId": page["targetId"], "flatten": True}))["result"]["sessionId"]
        if goto:
            await call("Page.enable", session=session)
            await call("Page.navigate", {"url": goto}, session=session)
            await asyncio.sleep(4)
        reply = await call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True}, session=session)
        return reply.get("result", {}).get("result", {}).get("value")


def run_case(name, settings, check):
    for key in SETTINGS + list(settings):
        os.environ.pop(key, None)
    os.environ.update(settings)
    provider = provider_module.AnchorBrowserProvider()
    session_id = None
    started = time.time()
    try:
        session = provider.create_session("livecheck")
        session_id = session["bb_session_id"]
        contract = all(key in session for key in ("session_name", "bb_session_id", "cdp_url", "features"))
        detail = check(session)
        record(name, contract and detail is not False, f"{time.time() - started:.1f}s features={[k for k, v in session['features'].items() if v]} {detail if isinstance(detail, str) else ''}")
    except Exception as error:
        record(name, False, f"{type(error).__name__}: {provider_module.redact(str(error))[:200]}")
    finally:
        if session_id:
            record(f"{name}: close_session", provider.close_session(session_id))
            record(f"{name}: second close is still clean", provider.close_session(session_id))
        for key in settings:
            os.environ.pop(key, None)


def title_check(session):
    title = asyncio.run(cdp(session["cdp_url"], "document.title", goto="https://example.com"))
    return f"title={title!r}" if title == "Example Domain" else False


def country_check(expected):
    def check(session):
        raw = asyncio.run(cdp(session["cdp_url"], "fetch('https://ipinfo.io/json').then(r => r.text())", goto="https://example.com"))
        country = (json.loads(raw).get("country") or "").lower() if raw else ""
        return f"exit country={country}" if country == expected else False
    return check


def expiry_check(session):
    left = (datetime.fromisoformat(session["expires_at"]) - datetime.now(timezone.utc)).total_seconds()
    return f"expires in {left:.0f}s" if 100 < left < 125 else False


def options_check(session):
    value = asyncio.run(cdp(session["cdp_url"], "JSON.stringify([location.hostname, window.innerWidth])"))
    host, width = json.loads(value)
    return f"opened {host}, width {width}" if host == "example.com" and 1200 <= width <= 1280 else False


def blocked_check(session):
    title = asyncio.run(cdp(session["cdp_url"], "document.title", goto="https://www.iana.org/"))
    return f"off-list page title={title!r}" if "IANA" not in (title or "") else False


run_case("default session, navigate over CDP", {}, title_check)
run_case("viewport, initial URL, tags", {"ANCHOR_VIEWPORT": "1280x800", "ANCHOR_INITIAL_URL": "https://example.com", "ANCHOR_TAGS": "livecheck"}, options_check)
run_case("domain allowlist blocks other sites", {"ANCHOR_DOMAIN_ALLOWLIST": "example.com"}, blocked_check)
run_case("raw JSON: fullscreen and popup blocker off", {"ANCHOR_SESSION_JSON": json.dumps({"browser": {"fullscreen": {"active": True}}, "session": {"tags": ["hermes", "raw"]}})}, title_check)
run_case("pdf viewer off, p2p download, web security off", {"ANCHOR_PDF_VIEWER": "false", "ANCHOR_P2P_DOWNLOAD": "true", "ANCHOR_DISABLE_WEB_SECURITY": "true"}, title_check)
run_case("proxy country de", {"ANCHOR_PROXY_COUNTRY": "de"}, country_check("de"))
run_case("proxy + captcha solver + extra stealth", {"ANCHOR_PROXY": "true", "ANCHOR_CAPTCHA_SOLVER": "true", "ANCHOR_EXTRA_STEALTH": "true"}, title_check)
run_case("headless, plain session URL", {"ANCHOR_HEADLESS": "true"}, title_check)
run_case("max duration sets expires_at", {"ANCHOR_MAX_DURATION": "2", "ANCHOR_IDLE_TIMEOUT": "1"}, expiry_check)
run_case("recording off, adblock off", {"ANCHOR_RECORDING": "false", "ANCHOR_ADBLOCK": "false"}, title_check)

run_case("earlier setting names still work", {"ANCHOR_STEALTH": "true", "ANCHOR_SESSION_TIMEOUT_MINUTES": "3"}, title_check)

saved = {name: os.environ.pop(name, None) for name in KEY_NAMES}
os.environ["ANCHOR_API_KEY"] = "sk-" + "0" * 32
bad = provider_module.AnchorBrowserProvider()
try:
    bad.create_session("livecheck")
    record("invalid key is refused", False)
except RuntimeError as error:
    record("invalid key is refused", "ANCHOR_API_KEY" in str(error) and "sk-0000" not in str(error), str(error)[:110])
record("close with invalid key returns False", bad.close_session("00000000-0000-0000-0000-000000000000") is False)
record("emergency cleanup with invalid key is silent", bad.emergency_cleanup("00000000-0000-0000-0000-000000000000") is None)
os.environ.pop("ANCHOR_API_KEY", None)
os.environ.update({name: value for name, value in saved.items() if value})

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
