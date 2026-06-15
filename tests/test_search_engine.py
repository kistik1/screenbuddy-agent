import pandas as pd

from services.search_engine import apply_filters


def test_short_duration_includes_short_specials_and_one_season_shows():
    df = pd.DataFrame(
        {
            "title": ["Special", "Movie", "Show", "Long Movie", "Long Show"],
            "duration": ["44 min", "89 min", "1 Season", "131 min", "4 Seasons"],
        }
    )

    filtered = apply_filters(df, {"duration_preference": "short"})

    assert filtered["title"].tolist() == ["Special", "Movie", "Show"]


def test_medium_and_long_duration_use_numeric_ranges():
    df = pd.DataFrame(
        {
            "title": ["Medium Movie", "Medium Show", "Long Movie", "Long Show"],
            "duration": ["105 min", "3 Seasons", "145 min", "5 Seasons"],
        }
    )

    medium = apply_filters(df, {"duration_preference": "medium"})
    long = apply_filters(df, {"duration_preference": "long"})

    assert medium["title"].tolist() == ["Medium Movie", "Medium Show"]
    assert long["title"].tolist() == ["Long Movie", "Long Show"]
