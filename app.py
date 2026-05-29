from fastapi import FastAPI, Request

from agent.conversation_state import ConversationSessionStore
from agent.screenbuddy_agent import ScreenBuddyAgent
from services.catalog_loader import load_catalog
from services.llm_service import generate_recommendation_explanation
from services.search_engine import search_titles
from services.telegram_service import send_telegram_message


app = FastAPI()


TOP_N = 3
MIN_SIMILARITY = 0.2

START_MESSAGE = (
    "Hi, I'm <b>ScreenBuddy</b>. Tell me a little about the kind "
    "of night you're having, and I'll help you find something "
    "that fits."
)

NEW_SESSION_MESSAGE = (
    "Started a new session. Tell me what kind of mood you're in, "
    "and I'll find something that fits."
)

HELP_MESSAGE = (
    "Tell me how you're feeling or what vibe you want to watch. "
    "Use /new to start over, and reply normally if you want me to "
    "refine the recommendations."
)


df, vectorizer, tfidf_matrix = load_catalog()
conversation_store = ConversationSessionStore()
screenbuddy_agent = ScreenBuddyAgent(
    store=conversation_store,
    search_fn=search_titles,
    explanation_fn=generate_recommendation_explanation,
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
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")

    if not chat_id:
        return {
            "ok": False,
            "error": "missing chat_id",
        }

    if text == "/start":
        screenbuddy_agent.reset(chat_id)
        send_telegram_message(chat_id, START_MESSAGE)
        return {"ok": True}

    if text == "/new":
        screenbuddy_agent.reset(chat_id)
        send_telegram_message(chat_id, NEW_SESSION_MESSAGE)
        return {"ok": True}

    if text == "/help":
        send_telegram_message(chat_id, HELP_MESSAGE)
        return {"ok": True}

    agent_response = screenbuddy_agent.handle_message(
        chat_id=chat_id,
        text=text,
    )
    send_telegram_message(chat_id, agent_response.message)
    return {"ok": True}
