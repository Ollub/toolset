from copy import deepcopy

import pytest

from toolset.testing.matching import assert_matches
from toolset.testing.tools import copy_dict_with_swap_value


def test_assert_matches_same_structures(master_payload):
    """Test assert_matches not raises error if compared structures are the same."""
    assert_matches(master_payload, master_payload)


def test_assert_matches_dict_with_partial(master_payload):
    """Test that partial dicts matches the original dict."""
    # dict has ellipsis instead of some keys - should match
    mutated_payload = deepcopy(master_payload)
    mutated_payload.pop("groups")
    mutated_payload[...] = ...
    assert_matches(master_payload, mutated_payload)

    # some keys contain ellipsis instead of actual values - should match
    mutated_payload["created_at"] = ...
    assert_matches(master_payload, mutated_payload)

    # some nested keys contain ellipsis instead of actual values  - should match
    mutated_payload["profile"]["registration_address"] = ...
    assert_matches(master_payload, mutated_payload)


def test_assert_matches_raises_error(master_payload):
    """Test assert_matches raises error if compared structures are not the same."""
    poped_key = "first_name"
    mutated_payload = deepcopy(master_payload)
    mutated_payload.pop(poped_key)

    with pytest.raises(AssertionError) as err:
        assert_matches(master_payload, mutated_payload)

    assert str(err.value) == f"Key '{poped_key}' not found in partial object."  # noqa: WPS441
    # WPS441: Found control variable used after block

    with pytest.raises(AssertionError) as err:
        assert_matches(mutated_payload, master_payload)

    assert str(err.value) == f"Key '{poped_key}' not found in original object."  # noqa: WPS441
    # WPS441: Found control variable used after block


def test_dict_with_partial():
    """Test case where length of dicts with partial is not the same."""
    d1 = {"France": "Paris", "UK": "London", "China": "Beijing"}
    d2 = {"France": "Paris", ...: "London"}

    msg = "Lengths of the original dict and the partial dict does not match."

    with pytest.raises(AssertionError) as err:
        assert_matches(d1, d2)

    assert str(err.value) == msg  # noqa: WPS441 control variable used after block


def test_dict_comparison_raises_proper_message_on_value_difference():
    """Test when values upon the same key in dicts are different we get proper error message."""
    # fmt: off
    msg = """
Dicts have different value for key: 'dogs'. Cause: Sets are unequal.
Partial set has extra elements: {'Gigi'}.
Original set has extra elements: {'Flipper'}.
""".strip("\n")
    # fmt: on

    d1 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Flipper"}}
    d2 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Gigi"}}

    with pytest.raises(AssertionError) as err:
        assert_matches(d1, d2)

    assert str(err.value) == msg  # noqa: WPS441 control variable used after block


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("profile.passport_data", {...: ...}),
        ("profile", {"passport_data": {...: ...}, ...: ...}),
        ("groups", [...]),
    ],
)
def test_assert_matches_correct_partial(master_payload, path, value):
    """Test assert_matches ignores structures with ellipsis."""
    partial_payload = copy_dict_with_swap_value(master_payload, path, value)
    assert_matches(master_payload, partial_payload)


def test_compare_sets_ok():
    """Test matching sets works correctly when sets match or partly match with ellipsis."""
    assert_matches({"cats", "dogs", "snakes"}, {"cats", "dogs", ...})
    assert_matches({"cats", "dogs", "snakes"}, {"cats", "dogs", "snakes"})


def test_compare_sets_is_not_subset():
    """Test assertion error message when one set is not subset of the other."""
    msg = "There are elements that exist only in partial set: {5}"
    with pytest.raises(AssertionError) as err:
        assert_matches({1, 2, 3, 4}, {1, 2, 5, ...})
    assert str(err.value) == msg  # noqa: WPS441 control variable used after block


def test_compare_sets_without_partial():
    """Test when sets do not match (without ellipsis)."""
    # fmt: off
    msg = """
Sets are unequal.
Partial set has extra elements: {5}.
Original set has extra elements: {3, 4}.
""".strip("\n")
    # fmt: on

    with pytest.raises(AssertionError) as err:
        assert_matches({1, 2, 3, 4}, {1, 2, 5})
    assert str(err.value) == msg  # noqa: WPS441 control variable used after block


@pytest.mark.parametrize(
    ("list1", "list2"),
    [([1, 2, 3], [1, 2, 3]), ([1, 2, 3, 4], [..., 2, ..., 4]), ([1, 2, 3, 4], [1, ..., ..., 4])],
)
def test_partial_list_matches(list1, list2):
    """Test that full list matches with partial list."""
    assert_matches(list1, list2)


@pytest.mark.parametrize(
    ("original_list", "partial_list", "error_message"),
    [
        ([1, 2, 3], [1, ..., 2], "Original 'list' has more elements than partial 'list'."),
        ([1, 2, 5], [1, 2, ..., 6], 'Missing item in partial object (index: 2, value: "5").'),
        ([1, 2], [1, 3], "Values of the iterables by index 1 does not match. Cause: 2 != 3."),
        ([1, 2], [1, 2, ..., 3], "Extra item in partial 'list'."),
        ([1, 2], [1, 2, 3], "Partial 'list' has more elements than original 'list'."),
    ],
)
def test_lists_do_not_match(original_list, partial_list, error_message):
    """Test different cases when lists do not match."""
    with pytest.raises(AssertionError) as err:
        assert_matches(original_list, partial_list)

    assert str(err.value) == error_message  # noqa: WPS441 control variable used after block
