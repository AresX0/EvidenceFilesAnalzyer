from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_agent.agent.agent import CaseAgent
from case_agent.reports import generate_extended_report

DB = Path('C:/Projects/FileAnalyzer/epstein.db')
agent = CaseAgent(db_path=str(DB))
print('Generating full synopsis (local fallback)...')
rpt = generate_extended_report(str(DB))
# Build local conservative summary
issues = rpt.get('issues', {})
summary = {
    'entities_count': len(rpt.get('top_entities', [])),
    'events_count': rpt.get('counts', {}).get('events'),
    'files_no_text': len(issues.get('files_no_text', [])),
    'pdfs_no_text': len(issues.get('pdfs_no_text', [])),
}
out = {'source': 'local', 'summary': summary, 'top_entities': rpt.get('top_entities', [])[:50]}
print('--- SYNOPSIS START ---')
print(out)
print('--- SYNOPSIS END ---')
with open('C:/Projects/FileAnalyzer/epstein_synopsis.json', 'w', encoding='utf-8') as fh:
    import json
    json.dump(out, fh, indent=2)
print('Saved synopsis to C:/Projects/FileAnalyzer/epstein_synopsis.json')
