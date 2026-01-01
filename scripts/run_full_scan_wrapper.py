import sys
sys.path.insert(0, r'C:\Projects\FileAnalyzer')
# Update these paths as needed or pass via environment/args
sys.argv = ['full_face_scan.py',
            '--evidence', r'C:\Users\doran\OneDrive - Say Family\legal analysis\Epstein',
            '--gallery', r'C:\Projects\FileAnalyzer\Images',
            '--db', r'C:\Projects\FileAnalyzer\file_analyzer.db',
            '--faces-out', r'C:\Projects\FileAnalyzer\faces_all',
            '--threshold', '0.9',
            '--top-k', '5',
            '--aggregate',
            '--report-out', r'C:\Projects\FileAnalyzer\reports']

from scripts.full_face_scan import main
if __name__ == '__main__':
    main()
