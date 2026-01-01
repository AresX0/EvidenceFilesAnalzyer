"""Simple GUI skeleton to browse people and their files from the generated report.

This is intentionally minimal so it can be imported safely; running it will open a small
Tkinter window listing people and files.
"""
from pathlib import Path

REPORT = Path(r"C:/Projects/FileAnalyzer/reports/epstein_face_report.json")


def load_report(path=REPORT):
    import json
    if not Path(path).exists():
        raise FileNotFoundError(f"Report not found: {path}")
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def run_gui(report_path=REPORT):
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as e:
        print('Tkinter not available:', e)
        return

    rpt = load_report(report_path)
    people = rpt.get('people', [])

    root = tk.Tk()
    root.title('Case Agent — People Explorer')
    root.geometry('900x600')

    left = ttk.Frame(root, width=300)
    left.pack(side='left', fill='y')
    right = ttk.Frame(root)
    right.pack(side='right', fill='both', expand=True)

    lb = tk.Listbox(left)
    lb.pack(fill='both', expand=True)

    for p in people:
        lb.insert('end', f"{p.get('person')} ({p.get('file_count')})")

    text = tk.Text(right)
    text.pack(fill='both', expand=True)

    def on_select(evt):
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        person = people[idx]
        text.delete('1.0', 'end')
        text.insert('end', f"Person: {person.get('person')}\nFiles ({person.get('file_count')}):\n")
        for f in person.get('files', []):
            text.insert('end', f" - {f}\n")

    lb.bind('<<ListboxSelect>>', on_select)

    def export_selected():
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        person = people[idx]
        import csv
        out = Path(r"C:/Projects/FileAnalyzer/reports")
        out.mkdir(parents=True, exist_ok=True)
        fname = out / f"people_{person.get('person').replace(' ', '_')}.csv"
        with fname.open('w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['person', 'file'])
            for f in person.get('files', []):
                w.writerow([person.get('person'), f])
        text.insert('end', f"\nExported to: {fname}\n")

    btn = ttk.Button(left, text='Export person CSV', command=export_selected)
    btn.pack(fill='x')

    root.mainloop()


if __name__ == '__main__':
    run_gui()