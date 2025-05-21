def is_immutable(value):
    """
    Check if a value is immutable.

    :param value: The value to check.
    :return: True if the value is immutable, False otherwise.
    """
    immutable_types = (int, float, str, bool, tuple, frozenset, bytes)

    if isinstance(value, immutable_types):
        # Check immutability of a tuple's elements
        if isinstance(value, tuple):
            return all(is_immutable(item) for item in value)
        return True

    # Check for frozen dataclasses
    if hasattr(value, "__dataclass_fields__") and getattr(value, "__dataclass_params__", None).frozen:
        return True

    return False
