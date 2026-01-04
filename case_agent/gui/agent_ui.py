"""Agent GUI (headless-friendly) implementation for tests and the desktop app."""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ..agent.client import AgentClient


class CaseAgentGUI(tk.Tk):
    def __init__(
        self, db_path=None, api_url: str | None = None, headless: bool = False
    ):
        """Create the GUI.

        - `api_url` if provided will make the GUI use the remote HTTP API instead of a local agent.
        - `headless` avoids creating Tk widgets (useful for running tests in CI).
        """
        self.db_path = db_path
        self.api_url = api_url
        self.headless = headless

        if not self.headless:
            super().__init__()
            self.title("Case Agent")
            self.geometry("700x500")

        # use AgentClient to abstract local vs remote agent
        self.client = AgentClient(db_path=db_path, api_url=api_url)
        # local agent (if any) kept for backward compatibility
        self.agent = getattr(self.client, "_local_agent", None)

        if not self.headless:
            self.create_widgets()
        else:
            # minimal output stub for headless test use
            class _OutStub:
                def __init__(self):
                    self.buf = []

                def insert(self, *args, **kwargs):
                    # mimic Text.insert(index, text)
                    if len(args) >= 2:
                        self.buf.append(args[1])

                def getvalue(self):
                    return "".join(self.buf)

            class _VarStub:
                def __init__(self, init=""):
                    self._v = init

                def set(self, v):
                    self._v = v

                def get(self):
                    return self._v

            # simple query var substitute for headless mode
            self.query_var = _VarStub()
            self.output = _OutStub()

    def create_widgets(self):
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)

        self.actions_menu = tk.Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="Actions", menu=self.actions_menu)
        self.actions_menu.add_command(label="Run Inventory", command=self.run_inventory)
        self.actions_menu.add_command(
            label="Extract Text (all PDFs)", command=self.reprocess_pdfs
        )
        self.actions_menu.add_command(
            label="Extract Entities (all files)", command=self.run_entities
        )
        self.actions_menu.add_command(label="Build Timeline", command=self.run_timeline)
        self.actions_menu.add_command(
            label="Run Full Synopsis", command=self.run_synopsis
        )
        self.actions_menu.add_command(
            label="People Mention Report", command=self.show_people_report
        )

        # Quick agent query bar
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=4, pady=4)
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(top_frame, textvariable=self.query_var)
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.query_btn = ttk.Button(top_frame, text="Ask Agent", command=self.ask_agent)
        self.query_btn.pack(side="left")

        self.output = tk.Text(self)
        self.output.pack(fill="both", expand=True)

    def run_in_thread(self, fn, *args, **kwargs):
        t = threading.Thread(
            target=lambda: self._run_and_log(fn, *args, **kwargs), daemon=True
        )
        t.start()

    def _run_and_log(self, fn, *args, **kwargs):
        try:
            self.output.insert("end", f"Running: {fn.__name__}\n")
            res = fn(*args, **kwargs)
            self.output.insert("end", f"Done: {fn.__name__} -> {res}\n")
        except Exception as e:
            self.output.insert("end", f"Error: {e}\n")

    def run_inventory(self):
        # Ask user for evidence dir
        evidence = Path.cwd() / "evidence"
        self.run_in_thread(lambda: None, evidence, None)

    def reprocess_pdfs(self):
        self.run_in_thread(lambda: None, self.db_path)

    def run_entities(self):
        # naive: run entity extraction for all files listed in DB
        messagebox.showinfo(
            "Not implemented", "Entity batch runner will be added in next iteration"
        )

    def run_timeline(self):
        self.run_in_thread(lambda: None, None)

    def run_synopsis(self):
        def do():
            res = self.agent.full_synopsis()
            self.output.insert(
                "end", f"Synopsis source: {res.get('source')}\n{res.get('summary')}\n"
            )

        threading.Thread(target=do, daemon=True).start()

    def ask_agent(self):
        q = self.query_var.get().strip()
        if not q:
            if not self.headless:
                messagebox.showinfo("No query", "Please type a query")
            return

        def do():
            try:
                res = self.client.answer_query(q)
            except Exception as e:
                self.output.insert("end", f"Agent error: {e}\n")
                return
            if "message" in res:
                self.output.insert("end", f"Agent: {res.get('message')}\n")
            else:
                self.output.insert("end", f"Agent summary: {res.get('summary')}\n")
                for f in res.get("facts", []):
                    self.output.insert(
                        "end",
                        f"- {f.get('text')[:200]} (confidence: {f.get('confidence')})\n",
                    )

        threading.Thread(target=do, daemon=True).start()

    def show_people_report(self):
        def do():
            try:
                rpt = self.client.people_report()
            except Exception as e:
                if self.headless:
                    self.output.insert("end", f"People report error: {e}\n")
                    return
                messagebox.showerror("Error", str(e))
                return

            people = rpt.get("people", [])

            # In headless mode simply write results to the output stub for tests
            if self.headless:
                for p in people[:200]:
                    self.output.insert(
                        "end", f"{p.get('person')} — {p.get('file_count')} files\n"
                    )
                return

            # show in a simple Toplevel with a listbox
            top = tk.Toplevel(self)
            top.title("People Mention Report")
            lb = tk.Listbox(top, width=80, height=25)
            lb.pack(side="left", fill="both", expand=True)
            for p in people[:200]:
                lb.insert("end", f"{p.get('person')} — {p.get('file_count')} files")
            frm = ttk.Frame(top)
            frm.pack(side="right", fill="y")

            def _export():
                from tkinter import filedialog

                path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv")],
                )
                if not path:
                    return
                import csv
                import json

                if path.endswith(".json"):
                    with open(path, "w", encoding="utf-8") as fh:
                        json.dump({"people": people}, fh, indent=2)
                else:
                    with open(path, "w", newline="", encoding="utf-8") as fh:
                        w = csv.writer(fh)
                        w.writerow(["person", "file_count", "files"])
                        for p in people:
                            w.writerow(
                                [
                                    p.get("person"),
                                    p.get("file_count"),
                                    ";".join(p.get("files", [])),
                                ]
                            )
                messagebox.showinfo("Export complete", f"Wrote report to {path}")

            b = ttk.Button(frm, text="Export", command=_export)
            b.pack(padx=4, pady=4)
