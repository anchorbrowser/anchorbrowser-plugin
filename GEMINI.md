# AnchorBrowser TypeScript SDK

Use the [`anchorbrowser`](https://www.npmjs.com/package/anchorbrowser) npm package. Do **not** use the deprecated `anchorbrowser` CLI (`@anchor-browser/cli`).

Docs: [SDK reference](https://docs.anchorbrowser.io/sdk-reference/overview) · source: [AnchorBrowser-SDK-Typescript](https://github.com/anchorbrowser/AnchorBrowser-SDK-Typescript)

## Setup Check

```bash
[ -n "${ANCHORBROWSER_API_KEY:-}" ] && echo "ANCHORBROWSER_API_KEY is set" || echo "ANCHORBROWSER_API_KEY is missing"
```

Install the `anchorbrowser` package from npm if it is not already in the project.

The SDK reads `ANCHORBROWSER_API_KEY` from the environment. Get a key at [app.anchorbrowser.io](https://app.anchorbrowser.io/api-keys). Set it explicitly only when needed:

```ts
import { client } from 'anchorbrowser';
client.setConfig({ auth: () => process.env.ANCHORBROWSER_API_KEY! });
```

Run snippets with `npx tsx` (or a temp `.ts` file). Execute — do not only describe the API.

## When To Use Which API

- **`agentTask`** — default for "go do this on the web" (navigate, extract, fill forms).
- **`Tools`** — one-shot fetch / screenshot / PDF / performWebTask.
- **`createBrowser` / `Sessions`** — multi-step Playwright control over a cloud session.
- **`Identities` / `Applications`** — stored logins attached to a session.
- **`Tasks`** — run a predefined task ID with input params.

## Agent task (default)

```ts
import { agentTask } from 'anchorbrowser';

const result = await agentTask('Go to news.ycombinator.com and return the top 5 story titles', {
  taskOptions: { url: 'https://news.ycombinator.com' },
});
console.log(result.data.result);
```

## Tools (one-shot)

```ts
import { Tools } from 'anchorbrowser';

const page = await Tools.fetchWebpage({ body: { url: 'https://example.com' } });
const shot = await Tools.screenshotWebpage({ body: { url: 'https://example.com' } });
const pdf = await Tools.createPagePdf({ body: { url: 'https://example.com' } });
const task = await Tools.performWebTask({
  body: { prompt: 'go to ycombinator hacker news and get top 10 news' },
});
```

## Session + Playwright

```ts
import { createBrowser, Sessions } from 'anchorbrowser';

const { browser, session } = await createBrowser({
  sessionOptions: { session: { recording: { active: true } } },
});
const page = browser.contexts()[0].pages()[0];
await page.goto('https://example.com');
console.log(await page.title());
await browser.close();
await Sessions.deleteSession({ path: { session_id: session.data.id } });
```

OS-level session helpers (no Playwright) live on `Sessions`: `goto`, mouse, keyboard, clipboard, screenshot, upload.

## Identities

```ts
import { Identities, Sessions } from 'anchorbrowser';

const identity = await Identities.createIdentity({
  body: { source: 'https://app.example' },
});
const session = await Sessions.createSession({
  body: { identities: [{ id: identity.data.id }] },
});
```

## Predefined tasks

```ts
import { Tasks } from 'anchorbrowser';

const run = await Tasks.runTask({
  path: { taskId: '<task-id>' },
  body: { input_params: { query: 'engineer' } },
});
```

## Execution Expectations

- Execute the SDK call; return the result, not only sample code.
- Prefer `agentTask` unless the user needs a screenshot, PDF, raw fetch, or a Playwright loop.
- After creating a session, delete it when the task is done.
- If auth fails, check `ANCHORBROWSER_API_KEY` — do not fall back to the deprecated CLI.
