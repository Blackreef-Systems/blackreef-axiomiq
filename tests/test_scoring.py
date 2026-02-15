import pandas as pd
from axiomiq.core.scoring import (
    health_score,
    add_risk_score,
    top_risks,
)


def sample_df():
    return pd.DataFrame({
        "engine_id": ["DG1", "DG2"],
        "risk_score": [10, 50],
        "health_score": [90, 40],
    })


def test_health_score_runs():
    df = sample_df()
    result = health_score(df.copy())
    assert not result.empty


def test_add_risk_score_runs():
    df = sample_df()
    result = add_risk_score(df.copy())
    assert not result.empty


def test_top_risks():
    df = sample_df()
    result = top_risks(df.copy(), n=1)
    assert len(result) == 1
