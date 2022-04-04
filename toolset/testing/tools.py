import typing as tp
from copy import deepcopy

from toolset.typing_helpers import ANY_DICT


def copy_dict_with_swap_value(original_dict: ANY_DICT, path: str, value: tp.Any) -> ANY_DICT:
    """
    Assigns given value to a path that is given as string of keys.

    For example:
    For path like "profile.passport_data.code" and value like "123" returns copy
    of the given dict with one change:
    copy_of_given_dict["profile"]["passport_data"]["code"] = "123"
    """
    copied_dict = deepcopy(original_dict)
    *nested_path, nested_key = path.split(".")

    nested_dict = copied_dict
    for key in nested_path:
        nested_dict = nested_dict[key]

    nested_dict[nested_key] = value

    return copied_dict
