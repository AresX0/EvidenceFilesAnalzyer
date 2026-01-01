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

    # Menu: File -> Settings
    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=0)
    def open_settings():
        try:
            s = tk.Toplevel(root)
            s.title('Settings')
            s.geometry('480x160')
            ttk.Label(s, text='PDF Viewer Path (optional)').pack(anchor='w', padx=8, pady=(8,0))
            pdf_var = tk.StringVar()
            try:
                import case_agent.config as cfg
                pdf_var.set(str(getattr(cfg, 'PDF_VIEWER', '') or ''))
            except Exception:
                pdf_var.set('')
            pdf_entry = ttk.Entry(s, textvariable=pdf_var)
            pdf_entry.pack(fill='x', padx=8, pady=4)
            # Show top subjects option
            subjects_var = tk.BooleanVar(value=True)
            try:
                import case_agent.config as cfg
                subjects_var.set(bool(getattr(cfg, 'SHOW_TOP_SUBJECTS', True)))
            except Exception:
                subjects_var.set(True)
            ttk.Checkbutton(s, text='Show top subjects panel', variable=subjects_var).pack(anchor='w', padx=8, pady=(4,4))
            btn_frame = ttk.Frame(s)
            btn_frame.pack(fill='x', padx=8, pady=8)
            def autodetect():
                from case_agent.utils.viewers import detect_pdf_viewer
                v = detect_pdf_viewer()
                if v:
                    pdf_var.set(str(v))
            ttk.Button(btn_frame, text='Autodetect', command=autodetect).pack(side='left')
            def save_settings():
                try:
                    import case_agent.config as cfg
                    cfg.PDF_VIEWER = pdf_var.get() or None
                    cfg.SHOW_TOP_SUBJECTS = bool(subjects_var.get())
                    cfg.save_user_config()
                    s.destroy()
                except Exception:
                    s.destroy()
            ttk.Button(btn_frame, text='Save', command=save_settings).pack(side='right')
        except Exception as e:
            print('Settings dialog failed', e)
    file_menu.add_command(label='Settings...', command=open_settings)
    file_menu.add_separator()
    file_menu.add_command(label='Quit', command=root.quit)
    menubar.add_cascade(label='File', menu=file_menu)
    root.config(menu=menubar)

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

    # Notebook with tabs for All / Images / Documents
    notebook = ttk.Notebook(left)
    tab_all = ttk.Frame(notebook)
    tab_images = ttk.Frame(notebook)
    tab_docs = ttk.Frame(notebook)
    notebook.add(tab_all, text='All')
    notebook.add(tab_images, text='Images')
    notebook.add(tab_docs, text='Documents')
    notebook.pack(fill='both', expand=True)

    lb_all = tk.Listbox(tab_all)
    lb_all.pack(fill='both', expand=True)
    lb_images = tk.Listbox(tab_images)
    lb_images.pack(fill='both', expand=True)
    lb_docs = tk.Listbox(tab_docs)
    lb_docs.pack(fill='both', expand=True)

    # Keep a working list of people that matches current filters
    _filtered_people = list(people)
    _filtered_images = []
    _filtered_docs = []

    def _person_has_ext(person, ext_set):
        for f in person.get('files', []):
            if Path(f).suffix.lower() in ext_set:
                return True
        return False

    def refresh_people_list():
        q = search_var.get().lower()
        ft = type_filter_var.get().strip().lower()
        sort = sort_var.get()
        # filter
        out = []
        out_images = []
        out_docs = []
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp'}
        doc_exts = {'.pdf', '.txt', '.docx', '.doc'}
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
            if _person_has_ext(p, image_exts):
                out_images.append(p)
            if _person_has_ext(p, doc_exts):
                out_docs.append(p)
        # sort
        if sort == 'Files (desc)':
            out.sort(key=lambda x: x.get('file_count', 0), reverse=True)
            out_images.sort(key=lambda x: x.get('file_count', 0), reverse=True)
            out_docs.sort(key=lambda x: x.get('file_count', 0), reverse=True)
        else:
            out.sort(key=lambda x: x.get('person', '').lower())
            out_images.sort(key=lambda x: x.get('person', '').lower())
            out_docs.sort(key=lambda x: x.get('person', '').lower())
        # update listboxes
        lb_all.delete(0, 'end')
        lb_images.delete(0, 'end')
        lb_docs.delete(0, 'end')
        for p in out:
            lb_all.insert('end', f"{p.get('person')} ({p.get('file_count')})")
        for p in out_images:
            lb_images.insert('end', f"{p.get('person')} ({p.get('file_count')})")
        for p in out_docs:
            lb_docs.insert('end', f"{p.get('person')} ({p.get('file_count')})")
        # store filtered
        nonlocal _filtered_people, _filtered_images, _filtered_docs
        _filtered_people = out
        _filtered_images = out_images
        _filtered_docs = out_docs

    # Debounce logic for search to improve performance
    _search_after_id = None
    def do_search_debounced(evt=None):
        nonlocal _search_after_id
        if _search_after_id:
            root.after_cancel(_search_after_id)
        _search_after_id = root.after(200, refresh_people_list)

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

    # Top subjects panel (configurable)
    # will be populated from report's 'top_subjects' or from face_matches list
    top_subjects_frame = ttk.Frame(top_frame)
    top_subjects_frame.pack(side='left', padx=(10,0))
    top_subjects_label = ttk.Label(top_subjects_frame, text='Top subjects:')
    top_subjects_label.pack(anchor='w')
    top_subjects_list = tk.Listbox(top_subjects_frame, height=6)
    top_subjects_list.pack(fill='y')
    # Expose for tests
    root.top_subjects_frame = top_subjects_frame

    # Documents list for selected person (double-click to open)
    docs_label = ttk.Label(top_frame, text='Documents')
    docs_label.pack(side='left', padx=(10,0))
    docs_lb = tk.Listbox(top_frame, height=6)
    docs_lb.pack(side='left', fill='y')

    # Alfred chat / voice input frame
    chat_frame = ttk.Frame(right)
    chat_frame.pack(fill='x')
    chat_label = ttk.Label(chat_frame, text='Alfred:')
    chat_label.pack(side='left')
    chat_entry = ttk.Entry(chat_frame)
    chat_entry.pack(side='left', fill='x', expand=True, padx=(4,4))
    chat_btn = ttk.Button(chat_frame, text='Ask', command=lambda: handle_alfred_query(chat_entry.get()))
    chat_btn.pack(side='left')
    mic_btn = ttk.Button(chat_frame, text='Mic', state='disabled')
    mic_btn.pack(side='left', padx=(4,0))

    # Try to enable mic button if speech_recognition available and microphone present
    try:
        import case_agent.config as cfg
        SHOW_TOP = bool(getattr(cfg, 'SHOW_TOP_SUBJECTS', True))
    except Exception:
        SHOW_TOP = True

    try:
        import speech_recognition as sr
        # naive check for mic devices
        r = sr.Recognizer()
        mics = sr.Microphone.list_microphone_names()
        if mics:
            mic_btn.config(state='normal')
            def on_mic_click():
                # run recognition in background
                def _listen():
                    with sr.Microphone() as source:
                        r.adjust_for_ambient_noise(source)
                        audio = r.listen(source, timeout=5)
                        try:
                            txt = r.recognize_sphinx(audio)
                        except Exception:
                            try:
                                txt = r.recognize_google(audio)
                            except Exception:
                                txt = ''
                        if txt:
                            chat_entry.delete(0, 'end')
                            chat_entry.insert(0, txt)
                            handle_alfred_query(txt)
                import threading
                threading.Thread(target=_listen, daemon=True).start()
            mic_btn.config(command=on_mic_click)
    except Exception:
        pass

    # populate top subjects list from report if enabled
    def _load_top_subjects():
        top_subjects_list.delete(0, 'end')
        try:
            # prefer precomputed top_subjects
            ts = rpt.get('top_subjects') or []
            if not ts and rpt.get('face_matches'):
                from collections import Counter
                subj_counts = Counter([r.get('subject') for r in rpt.get('face_matches', []) if r.get('subject')])
                ts = [{'subject': s, 'count': c} for s, c in subj_counts.most_common(20)]
            for s in ts[:20]:
                top_subjects_list.insert('end', f"{s.get('subject')} ({s.get('count')})")
        except Exception:
            pass

    if SHOW_TOP:
        _load_top_subjects()
    else:
        top_subjects_frame.pack_forget()
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

    # Virtualized thumbnails: render only items in visible region
    class VirtualThumbGrid:
        def __init__(self, canvas, container, cols=4, thumb_size=(160,120), gap=(4,4)):
            self.canvas = canvas
            self.container = container
            self.cols = cols
            self.thumb_w, self.thumb_h = thumb_size
            self.gx, self.gy = gap
            self.rendered = {}  # idx -> widget
            self.files = []
            self.person = None
            self.batch_size = 40
            # executor for background thumbnail generation
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=4)
            self._futures = {}  # idx -> future
            # debounce handle for scroll events
            self._scheduled_id = None
            # throttle small initial batch to make UI responsive
            self._initial_load = True

        def set_person(self, person):
            # reset state
            self.person = person
            self.files = person.get('files', []) if person else []
            # clear existing widgets
            for w in list(self.rendered.values()):
                try:
                    w.destroy()
                except Exception:
                    pass
            self.rendered.clear()
            # cancel outstanding futures
            for f in list(self._futures.values()):
                try:
                    f.cancel()
                except Exception:
                    pass
            self._futures.clear()
            self.container.update_idletasks()
            self._layout_placeholder()
            self._on_scroll()

        def _layout_placeholder(self):
            # set container grid rows to match count so scrollregion computed
            n = len(self.files)
            rows = (n + self.cols - 1) // self.cols
            self.container.update_idletasks()
            self.canvas.configure(scrollregion=(0,0, self.cols*(self.thumb_w+self.gx), rows*(self.thumb_h+self.gy)))

        def _visible_range(self):
            y0, y1 = self.canvas.yview()
            bbox = self.canvas.bbox('all') or (0,0,0,0)
            total_h = bbox[3] - bbox[1] if bbox else 0
            if total_h == 0:
                return 0, -1
            vy0 = int(y0 * total_h)
            vy1 = int(y1 * total_h)
            row0 = max(0, vy0 // (self.thumb_h + self.gy) - 1)
            row1 = (vy1 // (self.thumb_h + self.gy)) + 1
            start = row0 * self.cols
            end = min(len(self.files), (row1+1) * self.cols)
            return start, end

        def _on_scroll(self, evt=None):
            # debounce rapid scroll events to avoid excessive work
            try:
                if self._scheduled_id:
                    root.after_cancel(self._scheduled_id)
            except Exception:
                pass
            self._scheduled_id = root.after(100, self._do_on_scroll)

        def _do_on_scroll(self):
            self._scheduled_id = None
            start, end = self._visible_range()
            # remove widgets outside range
            for idx in list(self.rendered.keys()):
                if idx < start or idx >= end:
                    try:
                        self.rendered[idx].destroy()
                    except Exception:
                        pass
                    del self.rendered[idx]
            # render missing widgets
            for idx in range(start, end):
                if idx in self.rendered:
                    continue
                fpath = self.files[idx]
                # create placeholder
                from PIL import Image, ImageTk
                placeholder = Image.new('RGB', (self.thumb_w, self.thumb_h), color=(240,240,240))
                ph_img = ImageTk.PhotoImage(placeholder)
                lbl = ttk.Label(self.container, image=ph_img, text='Loading...', compound='center')
                lbl.image = ph_img
                r = idx // self.cols
                c = idx % self.cols
                lbl.grid(row=r, column=c, padx=self.gx, pady=self.gy)
                self.rendered[idx] = lbl
                # schedule background render
                if idx not in self._futures:
                    fut = self._executor.submit(self._render_thumb, idx, fpath)
                    # schedule main-thread UI update on completion
                    fut.add_done_callback(lambda fut, ix=idx, s=self: root.after(0, lambda: s._apply_rendered(ix, fut.result())))
                    self._futures[idx] = fut
            # update scrollregion just in case
            self.container.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        def _render_thumb(self, idx, fpath):
            # runs in worker thread: prepare PIL.Image
            try:
                from case_agent.utils.thumbs import thumbnail_for_image
                from case_agent.utils.image_overlay import overlay_matches_on_pil
                from PIL import Image
                thumb_path = thumbnail_for_image(fpath, Path(r"C:/Projects/FileAnalyzer/reports"), size=(self.thumb_w, self.thumb_h))
                img = Image.open(thumb_path).convert('RGB')
                # overlay small match marker
                try:
                    import sqlite3, json
                    conn = sqlite3.connect(r'C:/Projects/FileAnalyzer/file_analyzer.db')
                    cur = conn.cursor()
                    cur.execute("SELECT subject, probe_bbox FROM face_matches WHERE source=?", (fpath,))
                    rows = cur.fetchall()
                    conn.close()
                    matches = []
                    for r in rows:
                        subj, pb = r[0], r[1]
                        try:
                            pbj = json.loads(pb) if pb else None
                        except Exception:
                            pbj = None
                        matches.append({'subject': subj, 'probe_bbox': pbj})
                    if matches:
                        img = overlay_matches_on_pil(img, matches, size=img.size)
                except Exception:
                    pass
                return img
            except Exception:
                from PIL import Image
                return Image.new('RGB', (self.thumb_w, self.thumb_h), color=(220,220,220))

        def _apply_rendered(self, idx, pil_img):
            # must run in main thread to create PhotoImage
            try:
                from PIL import ImageTk
                if idx not in self.rendered:
                    return
                tkimg = ImageTk.PhotoImage(pil_img)
                lbl = self.rendered[idx]
                lbl.config(image=tkimg)
                lbl.image = tkimg
            except Exception:
                pass

        def shutdown(self):
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass

    # install virtualization handler
    _virtual_grid = VirtualThumbGrid(canvas, thumbs_container, cols=4, thumb_size=(160,120))
    canvas.bind('<Configure>', lambda e: _virtual_grid._on_scroll())
    canvas.bind_all('<MouseWheel>', lambda e: (canvas.yview_scroll(int(-1*(e.delta/120)), 'units'), _virtual_grid._on_scroll()))
    def show_thumbnails_for_person(person):
        _virtual_grid.set_person(person)


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

    def on_select_from_list(listbox, list_source):
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(list_source):
            return
        person = list_source[idx]
        text.delete('1.0', 'end')
        text.insert('end', f"Person: {person.get('person')}\nFiles ({person.get('file_count')}):\n")
        # Populate document listbox
        docs_lb.delete(0, 'end')
        image_files = []
        doc_files = []
        for f in person.get('files', []):
            if Path(f).suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp'}:
                image_files.append(f)
            else:
                doc_files.append(f)
            text.insert('end', f" - {f}\n")
        update_matches_for_person(person)
        show_thumbnails_for_person({'files': image_files, 'person': person.get('person'), 'file_count': len(image_files)})
        for d in doc_files:
            docs_lb.insert('end', d)

    # wire existing matches and docs events
    matches_lb.bind('<<ListboxSelect>>', show_gallery_for_selected_match)
    docs_lb.bind('<Double-1>', lambda e: __import__('os').startfile(docs_lb.get(docs_lb.curselection()[0])) if docs_lb.curselection() else None)

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

    # Small helper to call Alfred query backend and show results
    def handle_alfred_query(q: str):
        if not q:
            return
        from case_agent.agent.alfred import parse_query, list_files_for_person
        parsed = parse_query(q)
        if parsed.get('action') != 'list':
            text.insert('end', f"Alfred: I don't understand that query. Try 'list images of NAME'\n")
            return
        typ = parsed.get('type', 'images')
        if typ in {'pictures'}:
            typ = 'images'
        person = parsed.get('person')
        results = list_files_for_person(r'C:/Projects/FileAnalyzer/file_analyzer.db', person, typ=('images' if typ=='images' else 'documents' if typ=='documents' else 'all'))
        if not results:
            text.insert('end', f"Alfred: no {typ} found for {person}\n")
            return
        text.insert('end', f"Alfred: Found {len(results)} {typ} for {person}:\n")
        for r in results:
            text.insert('end', f" - {r}\n")
        # show thumbnails of first few results
        show_thumbnails_for_person({'files': results, 'person': person, 'file_count': len(results)}, batch=0)


    # Search/filter bindings
    # bind debounced search
    search_entry.bind('<KeyRelease>', do_search_debounced)
    sort_combo.bind('<<ComboboxSelected>>', lambda e: refresh_people_list())
    type_filter_entry.bind('<FocusIn>', lambda e: type_filter_entry.delete(0, 'end'))
    type_filter_entry.bind('<KeyRelease>', lambda e: refresh_people_list())

    # wire listbox selection handlers for all tabs
    def _bind_listboxes():
        lb_all.bind('<<ListboxSelect>>', lambda e: on_select_from_list(lb_all, _filtered_people))
        lb_images.bind('<<ListboxSelect>>', lambda e: on_select_from_list(lb_images, _filtered_images))
        lb_docs.bind('<<ListboxSelect>>', lambda e: on_select_from_list(lb_docs, _filtered_docs))
    _bind_listboxes()

    # keyboard shortcuts
    def focus_search(evt=None):
        search_entry.focus_set()
        return 'break'

    def next_person(evt=None):
        try:
            lb_all.select_clear(0, 'end')
            cur = lb_all.curselection()
            idx = cur[0] if cur else -1
            idx = min(idx+1, lb_all.size()-1)
            lb_all.select_set(idx)
            lb_all.event_generate('<<ListboxSelect>>')
        except Exception:
            pass
        return 'break'

    def prev_person(evt=None):
        try:
            lb_all.select_clear(0, 'end')
            cur = lb_all.curselection()
            idx = cur[0] if cur else lb_all.size()
            idx = max(idx-1, 0)
            lb_all.select_set(idx)
            lb_all.event_generate('<<ListboxSelect>>')
        except Exception:
            pass
        return 'break'

    def focus_alfred(evt=None):
        chat_entry.focus_set()
        return 'break'

    root.bind('<Control-f>', focus_search)
    root.bind('<n>', next_person)
    root.bind('<p>', prev_person)
    root.bind('<Control-l>', focus_alfred)
    root.mainloop()


if __name__ == '__main__':
    run_gui()