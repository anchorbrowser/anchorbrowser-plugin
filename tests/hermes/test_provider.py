import importlib.util
import io
import json
import sys
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "anchorbrowser_plugin", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
)
package = importlib.util.module_from_spec(spec)
sys.modules["anchorbrowser_plugin"] = package
spec.loader.exec_module(package)
provider = sys.modules["anchorbrowser_plugin.provider"]

KEY = "sk-" + "a" * 32
SESSION = {"data": {"id": "sess-1", "cdp_url": "wss://connect.anchorbrowser.io?token=tok-1&rt=r1",
                    "live_view_read_only_url": "https://live.anchorbrowser.io/inspector.html?token=tok-2&viewOnly=1"}}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(status, body="{}"):
    return urllib.error.HTTPError("https://api.anchorbrowser.io/v1/sessions", status, "error", {}, io.BytesIO(body.encode()))


class Harness(unittest.TestCase):
    def setUp(self):
        self.settings = {"ANCHOR_API_KEY": KEY}
        self.calls = []
        self.replies = []
        patches = [
            mock.patch.object(provider, "get_secret", side_effect=lambda name, default=None: self.settings.get(name, default)),
            mock.patch.object(provider, "_open", side_effect=self._fake_open),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.provider = provider.AnchorBrowserProvider()

    def _fake_open(self, request, timeout):
        body = json.loads(request.data) if request.data else None
        self.calls.append({"method": request.get_method(), "url": request.full_url, "body": body,
                           "headers": {k.lower(): v for k, v in request.header_items()}, "timeout": timeout})
        reply = self.replies.pop(0) if self.replies else SESSION
        if isinstance(reply, Exception):
            raise reply
        return FakeResponse(json.dumps(reply).encode())


class IdentityTests(Harness):
    def test_name_is_the_config_value(self):
        self.assertEqual(self.provider.name, "anchorbrowser")
        self.assertEqual(self.provider.display_name, "Anchor Browser")

    def test_is_available_reads_the_key_without_network(self):
        self.assertTrue(self.provider.is_available())
        self.settings.clear()
        self.assertFalse(self.provider.is_available())
        self.assertEqual(self.calls, [])

    def test_setup_schema_exposes_the_key(self):
        schema = self.provider.get_setup_schema()
        self.assertEqual(schema["env_vars"][0]["key"], "ANCHOR_API_KEY")
        self.assertEqual(schema["name"], "Anchor Browser")


class PayloadTests(Harness):
    def test_defaults_keep_recording_off_and_use_scoped_tokens(self):
        payload, features = provider.build_session_payload()
        self.assertEqual(payload, {"session": {"tags": ["hermes"], "recording": {"active": False}, "timeout": {"max_duration": 20, "idle_timeout": 5}, "scoped_access": {"active": True}}})
        self.assertFalse(features["proxy"])
        self.assertTrue(features["scoped_access"])

    def test_country_turns_the_proxy_on(self):
        self.settings.update({"ANCHOR_PROXY_COUNTRY": "DE", "ANCHOR_PROXY_CITY": "Berlin"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"],
                         {"active": True, "type": "anchor_proxy", "country_code": "de", "city": "Berlin"})
        self.assertTrue(features["proxy"])

    def test_captcha_and_stealth_turn_the_proxy_on(self):
        self.settings.update({"ANCHOR_CAPTCHA_SOLVER": "true", "ANCHOR_EXTRA_STEALTH": "true"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"], {"active": True, "type": "anchor_proxy"})
        self.assertEqual(payload["browser"], {"captcha_solver": {"active": True}, "extra_stealth": {"active": True}})
        self.assertTrue(features["proxy"] and features["captcha_solver"] and features["extra_stealth"])

    def test_both_prefixes_and_the_earlier_names_are_read(self):
        self.settings.update({"ANCHORBROWSER_PROXY_COUNTRY": "gb", "ANCHOR_STEALTH": "true", "ANCHOR_CAPTCHA": "1",
                              "ANCHOR_SESSION_TIMEOUT_MINUTES": "45", "ANCHOR_IDENTITY_ID": "id-9"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"]["country_code"], "gb")
        self.assertEqual(payload["browser"], {"captcha_solver": {"active": True}, "extra_stealth": {"active": True}})
        self.assertEqual(payload["session"]["timeout"], {"max_duration": 45, "idle_timeout": 5})
        self.assertEqual(payload["identities"], [{"id": "id-9"}])

    def test_the_anchor_prefix_wins_over_the_alias(self):
        self.settings.update({"ANCHOR_PROXY_COUNTRY": "de", "ANCHORBROWSER_PROXY_COUNTRY": "us"})
        payload, _ = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"]["country_code"], "de")

    def test_task_id_becomes_a_tag(self):
        payload, _ = provider.build_session_payload("task-" + "x" * 60)
        self.assertEqual(payload["session"]["tags"], ["hermes", ("task-" + "x" * 60)[:48]])

    def test_short_sessions_get_a_short_idle_timeout(self):
        self.settings["ANCHOR_MAX_DURATION"] = "2"
        payload, _ = provider.build_session_payload()
        self.assertEqual(payload["session"]["timeout"], {"max_duration": 2, "idle_timeout": 2})

    def test_profile_timeouts_recording_and_adblock(self):
        self.settings.update({"ANCHOR_PROFILE": "work", "ANCHOR_PROFILE_PERSIST": "yes",
                              "ANCHOR_MAX_DURATION": "30", "ANCHOR_IDLE_TIMEOUT": "3",
                              "ANCHOR_RECORDING": "false", "ANCHOR_ADBLOCK": "off"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["browser"]["profile"], {"name": "work", "persist": True})
        self.assertEqual(payload["browser"]["adblock"], {"active": False})
        self.assertEqual(payload["browser"]["popup_blocker"], {"active": False})
        self.assertEqual(payload["session"]["timeout"], {"max_duration": 30, "idle_timeout": 3})
        self.assertEqual(payload["session"]["recording"], {"active": False})
        self.assertTrue(features["profile_persist"])

    def test_every_other_session_setting_reaches_the_payload(self):
        self.settings.update({
            "ANCHOR_TAGS": "prod, hermes, team-a", "ANCHOR_INITIAL_URL": "https://example.com",
            "ANCHOR_DOMAIN_ALLOWLIST": "example.com,example.org", "ANCHOR_LIVE_VIEW_READ_ONLY": "true",
            "ANCHOR_VIEWPORT": "1280x800", "ANCHOR_FULLSCREEN": "true", "ANCHOR_PDF_VIEWER": "false",
            "ANCHOR_P2P_DOWNLOAD": "true", "ANCHOR_DISABLE_WEB_SECURITY": "true",
            "ANCHOR_POPUP_BLOCKER": "false", "ANCHOR_EXTENSIONS": "ext-1, ext-2",
            "ANCHOR_VOLUME_ID": "vol-1", "ANCHOR_VOLUME_READ_ONLY": "true",
            "ANCHOR_IDENTITIES": "id-1,id-2", "ANCHOR_IDENTITY_VALIDATE": "true"})
        payload, features = provider.build_session_payload()
        session, browser = payload["session"], payload["browser"]
        self.assertEqual(session["tags"], ["hermes", "prod", "team-a"])
        self.assertEqual(session["initial_url"], "https://example.com")
        self.assertEqual(session["domain_allowlist"], ["example.com", "example.org"])
        self.assertEqual(session["live_view"], {"read_only": True})
        self.assertEqual(browser["viewport"], {"width": 1280, "height": 800})
        self.assertEqual(browser["fullscreen"], {"active": True})
        self.assertEqual(browser["pdf_viewer"], {"active": False})
        self.assertEqual(browser["p2p_download"], {"active": True})
        self.assertEqual(browser["disable_web_security"], {"active": True})
        self.assertEqual(browser["popup_blocker"], {"active": False})
        self.assertEqual(browser["extensions"], ["ext-1", "ext-2"])
        self.assertEqual(browser["volume"], {"id": "vol-1", "read_only": True})
        self.assertEqual(payload["identities"], [{"id": "id-1"}, {"id": "id-2"}])
        self.assertIs(payload["identity_skip_validation"], False)
        self.assertTrue(features["identities"])

    def test_bring_your_own_proxy(self):
        self.settings.update({"ANCHOR_PROXY_SERVER": "https://proxy.example.com:443",
                              "ANCHOR_PROXY_USERNAME": "u", "ANCHOR_PROXY_PASSWORD": "p",
                              "ANCHOR_CAPTCHA_SOLVER": "true", "ANCHOR_EXTRA_STEALTH": "true"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"], {"active": True, "type": "custom",
                         "server": "https://proxy.example.com:443", "username": "u", "password": "p"})
        self.assertTrue(features["proxy"] and features["captcha_solver"])
        self.assertFalse(features["extra_stealth"])

    def test_raw_json_is_merged_last_and_covers_anything_else(self):
        self.settings.update({"ANCHOR_PROXY_COUNTRY": "us", "ANCHOR_SESSION_JSON": json.dumps({
            "session": {"proxy": {"country_code": "fr"}, "live_view": {"one_time_url": True}},
            "browser": {"captcha_solver": {"active": True}},
            "integrations": [{"id": "int-1", "type": "1PASSWORD"}]})})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["proxy"], {"active": True, "type": "anchor_proxy", "country_code": "fr"})
        self.assertEqual(payload["session"]["live_view"], {"one_time_url": True})
        self.assertEqual(payload["integrations"], [{"id": "int-1", "type": "1PASSWORD"}])
        self.assertEqual(payload["session"]["tags"], ["hermes"])
        self.assertTrue(features["captcha_solver"] and features["custom_config"])

    def test_bad_raw_json_and_viewport_are_ignored(self):
        self.settings.update({"ANCHOR_SESSION_JSON": "[1,2", "ANCHOR_VIEWPORT": "big"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload, {"session": {"tags": ["hermes"], "recording": {"active": False}, "timeout": {"max_duration": 20, "idle_timeout": 5}, "scoped_access": {"active": True}}})
        self.assertFalse(features["custom_config"])

    def test_headless_turns_scoped_tokens_off(self):
        self.settings["ANCHOR_HEADLESS"] = "true"
        payload, features = provider.build_session_payload()
        self.assertNotIn("scoped_access", payload["session"])
        self.assertEqual(payload["browser"]["headless"], {"active": True})
        self.assertFalse(features["scoped_access"])

    def test_bad_values_fall_back_to_defaults(self):
        self.settings.update({"ANCHOR_MAX_DURATION": "soon", "ANCHOR_PROXY": "maybe"})
        payload, features = provider.build_session_payload()
        self.assertEqual(payload["session"]["timeout"], {"max_duration": 20, "idle_timeout": 5})
        self.assertFalse(features["proxy"])


class CreateTests(Harness):
    def test_returns_the_session_contract(self):
        self.settings["ANCHOR_MAX_DURATION"] = "10"
        result = self.provider.create_session("task42")
        self.assertEqual(result["bb_session_id"], "sess-1")
        self.assertEqual(result["cdp_url"], SESSION["data"]["cdp_url"])
        self.assertTrue(result["session_name"].startswith("hermes_task42_"))
        self.assertIsInstance(result["features"], dict)
        left = (datetime.fromisoformat(result["expires_at"]) - datetime.now(timezone.utc)).total_seconds()
        self.assertTrue(580 < left <= 600, left)
        call = self.calls[0]
        self.assertEqual(call["body"]["session"]["tags"], ["hermes", "task42"])
        self.assertNotIn("anchor-identity-token", call["headers"])
        self.assertEqual((call["method"], call["url"]), ("POST", "https://api.anchorbrowser.io/v1/sessions"))
        self.assertEqual(call["headers"]["anchor-api-key"], KEY)
        self.assertTrue(call["headers"]["user-agent"].startswith("hermes-anchorbrowser/"))

    def test_no_expiry_when_the_cap_is_disabled(self):
        self.settings["ANCHOR_MAX_DURATION"] = "-1"
        self.assertNotIn("expires_at", self.provider.create_session("t"))
        self.assertEqual(self.calls[0]["body"]["session"]["timeout"]["max_duration"], -1)

    def test_identity_token_is_sent_when_set(self):
        self.settings["ANCHOR_IDENTITY_TOKEN"] = "idt-1"
        self.provider.create_session("t")
        self.assertEqual(self.calls[0]["headers"]["anchor-identity-token"], "idt-1")

    def test_either_key_name_works(self):
        self.settings = {"ANCHORBROWSER_API_KEY": KEY}
        self.provider.create_session("t")
        self.assertEqual(self.calls[0]["headers"]["anchor-api-key"], KEY)

    def test_missing_key_is_a_value_error_and_sends_nothing(self):
        self.settings.clear()
        with self.assertRaises(ValueError):
            self.provider.create_session("t")
        self.assertEqual(self.calls, [])

    def test_plain_http_base_url_is_refused(self):
        self.settings["ANCHOR_BASE_URL"] = "http://api.anchorbrowser.io"
        with self.assertRaises(ValueError):
            self.provider.create_session("t")
        self.assertEqual(self.calls, [])

    def test_custom_base_url_is_used(self):
        self.settings["ANCHOR_BASE_URL"] = "https://anchor.internal.example/"
        self.provider.create_session("t")
        self.assertEqual(self.calls[0]["url"], "https://anchor.internal.example/v1/sessions")

    def test_plan_refusal_drops_paid_features_one_at_a_time(self):
        self.settings.update({"ANCHOR_PROXY": "true", "ANCHOR_CAPTCHA_SOLVER": "true",
                              "ANCHOR_EXTRA_STEALTH": "true"})
        self.replies = [http_error(403), http_error(402), SESSION]
        result = self.provider.create_session("t")
        self.assertEqual(len(self.calls), 3)
        self.assertIn("extra_stealth", self.calls[0]["body"]["browser"])
        self.assertNotIn("extra_stealth", self.calls[1]["body"]["browser"])
        self.assertNotIn("captcha_solver", self.calls[2]["body"].get("browser", {}))
        self.assertFalse(result["features"]["extra_stealth"])
        self.assertFalse(result["features"]["captcha_solver"])
        self.assertTrue(result["features"]["proxy"])
        self.assertIn("proxy", self.calls[2]["body"]["session"])

    def test_scoped_token_refusal_retries_once_with_a_plain_url(self):
        self.settings.update({"ANCHOR_PROXY": "true", "ANCHOR_EXTRA_STEALTH": "true"})
        self.replies = [http_error(400, '{"error":"session.scoped_access: not supported"}'), SESSION]
        result = self.provider.create_session("t")
        self.assertNotIn("scoped_access", self.calls[1]["body"]["session"])
        self.assertIn("extra_stealth", self.calls[1]["body"]["browser"])
        self.assertFalse(result["features"]["scoped_access"])
        self.assertTrue(result["features"]["extra_stealth"])

    def test_other_bad_requests_are_not_retried(self):
        self.settings["ANCHOR_PROXY_COUNTRY"] = "zz"
        self.replies = [http_error(400, '{"error":"bad country"}')]
        with self.assertRaises(RuntimeError) as caught:
            self.provider.create_session("t")
        self.assertIn("bad country", str(caught.exception))
        self.assertEqual(len(self.calls), 1)

    def test_refusal_with_nothing_left_to_drop_raises(self):
        self.settings["ANCHOR_SCOPED_ACCESS"] = "false"
        self.replies = [http_error(400, '{"error":"bad"}')]
        with self.assertRaises(RuntimeError):
            self.provider.create_session("t")
        self.assertEqual(len(self.calls), 1)

    def test_bad_key_names_the_setting_and_hides_the_key(self):
        self.replies = [http_error(401, json.dumps({"error": "Invalid API Key " + KEY}))]
        with self.assertRaises(RuntimeError) as caught:
            self.provider.create_session("t")
        self.assertIn("ANCHOR_API_KEY", str(caught.exception))
        self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(len(self.calls), 1)

    def test_rate_limit_is_explained(self):
        self.replies = [http_error(429)]
        with self.assertRaises(RuntimeError) as caught:
            self.provider.create_session("t")
        self.assertIn("429", str(caught.exception))

    def test_network_failure_is_a_runtime_error(self):
        self.replies = [urllib.error.URLError("no route")]
        with self.assertRaises(RuntimeError):
            self.provider.create_session("t")

    def test_reply_without_cdp_url_closes_the_session(self):
        self.replies = [{"data": {"id": "sess-9"}}, {}]
        with self.assertRaises(RuntimeError):
            self.provider.create_session("t")
        self.assertEqual((self.calls[1]["method"], self.calls[1]["url"]),
                         ("DELETE", "https://api.anchorbrowser.io/v1/sessions/sess-9"))

    def test_live_view_is_logged_only_when_asked(self):
        with self.assertLogs(provider.logger, level="INFO") as logs:
            self.provider.create_session("t")
        self.assertFalse(any("live view" in line for line in logs.output))
        self.settings["ANCHOR_SHOW_LIVE_VIEW"] = "true"
        with self.assertLogs(provider.logger, level="INFO") as logs:
            self.provider.create_session("t")
        self.assertTrue(any("viewOnly=1" in line for line in logs.output))


class CloseTests(Harness):
    def test_close_deletes_the_session(self):
        self.replies = [{}]
        self.assertTrue(self.provider.close_session("sess-1"))
        self.assertEqual((self.calls[0]["method"], self.calls[0]["url"]),
                         ("DELETE", "https://api.anchorbrowser.io/v1/sessions/sess-1"))

    def test_already_gone_counts_as_closed(self):
        self.replies = [http_error(404)]
        self.assertTrue(self.provider.close_session("sess-1"))

    def test_close_never_raises(self):
        for failure in (http_error(500), urllib.error.URLError("down"), TimeoutError()):
            self.replies = [failure]
            self.assertFalse(self.provider.close_session("sess-1"))
        self.settings.clear()
        self.assertFalse(self.provider.close_session("sess-1"))

    def test_emergency_cleanup_never_raises(self):
        for failure in (http_error(500), urllib.error.URLError("down")):
            self.replies = [failure]
            self.assertIsNone(self.provider.emergency_cleanup("sess-1"))
        self.settings.clear()
        self.assertIsNone(self.provider.emergency_cleanup("sess-1"))


class RedactTests(unittest.TestCase):
    def test_keys_and_url_tokens_are_removed(self):
        text = provider.redact(f"key {KEY} url wss://connect.anchorbrowser.io?token=abc123&rt=zz&sessionId=s-1")
        self.assertNotIn(KEY, text)
        for secret in ("abc123", "zz", "s-1"):
            self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
