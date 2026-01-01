"""Detect common PDF viewers on Windows and provide a helper to prefer open-source viewers like SumatraPDF."""
from pathlib import Path
import shutil

COMMON_PATHS = [
    Path("C:/Program Files/SumatraPDF/SumatraPDF.exe"),
    Path("C:/Program Files (x86)/SumatraPDF/SumatraPDF.exe"),
    Path("C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE"),
]


def detect_pdf_viewer() -> Path | None:
    for p in COMMON_PATHS:
        if p.exists():
            return p
    # fallback to checking PATH for known binaries
    for name in ('sumatrapdf', 'mupdf', 'evince'):
        exe = shutil.which(name)
        if exe:
            return Path(exe)
    return None
