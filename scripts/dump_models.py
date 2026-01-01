import case_agent.db.models as m
for name in ('EvidenceFile','FaceMatch','Entity','ExtractedText','Transcription'):
    if hasattr(m, name):
        cls = getattr(m, name)
        print('---', name)
        for c in cls.__table__.columns:
            print(c.name, type(c.type).__name__)
    else:
        print('Missing', name)
