# Compatibility shim: re-export and adapt case_agent DB models for older code
from case_agent.db.models import (
    EvidenceFile as _EvidenceFile,
    ExtractedText as ExtractedText,
    Entity as Entity,
    Event as Event,
    Base,
)

class File(_EvidenceFile):
    """Compatibility wrapper: older code expects `File` with attribute `hash`.
    This class maps to the same underlying table as EvidenceFile and provides
    a `hash` property that maps to `sha256`.
    """
    __table__ = _EvidenceFile.__table__

    @property
    def hash(self):
        return self.sha256

    @hash.setter
    def hash(self, v):
        self.sha256 = v

# Note: ExtractedText, Entity, Event are re-exported under their original names

__all__ = ["Base", "File", "ExtractedText", "Entity", "Event"]
