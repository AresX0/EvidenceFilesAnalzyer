"""Simple Tkinter GUI for running pipelines and the agent synopsis.

This is a minimal, local-only interface intended as a starting point.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from .pipelines.hash_inventory import walk_and_hash
from .pipelines.text_extract import extract_for_file, reprocess_pdfs_without_text
from .pipelines.entity_extract import extract_entities_for_file
from .pipelines.media_extract import process_media
from .pipelines.timeline_builder import build_timeline
from .agent.agent import CaseAgent

class CaseAgentGUI(tk.Tk):
    def __init__(self, db_path=None):
        super().__init__()
        self.title('Case Agent')
        self.geometry('700x500')
        self.db_path = db_path
        self.agent = CaseAgent(db_path=db_path)

        self.create_widgets()

    def create_widgets(self):
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)

        self.actions_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label='Actions', menu=self.actions_menu)
        self.actions_menu.add_command(label='Run Inventory', command=self.run_inventory)
        self.actions_menu.add_command(label='Extract Text (all PDFs)', command=self.reprocess_pdfs)
        self.actions_menu.add_command(label='Extract Entities (all files)', command=self.run_entities)
        self.actions_menu.add_command(label='Build Timeline', command=self.run_timeline)
        self.actions_menu.add_command(label='Run Full Synopsis', command=self.run_synopsis)

        self.output = tk.Text(self)
        self.output.pack(fill='both', expand=True)

    def run_in_thread(self, fn, *args, **kwargs):
        t = threading.Thread(target=lambda: self._run_and_log(fn, *args, **kwargs), daemon=True)
        t.start()

    def _run_and_log(self, fn, *args, **kwargs):
        try:
            self.output.insert('end', f'Running: {fn.__name__}\n')
            res = fn(*args, **kwargs)
            self.output.insert('end', f'Done: {fn.__name__} -> {res}\n')
        except Exception as e:
            self.output.insert('end', f'Error: {e}\n')

    def run_inventory(self):
        # Ask user for evidence dir
        evidence = Path.cwd() / 'evidence'
        self.run_in_thread(walk_and_hash, evidence, None)

    def reprocess_pdfs(self):
        self.run_in_thread(reprocess_pdfs_without_text, self.db_path)

    def run_entities(self):
        # naive: run entity extraction for all files listed in DB
        session = self.agent.session
        for f in session.query(walk_and_hash.__module__ and None):
            pass
        messagebox.showinfo('Not implemented', 'Entity batch runner will be added in next iteration')

    def run_timeline(self):
        self.run_in_thread(build_timeline, None)

    def run_synopsis(self):
        def do():
            res = self.agent.full_synopsis()
            self.output.insert('end', f"Synopsis source: {res.get('source')}\n{res.get('summary')}\n")
        threading.Thread(target=do, daemon=True).start()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=None)
    args = parser.parse_args()
    app = CaseAgentGUI(db_path=args.db)
    app.mainloop()

if __name__ == '__main__':
    main()
