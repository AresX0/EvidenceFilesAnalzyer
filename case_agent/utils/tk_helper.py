"""Small helpers around Tk availability for tests and headless environments.

Functions:
- is_tk_usable() -> bool

This avoids importing tkinter in places where it's not needed and provides a deterministic
way for tests to skip UI-dependent checks.
"""
from __future__ import annotations


def is_tk_usable() -> bool:
    """Return True if a minimal Tk root can be created and destroyed successfully.

    This is safe to call in tests; it avoids leaving a running event loop.
    """
    try:
        import tkinter as tk
        root = tk.Tk()
        # Some environments may not be fully functional; try update_idletasks
        try:
            root.update_idletasks()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        return True
    except Exception:
        return False
