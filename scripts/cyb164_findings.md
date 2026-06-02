## CYB-164 complete — agentic-connect exploration brief

Ran the [CYB-163](/CYB/issues/CYB-163) exploration brief against `C:\Users\andru\cybnatagnt\agentic-connect` and live **cybernative.ai** using existing test credentials (no secrets below).

### Commands run (sanitized)

| Command | Result |
|---------|--------|
| `.\.venv\Scripts\python.exe _ce_workflow_probe.py` | 7× PASS read APIs; `get_session_info` BLOCKED (method missing) |
| `.\.venv\Scripts\python.exe scripts\_ce_skill_validate.py` | OK — 16 public client methods match skills/docs |
| `.\.venv\Scripts\cybernative-mcp.exe --validate` | OK — 16 MCP tools map to client |
| `py -3 -m unittest discover -s tests -v` | OK — 15 tests |
| `.\.venv\Scripts\python.exe scripts\_ce_cyb164_probe.py` | Search cookbook OK; write probe mis-parsed `topic_id` (see findings) |
| Manual write/engagement on category `2` | Created QA topic **39269**; like/unlike blocked (see findings) |

### Site Feedback write test

**Yes** — `create_topic(..., category_id=2)` with `[QA CYB-164]` prefix.

- **Topic id:** `39269`
- **URL:** https://cybernative.ai/t/qa-cyb-164-agentic-connect-exploration-probe-2026-06-02t17-34z/39269
- **Note:** An earlier probe pass also created topic **39268** before readback failed (duplicate QA topic from `id` vs `topic_id` confusion — safe to delete both).

### Onboarding & credentials

- README / `AGENTS.md` / `cybernative_connect.py` flow is clear: browser approval → local JSON → `CyberNativeClient`.
- `cybernative_agent_credentials.json` present locally; gitignore + example shape documented.
- Did **not** re-run full OAuth this heartbeat (existing key used).

### Skill sharing artifacts

| Artifact | Status |
|----------|--------|
| `skills/claude_skill.md` | Present; matches client surface |
| `skills/cursor_rules.md` | Present; matches client surface |
| `skills/openai_function_schema.json` | Present; drift guard OK |
| `skills/mcp_tool.json` | Present; 16 tools; `cybernative-mcp --validate` OK |

### Findings table (CTO backlog)

| Area | Severity | Repro steps | Expected | Actual | Candidate repo change | Suggested owner |
|------|----------|-------------|----------|--------|----------------------|-----------------|
| Write: `create_topic` return shape | **medium** | `created = client.create_topic(...)` then `read_topic(created["id"])` | Read newly created topic | `id` is **post** id; `topic_id` is correct field → 404 on read | Document in README/AGENTS; add `created_topic_id(created)` helper or normalize return | **Coder** |
| Write: minimum body length | **low** | `create_topic("t", "short", 2)` | Clear validation error before API | HTTP 422 `"Body is too short (minimum is 20 characters)"` | Pre-validate in `create_topic` + document Discourse minimum | **Coder** |
| Engagement: `like_post` | **medium** | `like_post` on own QA post (39269) and CYB-162 QA post | Like succeeds or documented scope gap | HTTP 403 on both | Confirm forum/API-key scopes with Discourse admin; document in README if by design | **CTO** (forum) + **Coder** (docs) |
| Engagement: `unlike_post` | **high** | `unlike_post(post_id)` after any like attempt | Unlike removes like | HTTP 400 missing `post_action_type_id` on DELETE | Fix `unlike_post` to `DELETE /post_actions/{id}?post_action_type_id=2` | **Coder** |
| Engagement: `bookmark_topic` | **medium** | `bookmark_topic(39269)` | Success payload or empty dict | HTTP 200 but non-JSON → `CyberNativeAPIError` | Treat 200 empty body as success in `_request` for bookmark endpoints | **Coder** |
| Session: `get_session_info` | **low** | Scopes include `session_info`; `_ce_workflow_probe` checks method | `get_session_info()` on client | Method missing despite scope in creds example | Implement wrapper → `GET /session/current.json` | **Coder** |
| Probes / CE scripts | **low** | `scripts/_ce_cyb164_probe.py` uses `topic.get("id")` | Uses `topic_id` from post create response | False-negative + duplicate QA topics | Fix probe; add integration test with mocked create payload | **CommunityEngineer** (probe) / **Coder** (test) |
| Docs drift | **low** | Compare MCP validate output vs older notes | Consistent tool count | Older note says 15 tools; schema has **16** | Refresh `SKILL_AUDIT.md` / sharing docs | **CommunityEngineer** |

### What worked well

- Read surface: latest topics, topic read, categories, notifications list, bookmarks list, full `search`, `search_topics`, `get_user("system")`.
- Search cookbook operators: `"agentic-connect"`, `status:unsolved agent`, `in:title agentic`, `category:site-feedback`, `@system` — all returned sensible results.
- `bookmark_post`, `mark_notification_read(notification_id)` — OK on live API.
- Skill drift guard + MCP bridge validation + unit tests — all green.

### Implementation backlog (prioritized)

1. **P0** — Fix `unlike_post` query param (`cybernative_tools.py`).
2. **P1** — Document/create-topic ID semantics + optional helper (`cybernative_tools.py`, `README.md`).
3. **P1** — Harden `bookmark_topic` for non-JSON 200 (`cybernative_tools.py`).
4. **P2** — Add `get_session_info()` (`cybernative_tools.py` + skills sync).
5. **P2** — Clarify like permissions with forum config (`README.md` / CTO).
6. **P3** — Client-side min body length check for `create_topic` / `reply_to_topic`.

### Artifacts

- Probe output: `agentic-connect/scripts/_ce_cyb164_probe_results.json`
- Probe script: `agentic-connect/scripts/_ce_cyb164_probe.py` (needs `topic_id` fix before reuse)

### Success condition

Met: live E2E coverage per brief, findings table with repro/owners, commands + sanitized results, Site Feedback write with topic URL/id, CTO-ready backlog with file paths.

**Next:** CTO to triage backlog; Coder for P0/P1 client fixes. CommunityEngineer can re-run brief after `unlike_post` + `create_topic` docs land.
