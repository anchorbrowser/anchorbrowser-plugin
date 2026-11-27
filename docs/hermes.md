# Anchor Browser for Hermes Agent

Run Hermes' built-in browser tools on [Anchor Browser](https://anchorbrowser.io) cloud browsers.

Hermes keeps doing the browsing. This plugin only supplies the browser: it starts one Anchor session per
task, hands Hermes the CDP URL, and closes the session when the task ends. Every Hermes browser tool
(`browser_exec`, `browser_cdp`, `browser_dialog`, `browser_vault`) works unchanged.

What you get from the Anchor side:

- **No local Chrome.** The browser runs in an isolated cloud VM that is destroyed after the session.
- **Residential proxy by country, region or city.** Browse as a visitor from where the site expects one.
- **Captcha solving and extra stealth** for sites that block ordinary automated browsers.
- **Saved profiles.** Keep cookies and logins between tasks.
- **Managed logins.** Start a session already signed in through Anchor identities.
- **Recordings and a live view** of what the agent did.

For Anchor's own tools (web tasks, the action index, managed logins, live-browser control), install the
companion MCP package in [`../hermes-mcp`](../hermes-mcp). It adds Anchor's three hosted MCP servers.

## Install

```bash
hermes plugins install anchorbrowser/anchorbrowser-plugin --enable
```

