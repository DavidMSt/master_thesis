from math import isclose




def limit(value, high, low=None):
    if low is None:
        low = -high

    if value < low:
        return low
    if value > high:
        return high

    return value

def are_lists_approximately_equal(K1, K2, rel_tol=1e-6, abs_tol=1e-6):
    """
    Checks if two lists of float values are approximately equal.

    Parameters:
        K1 (list of float): First list of floating-point numbers.
        K2 (list of float): Second list of floating-point numbers.
        rel_tol (float): Relative tolerance for floating-point comparisons.
        abs_tol (float): Absolute tolerance for floating-point comparisons.

    Returns:
        bool: True if the lists are approximately equal, False otherwise.
    """
    # Check if lists have the same length
    if len(K1) != len(K2):
        return False

    # Check if all corresponding elements are approximately equal
    for a, b in zip(K1, K2):
        if not isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol):
            return False

    return True