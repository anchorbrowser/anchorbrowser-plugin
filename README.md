# anchorbrowser plugin marketplace

Install the [`anchorbrowser`](https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript) TypeScript SDK as a native plugin in Claude Code, Cursor, Codex, Grok, Gemini CLI, and Hermes Agent.

This repo has no application code. It's a set of static JSON manifests that let each agent marketplace install and SHA-pin the `anchorbrowser` plugin, plus the skill that teaches the agent to drive the SDK.

## What's inside

| Path | Marketplace format |
|------|--------------------|
| `.claude-plugin/marketplace.json` | Claude Code marketplace |
| `.codex-plugin/plugin.json` | Codex plugin |
| `.cursor-plugin/marketplace.json` | Cursor marketplace |
| `.agents/plugins/marketplace.json` | Generic `.agents` marketplace |
| `.grok-plugin/plugin.json` | Grok plugin |
| `.hermes-plugin/plugin.json` | Hermes Agent plugin |
| `gemini-extension.json` | Gemini CLI extension (`GEMINI.md` context file) |

See [`docs/add-a-plugin.md`](docs/add-a-plugin.md) for the full repo layout and how to update the plugin.

## Quick start

- **Claude Code**: add this repo as a plugin marketplace, then install the `anchorbrowser` plugin.
- **Cursor**: add the marketplace, then install `anchorbrowser`.
- **Codex / Grok**: add the repo as a plugin marketplace and install `anchorbrowser`.
- **Gemini CLI**: install this repo as an extension (`gemini-extension.json` + `GEMINI.md`).
- **Hermes Agent**: install the plugin (registers the skill as `anchorbrowser:anchorbrowser`):

```bash
hermes plugins install anchorbrowser/anchorbrowser-plugin --enable
```

Or add this repo as a skill tap:

```bash
hermes skills tap add anchorbrowser/anchorbrowser-plugin
hermes skills install anchorbrowser/anchorbrowser-plugin/anchorbrowser
```

Then just ask your agent:

- *"Go to Hacker News and get the top 5 stories."*
- *"Fill out the signup form on example.com."*
- *"Take a screenshot of the current page."*

No local server, no build step. The agent uses the `anchorbrowser` npm package.

### API key

Cloud sessions, identities, proxies, and CAPTCHA solving use an AnchorBrowser API key:

```bash
export ANCHORBROWSER_API_KEY="your-api-key"
npm install anchorbrowser
```

Get a key at [app.anchorbrowser.io](https://app.anchorbrowser.io/api-key).

## Resources

- [AnchorBrowser TypeScript SDK](https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript)
- [Adding or updating the plugin](docs/add-a-plugin.md)
- [AnchorBrowser](https://anchorbrowser.io)
