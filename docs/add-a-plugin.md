# Repo layout

This repo is a **static, single-plugin catalog** — repo root **is** the plugin, one plugin per repo. No build step. Most clients get a `SKILL.md` that drives the TypeScript SDK. Hermes also gets a working [browser provider](https://hermes-agent.nousresearch.com/docs/developer-guide/browser-provider-plugin) (`provider.py`) that creates an Anchor session and returns a CDP URL. The root plugin carries no MCP config. Hermes' MCP servers live in `hermes-mcp/`, where the key is a `${ANCHORBROWSER_API_KEY}` reference that Hermes fills in at run time, so no key is stored in this public, git-pinned repo.

If Anchor Browser ever needs a second distinct plugin, it belongs in its own dedicated repo — not nested inside this one. A nested `plugins/<name>/` layout breaks third-party tools (e.g. Hermes Agent's skill "tap") that scan for `skills/` at repo root by convention.

`hermes-mcp/` is the one exception, and it is not a second product. Hermes loads MCP servers only from a portable `plugin.json` package, and a folder that has a native `plugin.yaml` (the repo root) is never read as one. The package installs with `hermes plugins install "anchorbrowser/anchorbrowser-plugin#hermes-mcp"`. Root `skills/` is unchanged.

## Names

On Claude Code, Cursor, Codex and Grok the plugin and its marketplace are named `anchorbrowser-sdk` (display name "Anchor Browser SDK"). The name `anchorbrowser` on those clients belongs to the hosted MCP plugin in [anchor-mcp-plugin](https://github.com/anchorbrowser/anchor-mcp-plugin), and two plugins with one name cannot be installed together. Gemini CLI, DeepSeek Harness and Hermes have no such overlap and keep `anchorbrowser`. The skill itself is `anchorbrowser` everywhere.

## Layout

```text
.
├── .claude-plugin/marketplace.json      # Claude Code marketplace (source: ".")
├── .claude-plugin/plugin.json           # Claude Code plugin manifest
├── .codex-plugin/plugin.json            # Codex plugin
├── .cursor-plugin/marketplace.json      # Cursor marketplace (source: ".", repo validator reads this)
├── .cursor-plugin/plugin.json           # Cursor plugin manifest
├── .agents/plugins/marketplace.json     # Generic .agents marketplace (path: ".")
├── .grok-plugin/plugin.json             # Grok plugin
├── .hermes-plugin/plugin.json           # Hermes Agent marketplace manifest
├── .hermes-plugin/plugin.yaml           # Hermes native manifest
├── plugin.yaml                          # Hermes install target (kind: backend)
├── __init__.py                          # Hermes register() — browser provider + skill
├── provider.py                          # Anchor BrowserProvider (CDP session lifecycle)
├── agent_access.py                      # hermes anchorbrowser {setup,challenge,submit}
├── hermes-mcp/                          # Hermes portable package: plugin.json + mcp.json + its own skill
├── tests/hermes/                        # provider unit tests and a live check (run with the Hermes interpreter)
├── docs/hermes.md                       # Hermes settings and disclosure
├── gemini-extension.json                # Gemini CLI extension
├── GEMINI.md                            # Gemini context file (SDK skill body, no mcpServers)
├── package.json                         # DeepSeek Harness bundle (dsh.bundle)
├── cordis.patch.yml                     # DSH layer that inserts dsh-anchorbrowser
├── dsh-plugin.js                        # DSH apply() — registers skills/anchorbrowser
├── plugin.json                          # Open Plugin spec manifest (vendor-neutral, e.g. `npx plugins add`)
├── assets/logo.svg
├── skills/anchorbrowser/SKILL.md        # YAML frontmatter: name + description
└── scripts/
    ├── validate-template.mjs            # run by CI and locally, see "Validate" below
    ├── gemini-sync.mjs                  # shared logic: derive GEMINI.md's expected content from SKILL.md
    ├── sync-gemini.mjs                  # regenerates GEMINI.md; --check fails without writing
    ├── version-sync.mjs                 # shared logic: reads the version every manifest must match
    └── sync-version.mjs                 # propagates plugin.json's version to the others; --check fails without writing
```

Every per-format `plugin.json`'s `"skills"` and `"logo"` fields are relative to repo root (`./skills/`, `assets/logo.svg`), and every root marketplace file's `"source"`/`"path"` is `"."`. The root `plugin.json` is a separate, vendor-neutral manifest ([Open Plugin spec](https://github.com/vercel-labs/open-plugin-spec) v1.0.0); it doesn't replace or override any per-client manifest and only needs updating when the plugin's name, version, or metadata changes.

## Updating the skill

- `skills/anchorbrowser/SKILL.md` — YAML frontmatter must include `name` and `description`, plus instructions for using the [`anchorbrowser`](https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript) TypeScript SDK. Edit the skill here (there is no CLI skill to copy).
- `GEMINI.md` — Gemini's extension format has no way to reference an external skill file, so it carries the same instructions as `SKILL.md`'s body, verbatim. After editing `skills/anchorbrowser/SKILL.md`, run `node scripts/sync-gemini.mjs` to regenerate `GEMINI.md`. CI fails if the two drift out of sync.
- DeepSeek Harness reads the same `SKILL.md` at runtime via `dsh-plugin.js`. No extra sync step.
- `assets/logo.svg` — the marketplace display logo.

## Bumping the version

`plugin.json`'s `version` tracks this repo's own release tags (`v0.1.0`, `v0.2.0`, ...), the same as the git tags already used for GitHub Releases. The published Cursor marketplace listing is built by `release.yml`, which only runs on a tag push — merging to `main` alone doesn't update it. `plugin.json` is the single source of truth for the others: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.grok-plugin/plugin.json`, `.hermes-plugin/plugin.json`, `hermes-mcp/plugin.json`, `gemini-extension.json`, and `package.json` must all match it exactly. Keep `plugin.yaml` and `.hermes-plugin/plugin.yaml` on the same version by hand.

To cut a release, bump `plugin.json`'s `version` and run:

```bash
node scripts/sync-version.mjs
```

CI fails if any of them drift out of sync. Once that PR merges to `main`, a second CI job (`tag-release`, in `.github/workflows/validate.yml`) detects the version change and pushes the matching `vX.Y.Z` tag automatically — no one runs `git tag` by hand. That tag push is what triggers `release.yml` to actually validate, package, and publish the release. If `plugin.json`'s version didn't change on a given push to `main`, or a tag for that version already exists, `tag-release` is a no-op.

## Validate

```bash
node scripts/validate-template.mjs
```

Fix all reported errors before committing. This also runs in CI on every pull request and on pushes to `main` (`.github/workflows/validate.yml`).

## Common pitfalls

- Plugin `name` not kebab-case, or not matching a marketplace entry name.
- Missing `.cursor-plugin/plugin.json` at repo root.
- Missing frontmatter keys (`name`, `description`) in `SKILL.md`.
- Broken relative paths for `logo` or `skills` in a manifest.
- A marketplace `source`/`path` pointing at anything other than `"."` — this repo has no nested plugin folder anymore.
- Editing `skills/anchorbrowser/SKILL.md` without running `node scripts/sync-gemini.mjs` afterward — CI fails if `GEMINI.md` drifts out of sync.
- Bumping `plugin.json`'s `version` without running `node scripts/sync-version.mjs` afterward — CI fails if the other manifests drift out of sync.
