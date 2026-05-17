import os
import html
import random
import requests
import pandas as pd

from fastapi import FastAPI, Request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


app = FastAPI()

TELEGRAM_BOT_TOKEN = "8879084175:AAGSzPCKsDkHnD9jKLhIKraMWEAGtgWD6k0"
CSV_PATH = "final_master_catalog_with_clusters.csv"

TOP_N = 3
MIN_SIMILARITY = 0.4

df = pd.read_csv(CSV_PATH)

# Ensure required columns exist
required_columns = [
    "title",
    "description",
    "listed_in",
    "cluster_kmeans",
    "cluster_name",
    "cluster_dbscan",
    "is_outlier",
]

for col in required_columns:
    if col not in df.columns:
        df[col] = ""

df["combined_text"] = (
    df["title"].fillna("").astype(str)
    + " "
    + df["description"].fillna("").astype(str)
    + " "
    + df["listed_in"].fillna("").astype(str)
    + " "
    + df["cluster_name"].fillna("").astype(str)
)

vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(df["combined_text"])


def send_telegram_message(chat_id: int, text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("Missing TELEGRAM_BOT_TOKEN")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as error:
        print(f"Telegram send error: {error}")


def safe(value, default="Unknown"):
    if pd.isna(value) or str(value).strip() == "":
        return default
    return str(value)


def is_true(value) -> bool:
    return str(value).strip().lower() in ["true", "1", "yes", "y"]


def get_more_from_same_cluster(index: int, limit: int = 2):
    current = df.iloc[index]
    cluster = current.get("cluster_kmeans", "")

    if safe(cluster, "") == "":
        return []

    candidates = df[
        (df["cluster_kmeans"].astype(str) == str(cluster))
        & (df.index != index)
    ]

    if candidates.empty:
        return []

    sample_size = min(limit, len(candidates))
    sampled = candidates.sample(sample_size)

    return [safe(row.get("title")) for _, row in sampled.iterrows()]


def get_recommendations(user_query: str) -> str:
    query = user_query.strip()

    if not query:
        return "כתוב לי איזה סוג סרט/סדרה אתה מחפש 🎬"

    query_vector = vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

    top_indices = similarities.argsort()[-TOP_N:][::-1]

    if similarities[top_indices[0]] < MIN_SIMILARITY:
        return (
            "לא מצאתי התאמה מספיק טובה 😅\n\n"
            "נסה לחפש לפי מילים כמו:\n"
            "<code>space</code>, <code>magic</code>, <code>crime</code>, "
            "<code>romance</code>, <code>family</code>, <code>shark</code>"
        )

    response = "🎬 <b>ScreenBuddy Recommendations</b>\n\n"

    for rank, idx in enumerate(top_indices, start=1):
        row = df.iloc[idx]

        title = html.escape(safe(row.get("title")))
        genres = html.escape(safe(row.get("listed_in"), "No genre"))
        description = html.escape(safe(row.get("description"), "No description"))
        score = similarities[idx]

        cluster_id = html.escape(safe(row.get("cluster_kmeans"), "N/A"))
        cluster_name = html.escape(safe(row.get("cluster_name"), "Unknown cluster"))
        dbscan_cluster = html.escape(safe(row.get("cluster_dbscan"), "N/A"))
        outlier = "Yes" if is_true(row.get("is_outlier")) else "No"

        more_titles = get_more_from_same_cluster(idx)
        more_text = ", ".join(html.escape(title) for title in more_titles)
        if not more_text:
            more_text = "No additional titles found"

        short_description = description[:250] + "..." if len(description) > 250 else description

        response += (
            f"<b>{rank}. {title}</b>\n"
            f"Genre: {genres}\n"
            f"Similarity score: <code>{score:.2f}</code>\n"
            f"K-Means cluster: <code>{cluster_id}</code> — {cluster_name}\n"
            f"DBSCAN cluster: <code>{dbscan_cluster}</code>\n"
            f"Outlier: <code>{outlier}</code>\n"
            f"Why recommended: similar text/profile to your request based on TF-IDF + cosine similarity.\n"
            f"More from same cluster: {more_text}\n"
            f"Description: {short_description}\n\n"
        )

    return response


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

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "")

    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": False, "error": "missing chat_id"}

    if text == "/start":
        send_telegram_message(
            chat_id,
            "Hi! I'm <b>ScreenBuddy</b> 🎬\n\n"
            "Write what kind of movie or show you want.\n"
            "Example:\n"
            "<code>I want something like Game of Thrones but less violent</code>",
        )
        return {"ok": True}

    answer = get_recommendations(text)
    send_telegram_message(chat_id, answer)

    return {"ok": True}