# Anchor Browser tools for Hermes

Adds [Anchor Browser](https://anchorbrowser.io)'s hosted MCP servers to Hermes, plus a skill that tells
the agent which tool to use.

| Server | Tools | What it is for |
| --- | --- | --- |
| `anchor` | 29 | Run a web task from a prompt, start and end browser sessions, managed logins (identities), saved tasks, the action index, docs search, and any other Anchor REST endpoint |
| `anchor-actions` | 2 | The action index: `find_actions` and `run_action` for verified, deterministic recipes on known sites, with no AI steps |
| `anchor-browser` | 25 | Step-by-step control of a running session: navigate, snapshot, click, type, screenshot, network and console logs |

Tool lists are served by Anchor, so new tools appear without a plugin update.

To make Hermes' own browser tools run on Anchor instead, install the `anchorbrowser` plugin at the
[repository root](../README.md#-hermes-agent). The two work independently.

## Install

```bash
hermes plugins install "anchorbrowser/anchorbrowser-plugin#hermes-mcp" --enable
```

Get an API key at <https://app.anchorbrowser.io/api-keys> and save it as `ANCHORBROWSER_API_KEY`
(`hermes plugins config anchorbrowser-mcp`, or `$HERMES_HOME/.env`). `hermes anchorbrowser setup` from the
`anchorbrowser` plugin saves the key under this name too.

This package lives in a subfolder because Hermes reads MCP servers only from a portable `plugin.json`
package, and the repository root is already the native `anchorbrowser` plugin.

## Approvals

All three servers are declared `trust: untrusted`. Tools Anchor marks read-only run freely. Every tool that
starts a browser, runs a task, changes a login or calls a write endpoint asks you first (once, for the
session, or always), and fails closed in unattended runs. To lift that for a server you trust, add a
same-name entry under `mcp_servers` in `config.yaml`.

## What this plugin does on your machine and network

- **Network.** Hermes connects to `https://api.anchorbrowser.io/v1/mcp`, `/v1/mcp/actions` and
  `/v1/mcp/browser`. Browsing happens in Anchor's cloud browsers.
- **Credentials.** `ANCHORBROWSER_API_KEY` is sent as the `anchor-api-key` header to those three URLs only.
  Hermes drops the header on any cross-origin redirect. The key is not stored in this package.
- **Cost.** Browser sessions, AI task steps and proxy traffic are billed to your Anchor account. See
  <https://docs.anchorbrowser.io/pricing>.
- **Your Anchor account.** Tools can create sessions, identities and profiles, run saved tasks, and call
  write endpoints in your account. Those calls are the ones that ask for approval.
- **Nothing local.** No code runs on your machine: no Python, no shell commands, no background processes,
  no files written, no telemetry.

## License

MIT
