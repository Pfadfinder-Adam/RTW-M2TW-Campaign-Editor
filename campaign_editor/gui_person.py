"""A character's own window from the Map (right click a general, a family man, the heir, the king, an agent >
'Edit this character...', or a double click on an agent): Characters in a window of its own, as the town's
garrison and buildings have theirs - the person picked; a change waits for Apply changes by itself (gui_util.AutoKeep -
the main window's Preview changes / Apply changes / Undo / Redo, a backup first; the writing is the Characters's own:
gui_family.FamilyEditor.make_plan)."""

import tkinter as tk
from tkinter import ttk

from .gui_util import AutoKeep
from .gui_family import FamilyEditor

TITLE = "Character"


class _Editor(FamilyEditor):
    """Characters inside the window: its changes are written by the window's own button."""

    def changed(self):
        self.app.status.set("Character window: changes waiting for Apply changes.")
        self.redraw()
        self.master.ak_changed()


class PersonWindow(AutoKeep, tk.Toplevel):
    def __init__(self, app, ch):
        super().__init__(app)
        self.app = app
        self.transient(app)
        self.geometry("1100x%d" % max(560, min(860, self.winfo_screenheight() - 110)))
        self.minsize(760, 520)
        self.protocol("WM_DELETE_WINDOW", self.close)
        bar = ttk.Frame(self, padding=(10, 4, 10, 6))
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self.ch = None
        self.ed = _Editor(self, app, standalone=True)
        self.ed.pack(fill="both", expand=True)
        self.show(ch)

    def show(self, ch):
        """Pick this character (a dict of the Map's: name, faction, from) - his faction's people, him chosen. Another
        faction's man: what waits for the one shown is kept first, then his faction's picks come back if they wait."""
        if self.ch is not None and self.ch["faction"] != ch["faction"]:
            self.ak_close()
            self.ed.states, self.ed.lib_adds = {}, []
        self._ak_busy = True
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
        self.ak_start()
        return p is not None

    # ---- kept by itself (gui_util.AutoKeep) ----
    def _ak_key(self):
        return "person:%s" % self.ch["faction"] if self.ch else None

    def _ak_label(self):
        return "Characters of %s (%s)" % (self.ch["faction"], self.ch["name"])

    def _ak_plan(self):
        return self.ed.make_plan()

    def _ak_state(self):
        import pickle
        return pickle.dumps((self.ed.states, self.ed.lib_adds), protocol=4)

    def _ak_set(self, st):
        import pickle
        self.ed.states, self.ed.lib_adds = pickle.loads(st)
        self.ed.redraw()

    @property
    def _ak_after(self):
        ch = dict(self.ch)

        def after(bdir):
            from . import log
            log.write("Character %s (%s) changed (backup %s)" % (ch["name"], ch["faction"], bdir))
            if self.winfo_exists():
                self.ak_reload()
        return after

    def ak_reload(self):
        self.ed.states, self.ed.lib_adds = {}, []
        self.show(self.ch)

    def close(self):
        self.ak_close()
        self._forget()
        self.destroy()

    def _forget(self):
        if getattr(self.app, "_person_window", None) is self:
            self.app._person_window = None


def open_person_window(app, ch):
    """One character window: another character opens in the same window."""
    if not app.mod or not ch.get("from"):
        return None
    w = getattr(app, "_person_window", None)
    if w is not None and w.winfo_exists():
        w.show(ch)                                     # what waits for the one shown before stays kept
        w.deiconify()
        w.lift()
        return w
    app._person_window = PersonWindow(app, ch)
    return app._person_window
