import html
from typing import Dict, List

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def safe(value, default="Unknown"):
    if pd.isna(value) or str(value).strip() == "":
        return default

    return str(value)


def is_true(value) -> bool:
    return str(value).strip().lower() in [
        "true",
        "1",
        "yes",
        "y",
    ]


def apply_filters(
    df: pd.DataFrame,
    parsed_query: Dict,
) -> pd.DataFrame:
    filtered_df = df.copy()

    release_year_min = parsed_query.get("release_year_min")
    release_year_max = parsed_query.get("release_year_max")

    streaming = parsed_query.get("streaming")
    target_audience = parsed_query.get("target_audience")
    age_category = parsed_query.get("age_category")

    content_type = parsed_query.get("type")

    duration_preference = parsed_query.get("duration_preference")

    if release_year_min:
        filtered_df = filtered_df[
            filtered_df["release_year"] >= release_year_min
        ]

    if release_year_max:
        filtered_df = filtered_df[
            filtered_df["release_year"] <= release_year_max
        ]

    if streaming:
        filtered_df = filtered_df[
            filtered_df["streaming"]
            .astype(str)
            .str.lower()
            .str.contains(streaming.lower(), na=False)
        ]

    if target_audience:
        filtered_df = filtered_df[
            filtered_df["target_audience"]
            .astype(str)
            .str.lower()
            .str.contains(target_audience.lower(), na=False)
        ]

    if age_category:
        filtered_df = filtered_df[
            filtered_df["age_category"]
            .astype(str)
            .str.lower()
            .str.contains(age_category.lower(), na=False)
        ]
    if content_type:
        filtered_df = filtered_df[
            filtered_df["type"]
            .astype(str)
            .str.lower()
            .str.contains(content_type.lower(), na=False)
        ]
    if duration_preference:
        if duration_preference == "short":
            filtered_df = filtered_df[
                filtered_df["duration"]
                .astype(str)
                .str.contains(
                    "60|70|80|90|1 season",
                    case=False,
                    na=False,
                    regex=True,
                )
            ]

        elif duration_preference == "medium":
            filtered_df = filtered_df[
                filtered_df["duration"]
                .astype(str)
                .str.contains(
                    "100|110|120|2 seasons|3 seasons",
                    case=False,
                    na=False,
                    regex=True,
                )
            ]

        elif duration_preference == "long":
            filtered_df = filtered_df[
                filtered_df["duration"]
                .astype(str)
                .str.contains(
                    "140|150|4 seasons|5 seasons|6 seasons",
                    case=False,
                    na=False,
                    regex=True,
                )
            ]

    return filtered_df


def get_more_from_same_cluster(
    df: pd.DataFrame,
    index: int,
    limit: int = 2,
):
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

    return [
        safe(row.get("title"))
        for _, row in sampled.iterrows()
    ]


def build_recommendation_object(
    row,
    similarity_score: float,
    more_titles: List[str],
):
    return {
        "title": safe(row.get("title")),
        "genres": safe(row.get("listed_in"), "No genre"),
        "description": safe(
            row.get("description"),
            "No description",
        ),
        "type": safe(row.get("type")),
        "release_year": safe(row.get("release_year")),
        "duration": safe(row.get("duration")),
        "target_audience": safe(
            row.get("target_audience")
        ),
        "age_category": safe(
            row.get("age_category")
        ),
        "streaming": safe(row.get("streaming")),
        "similarity_score": round(similarity_score, 2),
        "cluster_id": safe(
            row.get("cluster_kmeans"),
            "N/A",
        ),
        "cluster_name": safe(
            row.get("cluster_name"),
            "Unknown cluster",
        ),
        "dbscan_cluster": safe(
            row.get("cluster_dbscan"),
            "N/A",
        ),
        "is_outlier": is_true(
            row.get("is_outlier")
        ),
        "more_from_cluster": more_titles,
    }


def search_titles(
    user_query: str,
    parsed_query: Dict,
    df: pd.DataFrame,
    vectorizer,
    tfidf_matrix,
    top_n: int = 3,
    min_similarity: float = 0.25,
):
    filtered_df = apply_filters(
        df=df,
        parsed_query=parsed_query,
    )

    if filtered_df.empty:
        return []

    filtered_indices = filtered_df.index.tolist()

    filtered_matrix = tfidf_matrix[filtered_indices]

    semantic_query = parsed_query.get(
        "query_text",
        user_query,
    )

    query_vector = vectorizer.transform(
        [semantic_query]
    )

    similarities = cosine_similarity(
        query_vector,
        filtered_matrix,
    ).flatten()

    top_positions = similarities.argsort()[-top_n:][::-1]

    recommendations = []

    for position in top_positions:
        similarity_score = similarities[position]

        if similarity_score < min_similarity:
            continue

        real_index = filtered_indices[position]

        row = df.iloc[real_index]

        more_titles = get_more_from_same_cluster(
            df=df,
            index=real_index,
        )

        recommendation = build_recommendation_object(
            row=row,
            similarity_score=similarity_score,
            more_titles=more_titles,
        )

        recommendations.append(recommendation)

    return recommendations


def format_recommendations_message(
    recommendations: List[Dict],
    llm_explanation: str = "",
) -> str:
    if not recommendations:
        return (
            "⚠️ I could not find a strong enough match."
        )

    response = (
        "🎬 <b>ScreenBuddy Recommendations</b>\n\n"
    )

    if llm_explanation:
        response += (
            f"{html.escape(llm_explanation)}\n\n"
        )

    for rank, item in enumerate(
        recommendations,
        start=1,
    ):
        title = html.escape(item["title"])

        genres = html.escape(item["genres"])

        description = html.escape(
            item["description"]
        )

        release_year = html.escape(
            item["release_year"]
        )

        duration = html.escape(
            item["duration"]
        )

        target_audience = html.escape(
            item["target_audience"]
        )

        age_category = html.escape(
            item["age_category"]
        )
        content_type = html.escape(
            item["type"]
        )
        streaming = html.escape(
            item["streaming"]
        )

        cluster_name = html.escape(
            item["cluster_name"]
        )

        cluster_id = html.escape(
            item["cluster_id"]
        )

        dbscan_cluster = html.escape(
            item["dbscan_cluster"]
        )

        outlier = (
            "Yes"
            if item["is_outlier"]
            else "No"
        )

        more_text = ", ".join(
            html.escape(title)
            for title in item["more_from_cluster"]
        )

        if not more_text:
            more_text = (
                "No additional titles found"
            )

        short_description = (
            description[:250] + "..."
            if len(description) > 250
            else description
        )

        response += (
            f"<b>{rank}. {title}</b>\n"
            f"Genres: {genres}\n"
            f"Year: {release_year}\n"
            f"Duration: {duration}\n"
            f"Audience: {target_audience}\n"
            f"Age category: {age_category}\n"
            f"Streaming: {streaming}\n"
            f"Type: {content_type}\n"
            f"Similarity score: "
            f"<code>{item['similarity_score']}</code>\n"
            f"K-Means cluster: "
            f"<code>{cluster_id}</code> "
            f"— {cluster_name}\n"
            f"DBSCAN cluster: "
            f"<code>{dbscan_cluster}</code>\n"
            f"Outlier: <code>{outlier}</code>\n"
            f"More from same cluster: "
            f"{more_text}\n"
            f"Description: "
            f"{short_description}\n\n"
        )

    return response