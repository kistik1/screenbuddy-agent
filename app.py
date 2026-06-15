import os

from fastapi import FastAPI, Request

from agent.conversation_state import ConversationSessionStore
from agent.dialogue_generator import DialogueContext, generate_dialogue
from agent.screenbuddy_agent import ScreenBuddyAgent
from services.catalog_loader import load_catalog
from services.search_engine import search_titles
from services.telegram_service import send_telegram_message


app = FastAPI()


TOP_N = 3
MIN_SIMILARITY = 0.2
DEFAULT_SESSION_TIMEOUT_SECONDS = 300


def _session_timeout_seconds() -> int:
    try:
        value = int(
            os.getenv(
                "SCREENBUDDY_SESSION_TIMEOUT_SECONDS",
                str(DEFAULT_SESSION_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        return DEFAULT_SESSION_TIMEOUT_SECONDS

    if value <= 0:
        return DEFAULT_SESSION_TIMEOUT_SECONDS

    return value


df, vectorizer, tfidf_matrix = load_catalog()
conversation_store = ConversationSessionStore(
    timeout_seconds=_session_timeout_seconds(),
)
screenbuddy_agent = ScreenBuddyAgent(
    store=conversation_store,
    search_fn=search_titles,
    search_context={
        "df": df,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
    },
    top_n=TOP_N,
    min_similarity=MIN_SIMILARITY,
)


@app.get("/")
def health_check():
    return {
        "status": "ScreenBuddy Agent is running",
        "records_loaded": len(df),
    }


@app.get("/health")
def health_check_render():
    return {
        "status": "ok",
        "service": "ScreenBuddy Agent",
        "records_loaded": len(df),
    }


@app.head("/")
def root_head():
    return


@app.head("/health")
def health_head():
    return


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    sender = message.get("from", {})
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")
    user_id = sender.get("id")

    if not chat_id:
        return {
            "ok": False,
            "error": "missing chat_id",
        }

    if not user_id:
        return {
            "ok": False,
            "error": "missing user_id",
        }

    if text == "/start":
        screenbuddy_agent.reset(user_id)
        session = conversation_store.get_or_create(user_id)
        session.add_user_turn(
            text,
            kind="command",
            include_in_messages=False,
        )
        message = generate_dialogue(
            DialogueContext(
                phase="greeting",
                latest_user_message=text,
                session=session,
            )
        )
        session.add_assistant_turn(message, kind="command")
        conversation_store.set(session)
        send_telegram_message(
            chat_id,
            message,
        )
        return {"ok": True}

    if text == "/new":
        screenbuddy_agent.reset(user_id)
        session = conversation_store.get_or_create(user_id)
        session.add_user_turn(
            text,
            kind="command",
            include_in_messages=False,
        )
        message = generate_dialogue(
            DialogueContext(
                phase="session_reset",
                latest_user_message=text,
                session=session,
            )
        )
        session.add_assistant_turn(message, kind="command")
        conversation_store.set(session)
        send_telegram_message(
            chat_id,
            message,
        )
        return {"ok": True}

    if text == "/help":
        session = conversation_store.get(user_id)
        if session is None:
            session = conversation_store.get_or_create(user_id)
        session.add_user_turn(
            text,
            kind="command",
            include_in_messages=False,
        )
        message = generate_dialogue(
            DialogueContext(
                phase="help",
                latest_user_message=text,
                session=session,
            )
        )
        session.add_assistant_turn(message, kind="command")
        conversation_store.set(session)
        send_telegram_message(
            chat_id,
            message,
        )
        return {"ok": True}

    agent_response = screenbuddy_agent.handle_message(
        user_id=user_id,
        text=text,
    )
    send_telegram_message(chat_id, agent_response.message)
    return {"ok": True}
