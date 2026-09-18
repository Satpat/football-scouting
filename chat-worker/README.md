# football-chat Worker

Stateless Cloudflare Worker that powers the site's **Ask the data** page. It is the only
backend the scouting site has: the site is a static Observable Framework build on GitHub
Pages, and this Worker holds the OpenAI key so the key never touches a visitor's browser.

It stores nothing, and **it never sees football data** — all nine tables are already in the
browser in DuckDB-WASM, so the browser runs the SQL and owns the retry loop. This Worker
only answers "what should I ask next?".

## The contract

`POST /chat` with:

```json
{
  "system": "…schema prompt built in the browser…",
  "messages": [{"role": "user", "content": "top scorers in SL1"}],
  "model": "gpt-5.6-luna"
}
```

returns exactly one of:

```json
{"action": "query",  "sql": "SELECT …", "answer": null, "note": "why"}
{"action": "answer", "sql": null, "answer": "…markdown…", "note": null}
```

The page executes a `query` in DuckDB, appends the rows to `messages`, and posts again —
up to 3 query rounds. `usage` is included so the page can report what a question cost.

**The system prompt is built in the browser**, not here, from `labels.json` + `notes.json`
+ DuckDB `DESCRIBE`. That is deliberate: a data refresh updates the prompt for free, and
tuning the wording ships with a normal `git push` instead of a Worker redeploy. See
`site/src/components/schema-prompt.js`.

## Setup

```bash
npm install
npm run login          # once, to authenticate wrangler with Cloudflare
npm run secret         # paste the OpenAI key — goes to Cloudflare, never to disk
npm run deploy
```

## Local development

Copy `.dev.vars.example` to `.dev.vars` (gitignored), then:

```bash
npm run dev            # http://127.0.0.1:8787
```

Two modes:

- `CHAT_MOCK="1"` — no key, **no OpenAI spend**. The mock walks the same two-phase shape as
  the real model (ask for SQL, then answer), so the page's loop, SQL guard, table rendering
  and deep links can all be tested offline.
- `OPENAI_API_KEY="sk-…"` — real calls, real cost.

> The project's key lives in `~/.zshrc`, which is an *interactive* rc file — `zsh -lc` will
> not see it. Use `zsh -ic 'printf %s "$OPENAI_API_KEY"'` if you need to read it in a script.

Smoke test:

```bash
curl -s localhost:8787/chat -H 'content-type: application/json' \
  -H 'Origin: http://127.0.0.1:3101' \
  -d '{"system":"test","messages":[{"role":"user","content":"hi"}]}'
```

## Configuration

Everything tunable is a const at the top of `worker.js`:

| Const | Purpose |
| --- | --- |
| `MODEL` | `gpt-5.6-luna` (~$0.007/question). Deliberately *not* `rr-tailor`'s `gpt-5.5`/high — that takes 15–30s, which is right for a one-shot resume rewrite and wrong for chat. |
| `REASONING_EFFORT` | `low` — SQL generation is cheap, checkable and retryable. |
| `ALLOWED_MODELS` | What the page's dropdown may escalate to. Keep in sync with `src/chat.md`. |
| `ALLOWED_ORIGINS` | Origin allowlist. Localhost is additionally allowed via `ALLOW_LOCAL`. |
| `MAX_SYSTEM_CHARS` / `MAX_BODY_CHARS` / `MAX_MESSAGES` | Size caps, since the page supplies the system prompt. |

## Security notes

- The key is a Cloudflare secret; it is never in source and never returned to the browser.
- The origin allowlist is a **light deterrent**, not authentication — an `Origin` header can
  be forged with `curl`. Anyone who does so can spend your OpenAI credit. If that ever
  matters, add a shared token or Cloudflare rate limiting.
- The SQL guard lives browser-side in `chat-agent.js`, next to the DuckDB connection that
  has to run the query. It is not a security boundary — all of this data is public and
  already in the visitor's browser — it stops a stray statement corrupting the session.
