"""E6 — Slack bot (Socket Mode): @Astra in a channel or DM → same router as the web chat.

One-time setup (≈5 min):
  1. https://api.slack.com/apps → Create New App → From scratch.
  2. Socket Mode → Enable → generate an App-Level Token with `connections:write`  → SLACK_APP_TOKEN (xapp-…).
  3. OAuth & Permissions → Bot Token Scopes: app_mentions:read, chat:write, im:history, im:read, im:write.
  4. Event Subscriptions → Enable → bot events: app_mention, message.im.
  5. Install to workspace → SLACK_BOT_TOKEN (xoxb-…).
  6. Put both tokens in Astra/.env, then:  python -m astra.slack_bot

The bot answers with the routed engine (risk / onboarding / cited RAG) across ALL
ready repos in the workspace, and lists its sources.
"""

import os
import re

from astra import config  # noqa: F401 — loads .env
from astra import route


def _to_mrkdwn(md: str) -> str:
    """LLM output is GitHub markdown; Slack speaks mrkdwn. Convert the common cases."""
    out = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", md)                 # **bold** → *bold*
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (`\2`)", out)   # [text](path) → text (`path`)
    out = re.sub(r"^#{1,3}\s+(.+)$", r"*\1*", out, flags=re.M)    # headers → bold lines
    return out


def _answer(text: str) -> str:
    question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    if not question:
        return "Ask me about the codebase — risk, onboarding, or anything in the docs/code."
    res = route.dispatch(question)
    skill = {"rag": "cited rag", "risk": "risk engine", "onboarding": "onboarding"}.get(res["skill"], res["skill"])
    out = _to_mrkdwn(res["answer"])
    if res.get("sources"):
        srcs = "\n".join(
            f"• `{s.get('repo') or ''}` {s['source']}" for s in res["sources"][:5]
        )
        out += f"\n\n*Sources* (_{skill}_):\n{srcs}"
    return out


def main() -> None:
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        raise SystemExit(
            "Missing SLACK_BOT_TOKEN (xoxb-…) and/or SLACK_APP_TOKEN (xapp-…) in .env.\n"
            "Follow the setup steps in astra/slack_bot.py's docstring, then re-run."
        )

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=bot_token)

    @app.event("app_mention")
    def on_mention(event, say):
        say(text=_answer(event.get("text", "")), thread_ts=event.get("thread_ts") or event.get("ts"))

    @app.event("message")
    def on_dm(event, say):
        if event.get("channel_type") == "im" and not event.get("bot_id"):
            say(text=_answer(event.get("text", "")))

    print("✶ Astra Slack bot connected (Socket Mode). Mention @Astra or DM it.")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
