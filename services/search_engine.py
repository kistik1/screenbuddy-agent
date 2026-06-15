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
        durations = filtered_df["duration"].fillna("").astype(str).str.lower()
        minutes = pd.to_numeric(
            durations.str.extract(r"(\d+)\s*min", expand=False),
            errors="coerce",
        )
        seasons = pd.to_numeric(
            durations.str.extract(r"(\d+)\s*season", expand=False),
            errors="coerce",
        )

        if duration_preference == "short":
            filtered_df = filtered_df[
                minutes.le(90) | seasons.le(1)
            ]

        elif duration_preference == "medium":
            filtered_df = filtered_df[
                minutes.between(91, 130) | seasons.between(2, 3)
            ]

        elif duration_preference == "long":
            filtered_df = filtered_df[
                minutes.gt(130) | seasons.ge(4)
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

