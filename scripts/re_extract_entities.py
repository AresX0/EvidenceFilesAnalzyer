from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_agent.db.init_db import init_db, get_session
from case_agent.db.models import EvidenceFile, Entity, ExtractedText
from case_agent.pipelines.entity_extract import extract_entities_for_file
import logging

logging.basicConfig(level=logging.INFO)

DB = Path('C:/Projects/FileAnalyzer/epstein.db')

init_db(DB)
s = get_session()

# Debug: inspect model columns
print('ExtractedText attrs:', [a for a in dir(ExtractedText) if not a.startswith('_')][:50])
try:
    print('ExtractedText table columns:', [c.name for c in ExtractedText.__table__.columns])
except Exception:
    pass

candidates = []
for ef in s.query(EvidenceFile).all():
    # Find the FK column name for evidence id on ExtractedText
    cols = [c.name for c in getattr(ExtractedText, '__table__').columns]
    fk_col = None
    for c in cols:
        if c.endswith('evidence') or 'evidence' in c or c.endswith('file_id') or 'file' in c:
            fk_col = c
            break
    if fk_col is None:
        # fallback: any ExtractedText row where text is not empty
        has_text = s.query(ExtractedText).filter(ExtractedText.text != None).count() > 0
    else:
        has_text = s.query(ExtractedText).filter(getattr(ExtractedText, fk_col) == ef.id).count() > 0

    # inspect Entity columns
    try:
        entity_cols = [c.name for c in Entity.__table__.columns]
        print('Entity columns:', entity_cols)
    except Exception:
        entity_cols = []
    fk_entity_col = None
    for c in entity_cols:
        if c.endswith('evidence') or 'evidence' in c or c.endswith('file_id') or 'file' in c:
            fk_entity_col = c
            break
    if fk_entity_col is None:
        entity_count = s.query(Entity).filter(Entity.text != None).count()
    else:
        entity_count = s.query(Entity).filter(getattr(Entity, fk_entity_col) == ef.id).count()
    if has_text and entity_count == 0:
        candidates.append(ef.path)

logging.info(f'Found {len(candidates)} files to extract entities from')
for p in candidates[:50]:
    try:
        logging.info(f'Extracting entities for {p}')
        extract_entities_for_file(Path(p), db_path=str(DB))
    except Exception as e:
        logging.exception('Failed to extract entities for %s', p)

logging.info('Done')
