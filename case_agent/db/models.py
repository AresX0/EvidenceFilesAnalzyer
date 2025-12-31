"""SQLAlchemy models for the case agent."""
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, Text, Boolean, JSON, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import ForeignKey
import datetime

Base = declarative_base()

class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    size = Column(Integer)
    mtime = Column(DateTime)
    sha256 = Column(String, index=True, unique=True, nullable=False)
    processed = Column(Boolean, default=False)
    file_metadata = Column(JSON, default={})  # renamed from 'metadata' to avoid SQLAlchemy reserved name

class ExtractedText(Base):
    __tablename__ = "extracted_text"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("evidence_files.id"), index=True)
    page = Column(Integer, nullable=True)
    text = Column(Text)
    provenance = Column(JSON, default={})  # includes sha256 and file path

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("evidence_files.id"), index=True)
    entity_type = Column(String)
    text = Column(String)
    span = Column(String)  # e.g., character offsets or page numbers
    provenance = Column(JSON, default={})
    confidence = Column(String, default="low")  # explicit confidence: low|medium|high

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    description = Column(Text)
    timestamp = Column(String)  # normalized timestamp or 'inferred' flag
    provenance = Column(JSON, default={})

class Transcription(Base):
    __tablename__ = "transcriptions"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("evidence_files.id"), index=True)
    text = Column(Text)
    segments = Column(JSON, default=[])  # list of segment dicts with start/end/text
    provenance = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FaceMatch(Base):
    """Per-probe (crop or image) face match entry.

    - `source` is the probe image path
    - `probe_bbox` is JSON of bbox (if available)
    - `subject` is the labeled subject name when using labeled gallery
    - `gallery_path` is the matching gallery image path
    - `distance` is numeric distance between embeddings (Euclidean)
    - `created_at` timestamp of insertion
    """
    __tablename__ = 'face_matches'
    id = Column(Integer, primary_key=True)
    source = Column(String, index=True)
    probe_bbox = Column(JSON, nullable=True)
    subject = Column(String, nullable=True)
    gallery_path = Column(String, nullable=True)
    distance = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Relationships can be added as needed; left minimal for auditability
