from surge_score_utils import calculate_surge_score


def test_calculate_surge_score_returns_expected_fields(sample_surge_group):
    sample_surge_group["floor_type"] = "지상"
    result = calculate_surge_score(sample_surge_group)

    assert result is not None
    assert result["sggCd"] == "11710"
    assert result["surge_score"] == 15.0
    assert result["reliability_score"] == 3
    assert result["floor_type"] == "지상"


def test_calculate_surge_score_requires_two_rows(sample_surge_group):
    one_row = sample_surge_group.head(1).copy()
    one_row["floor_type"] = "지상"

    assert calculate_surge_score(one_row) is None
