"""Maps > 3D > 'Game's editor...': the campaign opened in the game's own campaign-map editor, and what it saved taken
back (gameeditor.py says how). One window: Open in the game's editor, Take the changes back, Remove the copy."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import gameeditor as GE
from . import theme
from .gui_util import ask, one_window, window_body

TITLE = "The game's campaign editor"
ABOUT = ("The game has a campaign-map editor of its own: it draws the map the way the game does. It opens only "
         "campaigns in campaign/custom/, so 'Open in the game's editor' copies this campaign there and starts the "
         "game in it. Edit, Save there, close the game - then 'Take the changes back' brings what it saved into "
         "your campaign. On Save it drops the 'script' line and anything it cannot read: the script lines are put "
         "back and what it dropped is listed. Every write makes a backup (Restore puts it back). Not tried in the "
         "game yet - please send a report after the first try.")


@one_window
class GameEditorWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(TITLE)
        frm, bar = window_body(self, 640, 460)
        ttk.Label(frm, text=ABOUT, wraplength=600, justify="left").pack(anchor="w")
        self.l_line = ttk.Label(frm, wraplength=600, justify="left", foreground=theme.palette()["muted"])
        self.l_line.pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(frm)
        row.pack(anchor="w", pady=(8, 0))
        self.b_open = ttk.Button(row, text="Open in the game's editor", command=self.open_it)
        self.b_open.pack(side="left")
        self.b_back = ttk.Button(row, text="Take the changes back", command=self.take_back)
        self.b_back.pack(side="left", padx=(theme.BUTTON_GAP, 0))
        self.b_drop = ttk.Button(row, text="Remove the copy", command=self.remove_copy)
        self.b_drop.pack(side="left", padx=(theme.BUTTON_GAP, 0))
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True, pady=(8, 0))
        self.txt = tk.Text(box, height=10, wrap="word")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        self.show()

    def _camp(self):
        return self.app.v_campaign.get()

    def _say(self, text):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.txt.configure(state="disabled")

    def show(self):
        mod, camp = self.app.mod, self._camp()
        if mod is None or not camp:
            self.l_line.configure(text="Load a mod first.")
            for b in (self.b_open, self.b_back, self.b_drop):
                b.state(["disabled"])
            return
        try:
            line = GE.start_line(mod.data, camp)
            started = "It starts: %s%s" % (line["words"], "\n" + line["how"] if line["how"] else "")
        except ValueError as e:
            started = "The game cannot be started from here: %s" % e
        self.l_line.configure(text="Campaign %s -> %s\n%s" % (camp, mod.rel(GE.custom_dir(mod, camp)), started))
        note = GE.read_note(mod, camp)
        self.b_open.state(["!disabled"])
        for b in (self.b_back, self.b_drop):
            b.state(["!disabled"] if note else ["disabled"])
        if not note:
            self._say("Not opened in the game's editor yet.")
            return
        got = GE.changed(mod, camp)
        self._say("The copy is in place.\n" + (
            "Saved and changed by the game's editor:\n  " + "\n  ".join(n for n, _, _ in got) if got else
            "Nothing saved by the game's editor yet (Save there, close the game, then look here again)."))

    def open_it(self):
        from . import log
        from .launch import start
        from .plan import Plan
        mod, camp = self.app.mod, self._camp()
        if mod is None:
            return
        if GE.read_note(mod, camp) and GE.changed(mod, camp) and not ask(
                TITLE, "The game's editor saved changes there that were not taken back. Copy the campaign again "
                "over them?", parent=self, yes="Copy again", no="Keep them"):
            return
        plan = Plan(mod, "game_editor", "game_editor", {})
        try:
            GE.prepare(plan, camp)
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror(TITLE, "Not copied: %s" % e, parent=self)
            return
        log.write("The campaign %s copied for the game's editor (backup %s)\n%s" % (camp, bdir, plan.report()))
        try:
            line = GE.start_line(mod.data, camp)
            start(line)
        except (ValueError, OSError) as e:
            messagebox.showinfo(TITLE, "Copied. %s" % e, parent=self)
            self.show()
            return
        log.write("The game started %s: %s" % ("in its campaign editor" if line["direct"] else
                                                "(the switch may not be known - see the message)", line["words"]))
        if not line["direct"]:
            messagebox.showinfo(TITLE, line["how"], parent=self)
        self.app.status.set("The game is starting%s - Save there, close the game, then 'Take the changes back' "
                            "(Maps > 3D > Game's editor...)." % (
                                " in its campaign editor" if line["direct"] else
                                " - if it opens at the main menu, see the message"))
        self.show()

    def take_back(self):
        from . import log
        from .plan import Plan
        mod, camp = self.app.mod, self._camp()
        if not GE.changed(mod, camp):
            messagebox.showinfo(TITLE, "The game's editor has saved nothing new there.", parent=self)
            return
        plan = Plan(mod, "game_editor_back", "game_editor_back", {})
        try:
            taken = GE.take_back(plan, camp)
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror(TITLE, "Not taken back: %s" % e, parent=self)
            return
        log.write("Taken back from the game's editor (backup %s)\n%s" % (bdir, plan.report()))
        said = [w for _, w in plan.warnings]
        messagebox.showinfo(TITLE, "Taken back: %s.%s\n\nA backup was made first - Restore puts it all back." % (
            ", ".join(taken), ("\n\n" + "\n".join(said)) if said else ""), parent=self)
        self.app.load()
        self.show()

    def remove_copy(self):
        from . import log
        from .plan import Plan
        mod, camp = self.app.mod, self._camp()
        note = GE.read_note(mod, camp)
        if not note or not ask(TITLE, "Remove the copy in %s? Changes not taken back are lost (a backup is made "
                                      "first)." % mod.rel(GE.custom_dir(mod, camp)),
                               parent=self, yes="Remove it", no="Keep it"):
            return
        plan = Plan(mod, "game_editor_out", "game_editor_out", {})
        GE.remove(plan, camp)
        bdir = plan.apply()
        log.write("The game's editor copy of %s removed (backup %s)" % (camp, bdir))
        self.show()


def open_window(app):
    return GameEditorWindow(app)
