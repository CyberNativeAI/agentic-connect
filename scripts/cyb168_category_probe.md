# CYB-168 Agent QA Sandbox Category Probe

Date: 2026-06-02

Objective: create a dedicated low-traffic CyberNative.ai category for agentic-connect QA posts, then update docs/skills with the resulting category id and moderation policy.

Live category read check:

- Command: `CyberNativeClient().get_categories()`
- Result: succeeded.
- Existing low-traffic fallback: `Site Feedback`, id `2`, slug `site-feedback`, topic_count `112`.
- Dedicated `agent-qa-sandbox` category: not present.

Live category creation attempt:

- Endpoint: `POST /categories.json`
- Payload summary: name `Agent QA Sandbox`, slug `agent-qa-sandbox`, color `3AB54A`, text color `FFFFFF`, public create/reply/read permission.
- Result: failed with HTTP 403, `["You are not permitted to view the requested resource."]`.

Conclusion:

The local CyberNative user API credential can verify categories but cannot administer category creation. CYB-168 is blocked until a CyberNative.ai site admin creates the category or provides an approved admin API credential for this one provisioning step.

After the category exists, update these repo references from `Site Feedback` id `2` to the new category id:

- `README.md`
- `AGENTS.md`
- `docs/SHARING_SKILLS.md`
- `skills/claude_skill.md`
- `skills/cursor_rules.md`
- `skills/mcp_tool.json`
- `skills/openai_function_schema.json`
- `SKILL_AUDIT.md`

Moderation and retention policy to document:

- Purpose: agentic-connect QA probes only; every write should include the issue id and be clearly labeled as agent QA.
- Volume: low-volume manual or issue-scoped probes, not load testing or repeated automation.
- Cleanup: remove accidental duplicates and undo non-idempotent test actions such as likes/bookmarks when possible.
- Retention: keep useful reproductions and findings; periodically archive/delete obsolete probe-only topics after the linked issue is resolved.
