from axiomiq.core.drift import add_limit_proximity, add_slope_per_day, compute_zscore


def test_add_limit_proximity(sample_df):
    out = add_limit_proximity(sample_df.copy())
    assert out is not None
    assert not out.empty


def test_add_slope_per_day(sample_df):
    out = add_slope_per_day(sample_df.copy())
    assert out is not None
    assert not out.empty


def test_compute_zscore(sample_df):
    out = compute_zscore(sample_df.copy())
    assert out is not None
    assert not out.empty
    # z-score column name is typically "z" — if yours differs, change here once.
    assert "z" in out.columns
