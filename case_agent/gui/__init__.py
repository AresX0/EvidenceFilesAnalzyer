"""UI components for the Case Agent application.

This package provides a minimal Tkinter-based explorer for people and their
associated files generated from the audit report. The GUI is intentionally
lightweight to remain import-safe in headless test environments.

Expose the main entrypoint `CaseAgentGUI` from `.app` so callers can use:

    from case_agent.gui import CaseAgentGUI

"""

from .agent_ui import CaseAgentGUI

__all__ = ["CaseAgentGUI"]
