import typing as tp

Matchable = tp.Union[dict, list, set, tuple]

# assert error messages
_MISSING_ITEM = 'Missing item in partial object (index: {0}, value: "{1}").'
_MORE_ITEMS_IN_PARTIAL = "Partial {0} has more elements than original {1}."
_MORE_ITEMS_IN_ORIGINAL = "Original {0} has more elements than partial {1}."


def assert_matches(  # noqa: WPS231 C901 too complex
    original_object: Matchable, partial_object: Matchable,
) -> bool:
    """
    Rewritten function from matchlib.

    https://github.com/qweeze/matchlib/blob/master/matchlib/main.py

    Matches a given object against another which can contain an Ellipsis (`...`)

    Returns True if object match or match partially with ellipsis.
    Otherwise, raises an error with proper message what do not match.


    Example 1:
    assert_matches({1, 2, 3}, {1, 2, ...})  # True

    Example 2:
    d1 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Flipper"}}
    d2 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Gigi"}}

    assert_matches(d1, d2)

    AssertionError: Dicts have different value for key: 'dogs'. Cause: Sets are unequal.
    Partial set has extra elements: {'Gigi'}.
    Original set has extra elements: {'Flipper'}.
    """
    if isinstance(partial_object, dict) and isinstance(original_object, dict):
        res = _compare_dicts(original_object, partial_object)
        if res:
            return res

    elif isinstance(partial_object, set) and isinstance(original_object, set):
        res = _compare_sets(original_object, partial_object)
        if res:
            return res

    elif isinstance(partial_object, (list, tuple)) and isinstance(original_object, (list, tuple)):
        res = _compare_lists_or_tuples(original_object, partial_object)
        if res:
            return res

    if partial_object == original_object:
        return True
    raise AssertionError(f"{repr(original_object)} != {repr(partial_object)}")


def _compare_dicts(  # noqa: WPS231 C901 too complex
    original_object: Matchable, partial_object: Matchable,
) -> bool:
    """Compares two dicts. Raises assertion error if structures do not match."""
    if ... in partial_object:
        keys = set(partial_object) - {...}
    else:
        keys = set(partial_object) | set(original_object)
    for key in keys:
        if key not in partial_object:
            raise AssertionError(f"Key '{key}' not found in partial object.")
        if key not in original_object:
            raise AssertionError(f"Key '{key}' not found in original object.")
        if partial_object[key] is ...:
            continue
        try:
            assert_matches(original_object[key], partial_object[key])
        except AssertionError as err:
            raise AssertionError(f"Dicts have different value for key: '{key}'. Cause: {str(err)}")

    if ... in partial_object and partial_object[...] is not ...:
        remaining = set(original_object) - set(partial_object) - {...}
        if len(remaining) != 1:
            raise AssertionError(
                "Lengths of the original dict and the partial dict does not match.",
            )
        return assert_matches(original_object[remaining.pop()], partial_object[...])

    return True


def _compare_sets(original_object: Matchable, partial_object: Matchable) -> bool:
    """Compare two sets. Raises assertion error if they not matches."""
    if ... in partial_object:
        if (partial_object - {...}).issubset(original_object):
            return True

        # if does not match with ellipsis
        partial_object.remove(...)
        unique_for_partial = partial_object.difference(original_object)
        raise AssertionError(
            f"There are elements that exist only in partial set: {unique_for_partial}",
        )

    if partial_object == original_object:
        return True

    # if does not match (without ellipsis)
    unique_for_partial = partial_object.difference(original_object)
    unique_for_original = original_object.difference(partial_object)
    msg = "Sets are unequal."
    if unique_for_partial:
        msg = f"{msg}\nPartial set has extra elements: {unique_for_partial}."
    if unique_for_original:
        msg = f"{msg}\nOriginal set has extra elements: {unique_for_original}."
    raise AssertionError(msg)


def _compare_lists_or_tuples(  # noqa: WPS231 C901 too complex
    original_object: Matchable, partial_object: Matchable,
) -> bool:
    """Compare two lists or tuples. Raises assertion error if structures do not match."""
    original_object_type = str(type(original_object))[7:-1]
    partial_object_type = str(type(partial_object))[7:-1]
    obj_idx = 0
    skip = False
    for idx, item in enumerate(partial_object):
        if item is ...:
            if idx == len(partial_object) - 1:
                return True
            skip = True
            continue
        if skip:
            match = False
            while not match:
                try:  # noqa:  WPS229 Found too long ``try`` body length: 2 > 1
                    assert_matches(original_object[obj_idx], item)
                    match = True
                except AssertionError:
                    if obj_idx == len(original_object) - 1:
                        raise AssertionError(  # noqa: WPS220 Found too deep nesting: 24 > 20
                            _MISSING_ITEM.format(obj_idx, original_object[obj_idx]),
                        )
                    obj_idx += 1
                except IndexError:
                    raise AssertionError(f"Extra item in partial {partial_object_type}.")
                skip = False

        if obj_idx >= len(original_object):
            raise AssertionError(
                _MORE_ITEMS_IN_PARTIAL.format(partial_object_type, original_object_type),
            )
        try:
            assert_matches(original_object[obj_idx], item)
        except AssertionError as err:
            raise AssertionError(
                f"Values of the iterables by index {obj_idx} does not match. Cause: {str(err)}.",
            )

        obj_idx += 1

    if not skip and obj_idx != len(original_object):
        raise AssertionError(
            _MORE_ITEMS_IN_ORIGINAL.format(original_object_type, partial_object_type),
        )

    return True
