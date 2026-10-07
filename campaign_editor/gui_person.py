"""A character's own window from the Map (right click a general, a family man, the heir, the king, an agent >
'Edit this character...', or a double click on an agent): the Character editor in a window of its own, as the town's
garrison and buildings have theirs - the person picked, Preview / Write it in with a backup (the writing is the
Character editor's own: gui_family.FamilyEditor.make_plan)."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_family import FamilyEditor

TITLE = "Character"


class _Editor(FamilyEditor):
    """The Character editor inside the window: its changes are written by the window's own button."""

    def changed(self):
        self.app.status.set("Character window: changes waiting - Preview, then Write it in.")
        self.redraw()


class PersonWindow(tk.Toplevel):
    def __init__(self, app, ch):
        super().__init__(app)
        self.app = app
        self.transient(app)
        self.geometry("1100x%d" % max(560, min(860, self.winfo_screenheight() - 110)))
        self.minsize(760, 520)
        from .gui_util import close_guard               # never closes over unwritten changes silently
        self.close = close_guard(self, TITLE, lambda: self.ed.dirty(), lambda: self.write(), after=self._forget)
        bar = ttk.Frame(self, padding=(10, 4, 10, 6))
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.ed = _Editor(self, app, standalone=True)
        self.ed.pack(fill="both", expand=True)
        self.show(ch)

    def show(self, ch):
        """Pick this character (a dict of the Map's: name, faction, from) - his faction's people, him chosen."""
        self.ch = ch
        self.title("%s - %s of %s" % (TITLE, ch["name"], ch["faction"]))
        self.ed.rebind(self.app.mod)
        self.ed.v_fac.set(ch["faction"])
        self.ed.load()
        people = self.ed.people()
        p = next((q for q in people if q["name"] == ch["name"] and q.get("xy") and ch.get("from")
                  and tuple(q["xy"]) == tuple(ch["from"])), None) or \
            next((q for q in people if q["name"] == ch["name"]), None)
        if p is not None:
            self.ed.pick(p["key"])
        return p is not None

    def _plan(self):
        if not self.ed.dirty():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return None
        try:
            return self.ed.make_plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return None

    def preview(self):
        plan = self._plan()
        if plan:
            self.app.show_text("%s - preview (nothing written)" % self.ch["name"], plan.report())

    def write(self):
        plan = self._plan()
        if not plan:
            return
        waiting = self.app.pending_parts()
        if waiting:
            messagebox.showerror(TITLE, "Not written yet. The main window holds changes not applied:\n\n%s\n\nApply "
                                        "them (Apply changes) or Undo them first: this write reads the mod again "
                                        "afterwards, and they would be lost."
                                 % "\n".join("- " + label for _, label in waiting), parent=self)
            return
        if not messagebox.askyesno(TITLE, "%s\n\nWrite it? A backup is made first (Tools > Restore undoes it)."
                                   % plan.report()[:1500], parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Character %s (%s) changed (backup %s)\n%s" % (self.ch["name"], self.ch["faction"], bdir,
                                                                 plan.report()))
        self.ed.states, self.ed.lib_adds = {}, []
        self.app.load()
        self.app.status.set("%s written (backup %s)." % (self.ch["name"], bdir))
        self.show(self.ch)

    def _forget(self):
        if getattr(self.app, "_person_window", None) is self:
            self.app._person_window = None


def open_person_window(app, ch):
    """One character window: another character opens in the same window."""
    if not app.mod or not ch.get("from"):
        return None
    w = getattr(app, "_person_window", None)
    if w is not None and w.winfo_exists():
        if w.ed.dirty() and not messagebox.askyesno(TITLE, "Show %s instead? The changes made to %s are not "
                                                           "written yet and go." % (ch["name"], w.ch["name"]),
                                                    parent=w):
            return w
        w.ed.states, w.ed.lib_adds = {}, []
        w.show(ch)
        w.deiconify()
        w.lift()
        return w
    app._person_window = PersonWindow(app, ch)
    return app._person_window
