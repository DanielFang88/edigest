# Campus Information Agent

Runs locally on Ubuntu. It uses the read-only methods of the third-party
`edapi` package to read new Ed Discussion threads, saves them in a local
SQLite database, applies a conservative high-value filter, and (when an
OpenRouter key is configured) extracts structured events.

## Setup

```bash
python -m venv .venv
cp .env.example .env
```

Edit `.env` locally and set `ED_API_TOKEN` and `OPENROUTER_API_KEY`. Do not
paste either value into chat or commit `.env`.

## Verify Ed access

```bash
.venv/bin/python -m campus_agent doctor
.venv/bin/python -m campus_agent courses
.venv/bin/python -m campus_agent threads COURSE_ID --limit 5
```

`doctor` only verifies authentication and reports a course count; it does not
print the token. `threads` prints a small, readable sample so that the API
response shape can be checked before data is stored.

## Sync and extraction

```bash
.venv/bin/python -m campus_agent sync --all-courses
.venv/bin/python -m campus_agent events
```

The first sync imports the most recent threads for each course (default 100).
Later runs only process thread IDs not already in SQLite. Only threads that
look staff-authored, announcements, or that contain high-value terms are sent
to OpenRouter. The original content and API responses remain local in
`data/campus_agent.sqlite3`.

## Ubuntu daily update

`python -m campus_agent.daily` runs the full daily workflow: it syncs Ed,
updates the digest, displays a desktop notification with the top items, and
saves the complete digest as a dated text file under
`~/Desktop/Campus Digests/YYYY-MM-DD.txt`. The notification is best-effort,
so the scheduled update still succeeds if no graphical desktop is active.

Each digest item ends with an Ed Discussion `原帖` link. It points to the
specific source thread so the summary can be checked against the original
post.

## Acknowledgments

- [`edapi`](https://github.com/smartspot2/edapi) by
  [smartspot2](https://github.com/smartspot2) provides the third-party Ed API
  integration used by this project. It is unofficial and released under the
  GPL-3.0 license.
- This project was developed with assistance from
  [OpenAI Codex](https://developers.openai.com/codex/).

## Ed API adapter

The project is pinned to `edapi` source revision
`9199e1001eb04b86bb8f68d0c5f9042453cd1387`. The package is an unofficial,
GPL-3.0 implementation and uses the US Ed API host. This project wraps it in
an adapter that only permits user/course lookup, thread listing, and thread
detail retrieval. It never calls its write-capable methods.

### Current API-access limitation

On 2026-09-03, a Python-standard-library client received Cloudflare Error
1010. The project now uses `edapi`'s normal `requests`-based API client rather
than attempting to alter browser identity or bypass access controls. If Ed
rejects a freshly generated token through this client, stop retrying and
contact Ed support.
