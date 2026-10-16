"""Campaign script... (the Events window's bottom bar): campaign_script.txt in its top-level pieces - monitors,
while / if blocks, counters, commands - each with its code; any taken out (one, the picked ones, or all - a mod
made bare for an engine, or its scripts started anew). Kept for Apply by itself (gui_util.AutoKeep) - the main
window's Preview changes / Apply changes / Undo / Redo; the script / end_script frame always stays."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import campaignscript as CS
from .gui_util import AutoKeep, ShortHint, one_window, right_click
from .plan import Plan

TITLE = "Campaign script"


@one_window
class CampaignScriptWindow(AutoKeep, tk.Toplevel):
    _ak_fields = ("removed",)

    def __init__(self, app, campaign):
        super().__init__(app)
        self.app, self.mod, self.campaign = app, app.mod, campaign
        self.path = CS.path_of(self.mod, campaign)
        self.title("%s - %s" % (TITLE, campaign))
        self.geometry("1000x640")
        self.transient(app)
        self.removed = []
        top = ttk.Frame(self, padding=8)
        top.pack(fill="both", expand=True)
        ShortHint(top, foreground="#555", justify="left", wraplength=960, text=(
            "The campaign's own script (%s), piece by piece: what it watches for (monitors), its counters and "
            "commands. Take out what you do not want - the game reads the rest; script / end_script stay." %
            self.mod.rel(self.path))).pack(fill="x")
        body = ttk.Panedwindow(top, orient="horizontal")
        body.pack(fill="both", expand=True, pady=6)
        left = ttk.Frame(body)
        body.add(left, weight=0)
        self.tv = ttk.Treeview(left, columns=("first", "lines"), show="headings", height=18, selectmode="extended")
        self.tv.heading("first", text="piece (its first line)")
        self.tv.heading("lines", text="lines")
        self.tv.column("first", width=380)
        self.tv.column("lines", width=50, anchor="e", stretch=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        bb = ttk.Frame(left)
        bb.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Button(bb, text="Remove all...", command=self.remove_all).pack(side="left")
        ttk.Label(bb, text="right click: remove (Ctrl / Shift + click picks many)", foreground="#666").pack(
            side="left", padx=8)
        right_click(self.tv, self.remove)
        sb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", lambda e: self.show())
        right = ttk.Frame(body)
        body.add(right, weight=1)
        self.code = tk.Text(right, wrap="none", height=20, width=60)
        csb = ttk.Scrollbar(right, orient="vertical", command=self.code.yview)
        self.code.configure(yscrollcommand=csb.set, state="disabled")
        csb.pack(side="right", fill="y")
        self.code.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(top)
        bar.pack(fill="x", pady=(6, 0))
        self.lbl = ttk.Label(bar, text="", foreground="#555")
        self.lbl.pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.reload()
        self.ak_start()

    def reload(self):
        self.f = self.mod.load(self.path)
        self.pieces = CS.read(self.f)
        self.fill()

    def fill(self):
        self.tv.delete(*self.tv.get_children())
        for p in self.pieces:
            if p["id"] not in self.removed:
                self.tv.insert("", "end", iid=p["id"], values=(p["first"], p["lines"]))
        kids = self.tv.get_children()
        if kids:
            self.tv.selection_set(kids[0])
        self.show()
        n = len(self.removed)
        self.lbl.configure(text="%d of %d piece(s) taken out - waiting for Apply changes." % (n, len(self.pieces))
                           if n else "%d piece(s). Nothing changed yet." % len(self.pieces))

    def show(self):
        sel = self.tv.selection()
        p = next((x for x in self.pieces if sel and x["id"] == sel[0]), None)
        self.code.configure(state="normal")
        self.code.delete("1.0", "end")
        if p:
            a, b = p["span"]
            self.code.insert("1.0", "\n".join(self.f.texts()[a:b]))
        self.code.configure(state="disabled")

    def remove(self, ids=None):
        ids = list(self.tv.selection()) if ids is None else ids
        self.removed += [i for i in ids if i not in self.removed]
        if ids:
            self.fill()
            self.ak_changed()

    def remove_all(self):
        ids = [p["id"] for p in self.pieces if p["id"] not in self.removed]
        if ids and messagebox.askyesno(TITLE, "Take out all %d piece(s) of the campaign script? Nothing is written "
                                              "before Apply changes." % len(ids), parent=self):
            self.remove(ids)

    def _plan(self):
        plan = Plan(self.mod, "campaign_script", "campaign_script", {})
        CS.plan_remove(plan, self.path, self.removed)
        return plan

    def _key(self):
        return "campaign_script:%s" % self.campaign

    # ---- kept by itself (gui_util.AutoKeep) ----
    def _ak_key(self):
        return self._key()

    def _ak_label(self):
        return "Campaign script (%s)" % self.campaign

    def _ak_plan(self):
        return self._plan()

    def ak_refresh(self):
        self.fill()

    @property
    def _ak_after(self):
        def after(bdir):
            from . import log
            log.write("Campaign script changed (backup %s)" % bdir)
            if self.winfo_exists():
                self.ak_reload()
        return after

    def ak_reload(self):
        self.mod, self.removed = self.app.mod, []
        self.reload()
        self.ak_start()

    def close(self):
        self.ak_close()
        self.destroy()


def open_campaign_script(app, parent=None):
    campaign = app.v_campaign.get()
    if not app.mod or not CS.path_of(app.mod, campaign):
        messagebox.showinfo(TITLE, "The campaign %s has no campaign_script.txt." % campaign, parent=parent or app)
        return None
    return CampaignScriptWindow(app, campaign)