Get an API key at <https://app.anchorbrowser.io/api-keys>, then run `hermes anchorbrowser setup` to paste it.
[Agent Access](https://docs.anchorbrowser.io/quickstart/agent-access), which issues a key with no dashboard
account, is suspended for now. Then select the backend, either in `hermes tools` (Browser Automation, Anchor Browser) or in
`config.yaml`:

```yaml
browser:
  cloud_provider: anchorbrowser
```

## Settings

All settings are optional except the key. Set them the same way as the key (`hermes plugins config
anchorbrowser`, or `$HERMES_HOME/.env`).

Every setting is read as `ANCHOR_<NAME>` first and `ANCHORBROWSER_<NAME>` second, so
`ANCHORBROWSER_API_KEY` from the SDK works unchanged. Four earlier names still work: `ANCHOR_STEALTH`,
`ANCHOR_CAPTCHA`, `ANCHOR_SESSION_TIMEOUT_MINUTES` and `ANCHOR_IDENTITY_ID`.

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_API_KEY` | required | Your Anchor Browser API key. |
| `ANCHOR_IDENTITY_TOKEN` | none | Agent Access identity token, sent as the `anchor-identity-token` header. `hermes anchorbrowser setup` saves it when Anchor issues one. |

**Proxy**

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_PROXY` | `false` | Route the browser through Anchor's residential proxy. |
| `ANCHOR_PROXY_COUNTRY` | none | Two-letter country code, for example `us`, `gb`, `de`. Turns the proxy on. |
| `ANCHOR_PROXY_REGION` | none | Region inside the country. Turns the proxy on. |
| `ANCHOR_PROXY_CITY` | none | City. Turns the proxy on. |
| `ANCHOR_PROXY_SERVER` | none | Your own proxy as `PROTOCOL://HOST:PORT`. Used instead of Anchor's proxy. |
| `ANCHOR_PROXY_USERNAME`, `ANCHOR_PROXY_PASSWORD` | none | Credentials for your own proxy. |

**Getting past blocks**

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_CAPTCHA_SOLVER` | `false` | Solve captchas automatically. Turns Anchor's proxy on unless you set your own proxy. |
| `ANCHOR_EXTRA_STEALTH` | `false` | Use Anchor's patched Chromium build. Turns Anchor's proxy on. Needs a plan that includes it; it stays off with your own proxy. |
| `ANCHOR_ADBLOCK` | Anchor default (on) | Set `false` to turn ad blocking off (popup blocking goes off with it). |
| `ANCHOR_POPUP_BLOCKER` | Anchor default (on) | Set `false` to keep popups and consent banners. |

**Logins and saved state**

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_PROFILE` | none | Name of a saved Anchor profile to load. |
| `ANCHOR_PROFILE_PERSIST` | `false` | Save cookies and storage back to that profile when the session ends. |
| `ANCHOR_IDENTITIES` | none | Comma-separated identity ids. The session starts signed in to those sites. |
| `ANCHOR_IDENTITY_VALIDATE` | Anchor default (off) | Set `true` to check each identity is still signed in and sign in again if not. |
| `ANCHOR_EXTENSIONS` | none | Comma-separated ids of browser extensions uploaded to your Anchor account. |
| `ANCHOR_VOLUME_ID` | none | Persistent volume to mount; downloads are kept there after the session. |
| `ANCHOR_VOLUME_READ_ONLY` | `false` | Mount that volume read-only. |

**Browser**

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_HEADLESS` | `false` | Run the browser headless. Turns scoped access tokens off. |
| `ANCHOR_VIEWPORT` | `1440x900` | Viewport as `WIDTHxHEIGHT`. |
| `ANCHOR_FULLSCREEN` | `false` | Start the browser in fullscreen. |
| `ANCHOR_PDF_VIEWER` | Anchor default (on) | Set `false` to download PDFs instead of viewing them. |
| `ANCHOR_P2P_DOWNLOAD` | `false` | Capture downloads for direct extraction instead of storing them at Anchor. |
| `ANCHOR_DISABLE_WEB_SECURITY` | `false` | Turn off CORS and same-origin checks, for cross-origin iframes. |
| `ANCHOR_INITIAL_URL` | none | Page the browser opens on start. |
| `ANCHOR_DOMAIN_ALLOWLIST` | none | Comma-separated domains the session may visit. Everything else is blocked. |

**Session**

| Setting | Default | What it does |
| --- | --- | --- |
| `ANCHOR_MAX_DURATION` | `20` | Longest session, in minutes. Hermes replaces the browser just before it ends. Agent Access keys are capped at 60. |
| `ANCHOR_IDLE_TIMEOUT` | `5` | Minutes a session stays open with nothing connected. |
| `ANCHOR_RECORDING` | `false` | Set `true` to record sessions. |
| `ANCHOR_TAGS` | none | Comma-separated tags added to each session, next to `hermes` and the Hermes task id. |
| `ANCHOR_SCOPED_ACCESS` | `true` | Ask Anchor for a CDP URL that carries a session token instead of the session id. |
| `ANCHOR_LIVE_VIEW_READ_ONLY` | `false` | Make the live view watch-only. |
| `ANCHOR_SHOW_LIVE_VIEW` | `false` | Write the read-only live view URL to the Hermes log when a session starts. |
| `ANCHOR_BASE_URL` | `https://api.anchorbrowser.io` | API host. Must be `https`. |

**Anything else**

`ANCHOR_SESSION_JSON` takes a JSON object in the shape of Anchor's
[start-session request](https://docs.anchorbrowser.io/api-reference/browser-sessions/start-browser-session)
and merges it over everything above. Use it for options that have no setting of their own, for example
integrations or a single-use live view URL:

```bash
ANCHOR_SESSION_JSON='{"session":{"live_view":{"one_time_url":true}},"integrations":[{"id":"...","type":"1PASSWORD"}]}'
```

If a plan does not include extra stealth or captcha solving (Anchor answers 402 or 403), the plugin logs a
warning and starts the session without that feature. It never drops the proxy on its own.

## What this plugin does on your machine and network

- **Network.** Sends HTTPS requests to `api.anchorbrowser.io` (or `ANCHOR_BASE_URL`) to start and end
  sessions. Hermes then opens a WebSocket to `connect.anchorbrowser.io` to drive the browser. The pages the
  agent visits are loaded by the Anchor browser, not by your machine.
- **Credentials.** Reads `ANCHOR_API_KEY` (or `ANCHORBROWSER_API_KEY`) through Hermes' secret scope only. `hermes anchorbrowser setup` writes the key to your Hermes profile `.env` under both names. The key is sent only to
  the Anchor API host and is never written to a log or a file. Redirects are refused, so the key cannot
  follow one to another host.
- **Cost.** Sessions are billed to your Anchor account: per browser, per browser hour, and per GB when the
  proxy is on. See <https://docs.anchorbrowser.io/pricing>.
- **Your Anchor account.** Each session is tagged `hermes` and with the Hermes task id. Identities, profiles, extensions and volumes are
  used only when you name them in a setting. Sessions are not recorded unless you set
  `ANCHOR_RECORDING=true`. With `ANCHOR_PROFILE_PERSIST=true`, cookies and
  storage are saved to the named profile in your account.
- **Usage tag.** Requests to the Anchor API carry a `hermes-anchorbrowser/<version>` User-Agent so Anchor
  can count plugin usage. The browser's own user agent is not changed. No other telemetry.
- **Logs.** With `ANCHOR_SHOW_LIVE_VIEW=true`, the read-only live view URL is written to the Hermes
  log. Anyone who has that URL can watch the session while it runs.
- **Nothing else.** No background threads, no local servers, no shell commands, no changes to Hermes
  internals, no Python dependencies beyond Hermes itself.

## If something goes wrong

- **Hermes used a local browser instead.** Hermes falls back to a local browser when a cloud session cannot
  start. The reason is in the Hermes log: a rejected key (401), a rate or concurrency limit (429), or the
  Anchor error text.
- **Captcha solving or extra stealth stayed off.** Your plan may not include them (the log has a warning),
  or extra stealth was asked for together with your own proxy.
- **Sessions left running.** Hermes closes the session when the task ends. If Hermes is killed, Anchor ends
  the session after the idle timeout.

## Tests

Run both with the Hermes interpreter, from a Hermes checkout:

```bash
# unit tests, no network
python /path/to/anchorbrowser-plugin/tests/hermes/test_provider.py

# real Anchor sessions: proxy country, captcha solver, extra stealth, headless, timeouts, bad key
ANCHOR_API_KEY=... python /path/to/anchorbrowser-plugin/tests/hermes/live_check.py
```

`hermes plugins validate .` and `hermes plugins doctor . --ci` both pass, for the repository root and for
`hermes-mcp/`.
