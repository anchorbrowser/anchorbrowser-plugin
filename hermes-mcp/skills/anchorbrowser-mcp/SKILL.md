---
name: anchorbrowser-mcp
description: Pick the right Anchor Browser tool for a web job. Use when a task needs a real browser, a site blocks plain HTTP or automated browsers, a login is needed, or the same web job will run again.
---

# Using Anchor Browser

Anchor runs real browsers in the cloud. Each session is an isolated browser that is destroyed when it
ends. Three tool groups come with this plugin: `anchor` (tasks, sessions, logins, the full API),
`anchor-actions` (deterministic recipes for known sites) and `anchor-browser` (step-by-step control of a
live browser).

## Pick the first that fits

1. **A saved automation already exists.** `list_tasks` to find it, `run_task` to run it, then poll
   `get_execution`.
2. **A known site may have a ready recipe.** `find_actions` with the site, then `run_action`. Recipes run
   fixed code with no AI steps, so they are fast and cost less. An empty result is final: move on.
3. **Any other web goal.** `perform_web_task` with a plain-language prompt, then poll `get_web_task_status`
   until it reports COMPLETED or FAILED. It reuses a matching recipe on its own.
4. **You need to drive the page yourself.** `create_session`, then use the `anchor-browser` tools on that
   session, or hand its `cdp_url` to any CDP client. Always `end_session` when done.
5. **Something the tools above do not cover.** `list_endpoints` with a search term, `get_endpoint`, then
   `call_endpoint_read` or `call_endpoint_write`.

## When a site blocks you

Turn these on in `create_session`. Stealth and captcha solving both need the proxy.

- `session.proxy`: residential proxy, with a country when the site expects local visitors.
- `browser.captcha_solver`: solves captchas as they appear.
- `browser.extra_stealth`: a patched browser build for sites that detect automation.

Open the site the way a person would: land on a search result or the home page first, then navigate, instead
of jumping straight to a deep URL.

## When a site needs a login

Never ask the user to paste a password into the chat.

1. `list_applications`, then `list_application_identities`, to reuse a login that already exists.
2. Otherwise `create_identity` for the site, then `create_reauth_link` and give the user the link. They sign
   in on Anchor's page; the password never passes through this conversation.
3. Pass the identity to `create_session` as `identities: [{ id }]`.
4. If the site signs the identity out later, `reauthenticate_identity`.

## Rules

- Long work is asynchronous. `perform_web_task`, `run_task` and `reauthenticate_identity` return quickly;
  poll their status tool for the result.
- Check the `status` field of a result. A reply can arrive with a failed status.
- End every session you create. A session left open bills until its idle timeout.
- Never submit a payment or confirm a purchase unless the user asked for exactly that.
