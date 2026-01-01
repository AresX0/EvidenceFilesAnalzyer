import json, os
p=r'C:\Projects\FileAnalyzer\reports\epstein_face_report.json'
print('exists', os.path.exists(p))
if os.path.exists(p):
    with open(p,'r',encoding='utf-8') as fh:
        j=json.load(fh)
    print('people count', len(j.get('people',[])))
    print('pdf_synopses count', len(j.get('pdf_synopses',[])))
    print('sample people:', j.get('people',[])[:3])
    print('sample pdf synopsis:', j.get('pdf_synopses',[])[:1])
else:
    print('report not found')