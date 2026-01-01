from case_agent.pipelines.text_extract import reprocess_pdfs_without_text
res = reprocess_pdfs_without_text(r'C:\Projects\FileAnalyzer\file_analyzer.db')
print('Reprocessed', len(res), 'pdfs')
for p in res[:50]:
    print('-', p)
