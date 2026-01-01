import json, os
p=r'C:\Projects\FileAnalyzer\reports\epstein_face_report.json'
if not os.path.exists(p):
    print('report not found')
    raise SystemExit(1)
with open(p,'r',encoding='utf-8') as fh:
    j=json.load(fh)
issues=j.get('issues',{})
pdfs_no_text=issues.get('pdfs_no_text',[])
print('pdfs_no_text count:', len(pdfs_no_text))
if pdfs_no_text:
    for x in pdfs_no_text[:20]:
        print('-', x.get('path'))
else:
    print('All PDFs have text extraction.')
