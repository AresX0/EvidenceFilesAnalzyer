# Docstring & Documentation Style

Recommendations:
- Use concise module and function docstrings describing purpose, parameters, and return values.
- Follow NumPy or Google docstring style; be consistent across modules.
- Keep docstrings focused (2–6 lines summary) plus an optional longer description and parameter listing.
- Add high-level module docstrings for every package with public API.
- Do not include implementation details that may change; document behavior and contracts.

Example (short):

def foo(x, y):
    """Add two numbers and return result.

    Parameters
    ----------
    x : int
    y : int

    Returns
    -------
    int
        The sum of x and y.
    """
