"""Central logging configuration for case_agent."""
import logging
from pathlib import Path


def setup_logging(level: int = logging.INFO, logfile: str | Path | None = None):
    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    # clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if logfile:
        fh = logging.FileHandler(str(logfile))
        fh.setFormatter(fmt)
        root.addHandler(fh)
    logging.getLogger("case_agent").debug("Logging configured. level=%s logfile=%s", level, logfile)
