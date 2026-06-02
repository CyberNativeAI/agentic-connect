# Lessons

- 2026-06-02: For standing improvement loops, do not treat issue comments, status flips, or repeated verification as meaningful progress. Keep the parent open only when there is active backlog, and when a user asks for sustained improvement, create concrete exploration, implementation, verification, and deployment tasks with named owners.
- 2026-06-02: CyberNative.ai user API credentials can read `/categories.json` but cannot create categories; Discourse returns HTTP 403 on `POST /categories.json`. Category provisioning needs a site admin credential or a CyberNative.ai admin to create it manually before docs can name a real `category_id`.
- 2026-06-02: Discourse rejects self-likes with HTTP 403 and omits the like action on posts where `yours: true`; QA probes must like a readable post authored by another account, and unlike cleanup must include `post_action_type_id=2`.
