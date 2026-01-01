"""Media extraction pipeline: extract audio from video and provide transcription hooks.

This module keeps behavior deterministic and auditable; it will only call local
transcription libraries if present, and will never call external services.
"""
from pathlib import Path
import subprocess
import logging
from ..db.init_db import init_db, get_session
from ..db.models import EvidenceFile, Transcription
from ..config import FFMPEG_PATH

logger = logging.getLogger("case_agent.media_extract")

try:
    import whisper  # optional local whisper
except Exception:
    whisper = None


def extract_audio(video_path: Path, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (video_path.stem + ".wav")
    cmd = [FFMPEG_PATH, "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(out_path)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Extracted audio to %s", out_path)
        return out_path
    except Exception as e:
        logger.error("FFmpeg failed extracting audio: %s", e)
        return None


def transcribe_whisper_local(audio_path: Path) -> dict:
    """Transcribe audio using local whisper if available.

    Returns a dict {"segments": [...], "text": "..."}
    If Whisper isn't available, returns an empty but auditable result.
    """
    if whisper is None:
        logger.warning("Whisper not installed; transcription unavailable for %s", audio_path)
        return {"segments": [], "text": ""}
    try:
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path), verbose=False)
    except Exception as e:
        logger.exception("Whisper transcription failed for %s: %s", audio_path, e)
        return {"segments": [], "text": ""}
    # Normalize result for deterministic storage
    segments = []
    for s in result.get("segments", []):
        try:
            segments.append({"start": float(s.get("start", 0.0)), "end": float(s.get("end", 0.0)), "text": s.get("text", "").strip()})
        except Exception:
            logger.exception("Malformed segment in whisper result: %s", s)
    return {"segments": segments, "text": result.get("text", "").strip()}


def persist_transcription(session, file_row, transcription):
    t = Transcription(
        file_id=file_row.id,
        text=transcription.get("text", ""),
        segments=transcription.get("segments", []),
        provenance={"sha256": file_row.sha256, "path": file_row.path},
    )
    session.add(t)
    session.commit()
    logger.info("Saved transcription (id=%s) for file %s", t.id, file_row.path)
    return t


def process_media(path: Path, out_dir: Path, db_path=None):
    init_db(db_path) if db_path is not None else init_db()
    session = get_session()
    file_row = session.query(EvidenceFile).filter_by(path=str(path)).first()
    if not file_row:
        logger.error("File %s not found in DB; run hash_inventory first", path)
        return None
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".wav"}:
        # allow processing of .wav as well for convenience
        audio = path if suffix == ".wav" else extract_audio(path, out_dir)
        if audio:
            transcription = transcribe_whisper_local(audio)
            saved = persist_transcription(session, file_row, transcription)
            return {"transcription_id": saved.id, "segments": transcription.get("segments", []), "text": transcription.get("text", "")}
    else:
        logger.info("No media processing implemented for %s", path)
    return None


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Extract media and transcribe locally")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--out", default="./media_out")
    args = parser.parse_args()
    for p in args.paths:
        process_media(Path(p), Path(args.out))



if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Extract media and transcribe locally")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--out", default="./media_out")
    args = parser.parse_args()
    for p in args.paths:
        process_media(Path(p), Path(args.out))
