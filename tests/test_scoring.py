from axiomiq.core.drift import compute_zscore
from axiomiq.core.scoring import add_risk_score, health_score, top_risks


def test_add_risk_score_runs(sample_df):
    df = compute_zscore(sample_df.copy())
    out = add_risk_score(df)

    assert out is not None
    assert not out.empty
    assert "risk_score" in out.columns


def test_health_score_runs(sample_df):
    df = compute_zscore(sample_df.copy())
    df = add_risk_score(df)

    score = health_score(df)

    # IMPORTANT: health_score returns a float (fleet/engine health score)
    assert isinstance(score, float)
    # keep this loose; exact bounds depend on your scoring model
    assert score == score  # not NaN


def test_top_risks(sample_df):
    df = compute_zscore(sample_df.copy())
    df = add_risk_score(df)

    risks = top_risks(df, top_n=1)
    assert risks is not None
    assert len(risks) == 1
