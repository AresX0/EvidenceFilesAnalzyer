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


def export_person_csv(person: dict, out_dir: str | Path):
    """Export a person's file list to CSV with sha256 and thumbnail columns. Returns the Path to the CSV."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / f"people_{person.get('person').replace(' ', '_')}.csv"
    from case_agent.pipelines.hash_inventory import sha256_file
    from case_agent.utils.thumbs import thumbnail_for_image
    import csv
    with fname.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['person', 'file', 'sha256', 'thumbnail'])
        for f in person.get('files', []):
            try:
                sha = sha256_file(Path(f))
            except Exception:
                sha = ''
            try:
                thumb = thumbnail_for_image(f, out_dir, size=(160, 120))
            except Exception:
                thumb = ''
            w.writerow([person.get('person'), f, sha, str(thumb)])
    return fname


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

    # Left panel (search + list)
    left = ttk.Frame(root, width=300)
    left.pack(side='left', fill='y')
    right = ttk.Frame(root)
    right.pack(side='right', fill='both', expand=True)

    # Search + sort + filter controls
    search_var = tk.StringVar()
    search_entry = ttk.Entry(left, textvariable=search_var)
    search_entry.pack(fill='x', pady=(2,4))

    sort_var = tk.StringVar(value='Name (A-Z)')
    sort_combo = ttk.Combobox(left, textvariable=sort_var, values=['Name (A-Z)', 'Files (desc)'], state='readonly')
    sort_combo.pack(fill='x')

    type_filter_var = tk.StringVar()
    type_filter_entry = ttk.Entry(left, textvariable=type_filter_var)
    type_filter_entry.pack(fill='x', pady=(4,6))
    type_filter_entry.insert(0, 'Filter by extension (e.g. .jpg)')

    lb = tk.Listbox(left)
    lb.pack(fill='both', expand=True)

    # Keep a working list of people that matches current filters
    _filtered_people = list(people)

    def refresh_people_list():
        q = search_var.get().lower()
        ft = type_filter_var.get().strip().lower()
        sort = sort_var.get()
        # filter
        out = []
        for p in people:
            name = p.get('person', '')
            files = p.get('files', [])
            if q and q not in name.lower():
                continue
            if ft and ft != '':
                # check if any file has that extension
                ok = False
                for f in files:
                    if f.lower().endswith(ft):
                        ok = True
                        break
                if not ok:
                    continue
            out.append(p)
        # sort
        if sort == 'Files (desc)':
            out.sort(key=lambda x: x.get('file_count', 0), reverse=True)
        else:
            out.sort(key=lambda x: x.get('person', '').lower())
        # update listbox
        lb.delete(0, 'end')
        for p in out:
            lb.insert('end', f"{p.get('person')} ({p.get('file_count')})")
        # store filtered
        nonlocal _filtered_people
        _filtered_people = out

    # initial population
    refresh_people_list()

    # Right pane: details, matches, preview, and thumbnail gallery
    top_frame = ttk.Frame(right)
    top_frame.pack(fill='x')
    text = tk.Text(right, height=8)
    text.pack(fill='x')

    matches_label = ttk.Label(top_frame, text='Top face matches')
    matches_label.pack(side='left')
    matches_lb = tk.Listbox(top_frame, height=6)
    matches_lb.pack(side='left', fill='y')

    # Thumbnail gallery area with a canvas + scrollbar
    gallery_frame = ttk.Frame(right)
    gallery_frame.pack(fill='both', expand=True)

    canvas = tk.Canvas(gallery_frame)
    vbar = ttk.Scrollbar(gallery_frame, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)

    thumbs_container = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=thumbs_container, anchor='nw')

    preview = ttk.Label(right)
    preview.pack(fill='both', expand=True)

    # Keep references to Tk images so they don't get GC'd
    _tk_thumb_refs = []

    def update_matches_for_person(person):
        # Query DB for top matched subjects for this person's files
        files = person.get('files', [])
        matches_lb.delete(0, 'end')
        if not files:
            return
        import sqlite3
        conn = sqlite3.connect(r'C:/Projects/FileAnalyzer/file_analyzer.db')
        cur = conn.cursor()
        placeholders = ','.join('?' for _ in files)
        q = f"SELECT subject, COUNT(*) as c FROM face_matches WHERE source IN ({placeholders}) GROUP BY subject ORDER BY c DESC LIMIT 10"
        cur.execute(q, files)
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            matches_lb.insert('end', f"{r[0]} ({r[1]})")

    # Thumbs: use thumbnail util to generate cached thumbnails and show them
    def show_thumbnails_for_person(person):
        # Clear container
        for child in thumbs_container.winfo_children():
            child.destroy()
        _tk_thumb_refs.clear()
        files = person.get('files', [])
        if not files:
            return
        from case_agent.utils.thumbs import thumbnail_for_image
        from PIL import Image, ImageTk
        # show up to first 50 thumbnails in a simple grid
        cols = 4
        for idx, fpath in enumerate(files[:200]):
            try:
                thumb_path = thumbnail_for_image(fpath, Path(r"C:/Projects/FileAnalyzer/reports"), size=(160, 120))
                img = Image.open(thumb_path)
                tkimg = ImageTk.PhotoImage(img)
            except Exception:
                img = Image.new('RGB', (160, 120), color=(220, 220, 220))
                tkimg = ImageTk.PhotoImage(img)
            lbl = ttk.Label(thumbs_container, image=tkimg)
            lbl.image = tkimg
            # attach filepath for click handler
            lbl.filepath = fpath
            r = idx // cols
            c = idx % cols
            lbl.grid(row=r, column=c, padx=4, pady=4)

            def on_click(ev, p=fpath):
                # show full image in preview
                try:
                    pil = Image.open(p)
                    pil.thumbnail((800, 600))
                    tkp = ImageTk.PhotoImage(pil)
                    preview.image = tkp
                    preview.config(image=tkp, text='')
                except Exception:
                    preview.config(text=f'Cannot open: {p}')
            lbl.bind('<Button-1>', on_click)
            lbl.bind('<Double-1>', lambda ev, p=fpath: __import__('os').startfile(p))

            # right-click context menu
            def on_right_click(ev, p=fpath):
                menu = tk.Menu(root, tearoff=0)
                menu.add_command(label='Open file', command=lambda: __import__('os').startfile(p))
                menu.add_command(label='Reveal in Explorer', command=lambda: __import__('subprocess').run(['explorer', '/select,', p]))
                try:
                    menu.tk_popup(ev.x_root, ev.y_root)
                finally:
                    menu.grab_release()
            lbl.bind('<Button-3>', on_right_click)
            _tk_thumb_refs.append(tkimg)
        # update scrollregion
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))

    def show_gallery_for_selected_match(evt=None):
        sel = matches_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        text_val = matches_lb.get(idx)
        subject = text_val.split(' (')[0]
        # Find a gallery_path for this subject from DB
        import sqlite3
        conn = sqlite3.connect(r'C:/Projects/FileAnalyzer/file_analyzer.db')
        cur = conn.cursor()
        cur.execute("SELECT gallery_path FROM face_matches WHERE subject=? LIMIT 1", (subject,))
        row = cur.fetchone()
        conn.close()
        if not row or not row[0]:
            preview.config(text='No gallery image')
            return
        gpath = row[0]
        try:
            from PIL import Image, ImageTk
            img = Image.open(gpath)
            img.thumbnail((600, 400))
            tkimg = ImageTk.PhotoImage(img)
            preview.image = tkimg
            preview.config(image=tkimg, text='')
        except Exception as e:
            preview.config(text=f'Cannot open image: {gpath}')

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
        update_matches_for_person(person)
        show_thumbnails_for_person(person)

    lb.bind('<<ListboxSelect>>', on_select)
    matches_lb.bind('<<ListboxSelect>>', show_gallery_for_selected_match)

    def export_selected():
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        person = people[idx]
        out = Path(r"C:/Projects/FileAnalyzer/reports")
        out.mkdir(parents=True, exist_ok=True)
        fname = export_person_csv(person, out)
        text.insert('end', f"\nExported to: {fname}\n")

    btn = ttk.Button(left, text='Export person CSV', command=export_selected)
    btn.pack(fill='x')

    # Search/filter bindings
    def do_search(evt=None):
        refresh_people_list()

    search_entry.bind('<KeyRelease>', do_search)
    sort_combo.bind('<<ComboboxSelected>>', lambda e: refresh_people_list())
    type_filter_entry.bind('<FocusIn>', lambda e: type_filter_entry.delete(0, 'end'))
    type_filter_entry.bind('<KeyRelease>', lambda e: refresh_people_list())

    root.mainloop()


if __name__ == '__main__':
    run_gui()