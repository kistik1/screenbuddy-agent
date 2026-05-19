import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


CSV_PATH = "final_master_catalog_with_clusters.csv"


REQUIRED_COLUMNS = [
    "title",
    "description",
    "genre_1",
    "genre_2",
    "genre_3",
    "cluster_kmeans",
    "cluster_name",
    "cluster_dbscan",
    "is_outlier",
    "release_year",
    "duration",
    "target_audience",
    "age_category",
    "streaming",
    "type"
]


CUSTOM_STOP_WORDS = list(
    ENGLISH_STOP_WORDS.union(
        {
            "recommend",
            "movie",
            "movies",
            "film",
            "films",
            "show",
            "series",
            "want",
            "looking",
            "called",
            "please",
            "something",
            "find",
            "watch",
        }
    )
)


def safe_text(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return ""
    return str(value).strip()


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df


def build_listed_in(df: pd.DataFrame) -> pd.DataFrame:
    df["listed_in"] = (
        df["genre_1"].fillna("").astype(str)
        + ", "
        + df["genre_2"].fillna("").astype(str)
        + ", "
        + df["genre_3"].fillna("").astype(str)
    )

    return df


def build_combined_text(df: pd.DataFrame) -> pd.DataFrame:
    df["combined_text"] = (
        df["title"].fillna("").astype(str).str.lower()
        + " "
        + df["description"].fillna("").astype(str).str.lower()
        + " "
        + df["listed_in"].fillna("").astype(str).str.lower()
        + " "
        + df["cluster_name"].fillna("").astype(str).str.lower()
        + " "
        + df["release_year"].fillna("").astype(str).str.lower()
        + " "
        + df["duration"].fillna("").astype(str).str.lower()
        + " "
        + df["target_audience"].fillna("").astype(str).str.lower()
        + " "
        + df["age_category"].fillna("").astype(str).str.lower()
        + " "
        + df["streaming"].fillna("").astype(str).str.lower()
        + " "
        + df["type"].fillna("").astype(str).str.lower()
    )

    return df


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")

    return df


def load_catalog(csv_path: str = CSV_PATH):
    df = pd.read_csv(csv_path)

    df = ensure_required_columns(df)
    df = build_listed_in(df)
    df = normalize_numeric_columns(df)
    df = build_combined_text(df)

    vectorizer = TfidfVectorizer(
        stop_words=CUSTOM_STOP_WORDS,
        max_features=5000,
    )

    tfidf_matrix = vectorizer.fit_transform(df["combined_text"])

    return df, vectorizer, tfidf_matrix
