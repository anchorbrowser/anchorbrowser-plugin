<p align="center">
  <img src="assets/logo.svg" width="88" height="88" alt="Anchor Browser" />
</p>

<h1 align="center">Anchor Browser Plugin</h1>

<p align="center">
  <strong>Cloud browser for AI agents</strong> — one plugin, seven agents.<br />
  Navigate, extract, fill forms, and screenshot real pages with the
  <a href="https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript">TypeScript SDK</a>.
</p>

<p align="center">
  <a href="#claude-code"><img src="https://img.shields.io/badge/Claude_Code-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude Code" /></a>
  <a href="#cursor"><img src="https://img.shields.io/badge/Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white" alt="Cursor" /></a>
  <a href="#codex"><img src="https://img.shields.io/badge/Codex-10A37F?style=for-the-badge" alt="Codex" /></a>
  <a href="#grok"><img src="https://img.shields.io/badge/Grok-111111?style=for-the-badge&logo=x&logoColor=white" alt="Grok" /></a>
  <a href="#gemini-cli"><img src="https://img.shields.io/badge/Gemini_CLI-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini CLI" /></a>
  <a href="#deepseek-harness"><img src="https://img.shields.io/badge/DeepSeek-4D6BFE?style=for-the-badge&logo=deepseek&logoColor=white" alt="DeepSeek" /></a>
  <a href="#hermes-agent"><img src="https://img.shields.io/badge/Hermes-5B4BDB?style=for-the-badge&logoColor=white" alt="Hermes" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-111111?style=flat-square" alt="version 0.1.0" />
  <img src="https://img.shields.io/badge/license-MIT-2ea44f?style=flat-square" alt="MIT" />
  <a href="https://www.npmjs.com/package/anchorbrowser"><img src="https://img.shields.io/badge/sdk-anchorbrowser-black?style=flat-square" alt="npm anchorbrowser" /></a>
  <a href="https://anchorbrowser.io"><img src="https://img.shields.io/badge/anchorbrowser.io-000000?style=flat-square" alt="anchorbrowser.io" /></a>
</p>

---

