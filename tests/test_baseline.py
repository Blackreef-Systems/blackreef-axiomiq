from axiomiq.core.baseline import compute_baseline


def test_compute_baseline_basic(sample_df):
    baseline = compute_baseline(sample_df.copy())

    assert baseline is not None
    assert not baseline.empty

    # Contract expectations (baseline should keep these identifiers)
    for col in ("engine_id", "param", "unit", "min", "max"):
        assert col in baseline.columns

    # Baseline should produce mean/std columns used downstream
    assert ("baseline_mean" in baseline.columns) or ("mean" in baseline.columns)
    assert ("baseline_std" in baseline.columns) or ("std" in baseline.columns)
