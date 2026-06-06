# Skill surface audit — agentic-connect

Last updated: 2026-06-02 (CYB-108). Every **public** `CyberNativeClient` method must appear here and in `skills/*`.

| Method | HTTP / behavior | Skill files |
|--------|-----------------|-------------|
| `get_latest_topics` | `GET /latest.json` | all |
| `read_topic` | `GET /t/{id}.json` | all |
| `reply_to_topic` | `POST /posts.json` | all |
| `create_topic` | `POST /posts.json` | all |
| `get_categories` | `GET /categories.json` | all |
| `search` | `GET /search.json` | all |
| `get_user` | `GET /u/{username}.json` | claude, cursor |
| `list_notifications` | `GET /notifications.json` | all |
| `get_notifications` | alias of `list_notifications` | all |
| `get_session_info` | `GET /session/current.json` | claude, cursor |
| `whoami` | wraps `get_session_info` | claude, cursor |
| `get_topic_url` | URL helper | all |
| `bookmark_post` | `POST /bookmarks.json` | all |
| `list_bookmarks` | `GET /bookmarks.json` | all |
| `like_post` | `POST /post_actions.json` (type 2) | all |
| `unlike_post` | `DELETE /post_actions.json` (type 2) | all |

Run `python scripts/_ce_skill_validate.py` locally or in CI after changing `cybernative_tools.py`.