This repo is a set of static marketplace manifests plus the skill that teaches each agent to drive the SDK. On **DeepSeek Harness** it is an installable bundle (`dsh plugin add`) that registers the same skill. On **Hermes** it is also a working [browser provider](https://hermes-agent.nousresearch.com/docs/developer-guide/browser-provider-plugin): it creates an Anchor cloud session and hands Hermes a CDP URL so `browser_*` tools work.

No local server. No build step.

## One-click install

These open the desktop app and confirm before anything is installed.

<p align="center">
  <a href="https://cursor.com/link/prompt?text=%2Fadd-plugin%20anchorbrowser%40https%3A%2F%2Fgithub.com%2Fanchorbrowser%2Fanchorbrowser-plugin"><img src="https://img.shields.io/badge/Add_to_Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white" alt="Add to Cursor" /></a>
  <a href="https://cdn.jsdelivr.net/gh/anchorbrowser/anchorbrowser-plugin@main/docs/install-hermes.html"><img src="https://img.shields.io/badge/Install_in_Hermes-5B4BDB?style=for-the-badge" alt="Install in Hermes" /></a>
</p>

## Quick start

**Claude Code** <img src="https://cdn.simpleicons.org/anthropic/D97757" width="16" height="16" alt="" />

```text
/plugin marketplace add anchorbrowser/anchorbrowser-plugin
/plugin install anchorbrowser@anchorbrowser
```

---

**Cursor** <img src="https://cdn.simpleicons.org/cursor/000000" width="16" height="16" alt="" />

[![Add to Cursor](https://img.shields.io/badge/Add_to_Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white)](https://cursor.com/link/prompt?text=%2Fadd-plugin%20anchorbrowser%40https%3A%2F%2Fgithub.com%2Fanchorbrowser%2Fanchorbrowser-plugin)

```text
/add-plugin anchorbrowser@https://github.com/anchorbrowser/anchorbrowser-plugin
```

Or add the marketplace by hand:

```bash
cursor-agent plugin marketplace add https://github.com/anchorbrowser/anchorbrowser-plugin
```

---

**Codex**

```bash
codex plugin marketplace add anchorbrowser/anchorbrowser-plugin
codex plugin add anchorbrowser@anchorbrowser
```

---

**Grok** <img src="https://cdn.simpleicons.org/x/111111" width="16" height="16" alt="" />

```bash
grok plugin marketplace add anchorbrowser/anchorbrowser-plugin
grok plugin install anchorbrowser --trust
```

---

**Gemini CLI** <img src="https://cdn.simpleicons.org/googlegemini/8E75B2" width="16" height="16" alt="" />

```bash
gemini extensions install https://github.com/anchorbrowser/anchorbrowser-plugin --ref=main
```

---

**DeepSeek** <img src="https://cdn.simpleicons.org/deepseek/4D6BFE" width="16" height="16" alt="" />

```bash
dsh plugin --profile web add github:anchorbrowser/anchorbrowser-plugin
```

---

**Hermes** ⚡

[![Install in Hermes](https://img.shields.io/badge/Install_in_Hermes-5B4BDB?style=for-the-badge)](https://cdn.jsdelivr.net/gh/anchorbrowser/anchorbrowser-plugin@main/docs/install-hermes.html)

Or from the terminal:

```bash
hermes plugins install anchorbrowser/anchorbrowser-plugin --enable
```

Then set an API key and ask:

> *Go to Hacker News and get the top 5 stories.*

## Install

### <img src="https://cdn.simpleicons.org/anthropic/D97757" width="20" height="20" alt="" /> Claude Code

Two steps: add this repo as a marketplace, then install the plugin.

Docs: [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins).

**In a Claude Code session**

```text
/plugin marketplace add anchorbrowser/anchorbrowser-plugin
/plugin install anchorbrowser@anchorbrowser
```

Pick a scope when the details pane opens:

| Scope | Who gets it |
| :--- | :--- |
| **User** | You, across all projects |
| **Project** | Everyone who clones the repo (writes `.claude/settings.json`) |
| **Local** | You, this repo only |

If the summary says `Run /reload-plugins to activate.`, run `/reload-plugins`.

If that warns about re-reading the conversation, use `/reload-plugins --force`.

**From your terminal**

```bash
claude plugin marketplace add anchorbrowser/anchorbrowser-plugin
claude plugin install anchorbrowser@anchorbrowser
```

Installs to **user** scope by default.

Pass `--scope project` or `--scope local` to change it.

CLI installs load the next time you start Claude Code, or after `/reload-plugins` in an open session.

**Or browse**

Run `/plugin` → **Discover** and install `anchorbrowser` from the `anchorbrowser` marketplace.

The skill is `/anchorbrowser:anchorbrowser`.

Set `ANCHORBROWSER_API_KEY` and ask Claude to drive a page.

---

### <img src="https://cdn.simpleicons.org/cursor/000000" width="20" height="20" alt="" /> Cursor

[![Add to Cursor](https://img.shields.io/badge/Add_to_Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white)](https://cursor.com/link/prompt?text=%2Fadd-plugin%20anchorbrowser%40https%3A%2F%2Fgithub.com%2Fanchorbrowser%2Fanchorbrowser-plugin)

That opens Cursor with this command ready to run. Confirm the prompt to install.

```text
/add-plugin anchorbrowser@https://github.com/anchorbrowser/anchorbrowser-plugin
```

You can also add the marketplace, then install the plugin in the UI.

There is no non-interactive install CLI yet.

Docs: [Cursor plugins](https://cursor.com/docs/plugins).

```bash
cursor-agent plugin marketplace add https://github.com/anchorbrowser/anchorbrowser-plugin
```

Then either:

- **Customize** in the sidebar → find `anchorbrowser` → **Install** (project or user scope)

- Or run `cursor-agent`, type `/plugin`, open **Marketplace**, and install it there

---

### Codex

```bash
codex plugin marketplace add anchorbrowser/anchorbrowser-plugin
codex plugin add anchorbrowser@anchorbrowser
```

Docs: [Build plugins](https://developers.openai.com/codex/plugins/build).

Refresh later with `codex plugin marketplace upgrade`.

---

### <img src="https://cdn.simpleicons.org/x/111111" width="20" height="20" alt="" /> Grok

```bash
grok plugin marketplace add anchorbrowser/anchorbrowser-plugin
grok plugin install anchorbrowser --trust
```

`--trust` is required to activate the plugin. Without it, Grok shows the source and stops.

Browse from the TUI with `/plugins` or `/marketplace`.

Docs: [Skills, plugins, and marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces).

---

### <img src="https://cdn.simpleicons.org/googlegemini/8E75B2" width="20" height="20" alt="" /> Gemini CLI

```bash
gemini extensions install https://github.com/anchorbrowser/anchorbrowser-plugin --ref=main
```

`--ref=main` installs from the default branch (Gemini otherwise prefers a GitHub release).

Restart the session after install.

Update later with `gemini extensions update`.

Docs: [Gemini CLI extensions](https://google-gemini.github.io/gemini-cli/docs/extensions/).

---

### <img src="https://cdn.simpleicons.org/deepseek/4D6BFE" width="20" height="20" alt="" /> DeepSeek Harness

```bash
dsh plugin --profile web add github:anchorbrowser/anchorbrowser-plugin
```

This installs the `dsh-anchorbrowser` bundle and registers the `anchorbrowser` skill.

Restart `dsh web` after install, then set `ANCHORBROWSER_API_KEY`.

Without a global `dsh` on your PATH:

```bash
npx -p @deepseek-ai/dsh dsh plugin --profile web add github:anchorbrowser/anchorbrowser-plugin
```

Docs: [Package and install a plugin](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/publish).

---

### ⚡ Hermes Agent

[![Install in Hermes](https://img.shields.io/badge/Install_in_Hermes-5B4BDB?style=for-the-badge)](https://cdn.jsdelivr.net/gh/anchorbrowser/anchorbrowser-plugin@main/docs/install-hermes.html)

That opens a short page which launches Hermes Desktop and asks you to confirm. Nothing installs until you do.

Or from the terminal:

```bash
hermes plugins install anchorbrowser/anchorbrowser-plugin --enable
```

Then pick **Anchor Browser** in `hermes tools`, or set `browser.cloud_provider` to `anchorbrowser`.

The skill is also registered as `anchorbrowser:anchorbrowser`.

Proxy country, captcha solving, extra stealth, saved profiles, managed logins, extensions, timeouts and the
rest of Anchor's session options are plain settings. The full list is in [docs/hermes.md](docs/hermes.md).

For Anchor's own tools inside Hermes (web tasks from a prompt, the action index, managed logins, saved tasks,
step-by-step control of a live browser), add the MCP package. It registers Anchor's three hosted MCP servers:

```bash
hermes plugins install "anchorbrowser/anchorbrowser-plugin#hermes-mcp" --enable
```

Docs: [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins).

Skill tap only (no browser backend):

```bash
hermes skills tap add anchorbrowser/anchorbrowser-plugin
hermes skills install anchorbrowser/anchorbrowser-plugin/anchorbrowser
```

## Try it

Once the plugin is installed, just ask:

- *Go to Hacker News and get the top 5 stories.*
- *Fill out the signup form on example.com.*
- *Take a screenshot of the current page.*

## API key

Cloud sessions, identities, proxies, and CAPTCHA solving need an Anchor Browser API key:

```bash
export ANCHORBROWSER_API_KEY="your-api-key"   # also accepts ANCHOR_API_KEY
```

Get a key at [app.anchorbrowser.io](https://app.anchorbrowser.io/api-keys). In Hermes, run `hermes anchorbrowser setup` to paste it. Agent Access is suspended for now.

Install the `anchorbrowser` package from npm when using the TypeScript SDK.

## What's inside

| Path | Format |
| :--- | :--- |
| `.claude-plugin/marketplace.json` | Claude Code marketplace |
| `.codex-plugin/plugin.json` | Codex plugin |
| `.cursor-plugin/marketplace.json` | Cursor marketplace |
| `.agents/plugins/marketplace.json` | Generic `.agents` marketplace |
| `.grok-plugin/plugin.json` | Grok plugin |
| `.hermes-plugin/plugin.json` | Hermes Agent plugin |
| `hermes-mcp/` | Hermes Agent MCP package (Anchor's hosted MCP servers) |
| `gemini-extension.json` | Gemini CLI extension (`GEMINI.md` context file) |
| `package.json` + `cordis.patch.yml` | DeepSeek Harness bundle (`dsh-anchorbrowser`) |

See [`docs/add-a-plugin.md`](docs/add-a-plugin.md) for the full repo layout and how to update the plugin.

## Resources

| | |
| :--- | :--- |
| 🌐 | [anchorbrowser.io](https://anchorbrowser.io) |
| 📦 | [TypeScript SDK](https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript) |
| 🛠️ | [Add or update the plugin](docs/add-a-plugin.md) |
| <img src="https://cdn.simpleicons.org/anthropic/D97757" width="14" height="14" alt="" /> | [Claude Code plugins](https://code.claude.com/docs/en/discover-plugins) |
| <img src="https://cdn.simpleicons.org/cursor/000000" width="14" height="14" alt="" /> | [Cursor plugins](https://cursor.com/docs/plugins) |
| | [Codex plugins](https://developers.openai.com/codex/plugins) |
| <img src="https://cdn.simpleicons.org/x/111111" width="14" height="14" alt="" /> | [Grok plugins](https://docs.x.ai/build/features/skills-plugins-marketplaces) |
| <img src="https://cdn.simpleicons.org/googlegemini/8E75B2" width="14" height="14" alt="" /> | [Gemini CLI extensions](https://google-gemini.github.io/gemini-cli/docs/extensions/) |
| <img src="https://cdn.simpleicons.org/deepseek/4D6BFE" width="14" height="14" alt="" /> | [DeepSeek Harness plugins](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/publish) |
| ⚡ | [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins) |
