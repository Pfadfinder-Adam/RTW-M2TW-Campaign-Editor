"""New faction > From zero...: a new faction step by step, nothing of an existing faction seen (fromzero.py) - its
culture (the faction its lines are made from is picked behind it), its names, colours away from every faction's,
its emblem on every sign (a must), a name list mixed from the whole culture; then the form, for its towns and
leader, and one Apply that creates it and recolours every picture it got in its colours."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import fromzero as Z
from .fromzero import internal_of
from . import theme
from .gui_util import ShortHint

TITLE = "New faction from zero"
STEPS = ("Culture", "Names", "Colours", "Emblem", "Name list", "Done")
RECOLOUR_KEY = "recolour:from zero"


def keep_recolour(app):
    """Apply changes recolours every picture the new faction got (its copies of the frame's cards, textures and
    signs) from the frame's colours to its own, after the faction part has written it - the emblem's pictures left
    as they are made. App.zero is read at the write (its name, colours and emblem as the form has them then) - none
    then (the form emptied, Forget it): nothing is recoloured."""
    from .moddata import ModData
    from .plan import Plan

    def build():
        from . import recolour as R
        mod = ModData(app.mod.data)
        z = app.zero or {}
        new, frame = z.get("new"), z.get("frame")
        plan = Plan(mod, "recolour", "recolour_%s" % (new or "new"), {})
        if not new or new not in [n for n, _ in mod.factions()]:
            plan.note(None, "the new faction's pictures are recoloured once it is created")
            return plan
        source = z.get("from") or R.faction_colours(mod).get(frame) or ((200, 0, 0), None)
        target = z.get("to") or R.faction_colours(mod).get(new)
        if not target or not target[0]:
            plan.note(None, "no colours picked for %s: its pictures keep the colours they came with" % new)
            return plan
        made = {k.replace("\\", "/").lower() for k in z.get("art") or ()}
        items = [it for it in R.targets(mod, z.get("campaign"), new)
                 if R.plain_rel(it["rel"]).replace("\\", "/").lower() not in made]
        done = R.plan_recolour(plan, items, list(source), list(target), frame)
        for it, how in done:
            if not isinstance(how, float) and not it.get("skip"):
                plan.warn(None, "%s: %s" % (it["rel"], how))
        return plan
    app.session_add(RECOLOUR_KEY, "Recolour every picture of the new faction (from zero)", None, build=build,
                    quiet=True)


class FromZeroWindow:
    """The steps; Done fills the New faction form (App.zero says it is made from zero)."""

    def __init__(self, app):
        self.app, self.mod = app, app.mod
        self.camp = app.v_campaign.get()
        self.step = 0
        self._logos = None
        self.pools, self.pool_from = None, []
        self.v = {k: tk.StringVar() for k in ("culture", "name", "display_name", "short_name", "adjective",
                                               "people")}
        self.colours = [None, None]
        self.v_common = tk.BooleanVar(value=True)
        w = self.w = tk.Toplevel(app)
        w.title(TITLE)
        w.transient(app)
        w.geometry("720x520")
        top = ttk.Frame(w, padding=(10, 8, 10, 0))
        top.pack(fill="x")
        self.steps_bar = ttk.Label(top, font=("", 10))
        self.steps_bar.pack(anchor="w")
        self.l_title = ttk.Label(top, font=("", 12, "bold"))
        self.l_title.pack(anchor="w", pady=(4, 0))
        self.body = ttk.Frame(w, padding=10)
        self.body.pack(fill="both", expand=True)
        nav = ttk.Frame(w, padding=10)
        nav.pack(fill="x")
        self.b_back = ttk.Button(nav, text="< Back", command=lambda: self.go(-1))
        self.b_back.pack(side="left")
        self.b_next = ttk.Button(nav, text="Next >", command=lambda: self.go(1))
        self.b_next.pack(side="left", padx=theme.BUTTON_GAP)
        ttk.Button(nav, text="Cancel", command=w.destroy).pack(side="right")
        for k in ("display_name", "short_name"):
            self.v[k].trace_add("write", lambda *_: self._name_typed())
        self._auto_internal = ""
        self.show()

    # ---- steps ----
    def show(self):
        for c in self.body.winfo_children():
            c.destroy()
        self.steps_bar.configure(text="   ".join(("[%d %s]" if i == self.step else "%d %s") % (i + 1, s)
                                               for i, s in enumerate(STEPS)))
        self.l_title.configure(text="%d. %s" % (self.step + 1, STEPS[self.step]))
        self.b_back.state(["disabled" if self.step == 0 else "!disabled"])
        self.b_next.configure(text="Fill the form" if self.step == len(STEPS) - 1 else "Next >")
        getattr(self, "s_" + STEPS[self.step].lower().replace(" ", "_"))(self.body)

    def go(self, d):
        if d > 0:
            why = getattr(self, "ok_" + STEPS[self.step].lower().replace(" ", "_"), lambda: None)()
            if why:
                messagebox.showinfo(TITLE, why, parent=self.w)
                return
            if self.step == len(STEPS) - 1:
                return self.finish()
        self.step = max(0, min(len(STEPS) - 1, self.step + d))
        self.show()

    def _hint(self, parent, text):
        ttk.Label(parent, text=text, wraplength=680, justify="left", foreground="#555").pack(anchor="w", pady=(0, 8))

    # 1 culture
    def s_culture(self, f):
        from .culture import names
        self._hint(f, "The game takes the faction's look from its culture: its towns on the map, its portraits and "
                      "agents, the buildings and units open to it. Nothing else of an existing faction comes along: "
                      "its colours, symbol, names and pictures are made in the next steps.")
        cults = [c for c in names(self.mod) if Z.culture_factions(self.mod, c)]
        cb = ttk.Combobox(f, textvariable=self.v["culture"], values=cults, state="readonly", width=30)
        cb.pack(anchor="w")
        if not self.v["culture"].get() and cults:
            self.v["culture"].set(cults[0])
        self.l_frame = ShortHint(f, foreground="#666")
        self.l_frame.pack(anchor="w", pady=(8, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._frame_text())
        self._frame_text()

    def _frame_text(self):
        c = self.v["culture"].get()
        frame = Z.frame_faction(self.mod, self.camp, c) if c else None
        shown = self.app.shown_names()
        others = Z.culture_factions(self.mod, c) if c else []
        self.l_frame.configure(text=(
            "Factions of this culture: %s. The new faction's lines in the game's lists are made from %s's (inside "
            "the files only: its colours, symbol, names, texts and pictures are not taken)." % (
                ", ".join(shown.get(x, x) for x in others), shown.get(frame, frame))) if frame else "")

    def ok_culture(self):
        if not self.v["culture"].get():
            return "Pick the culture."
        return None

    # 2 names
    def s_names(self, f):
        self._hint(f, "The names players read. The internal name is written in the files (lower case letters, "
                      "digits and _) - made from the short name (else the full one) until you change it.")
        g = ttk.Frame(f)
        g.pack(anchor="w")
        rows = [("Name (full)", "display_name", "Kingdom of Zorga"), ("Name (short)", "short_name", "Zorga"),
                ("Adjective", "adjective", "Zorgan"), ("People (plural)", "people", "Zorgans"),
                ("Internal name", "name", "zorga")]
        for i, (label, k, eg) in enumerate(rows):
            ttk.Label(g, text=label).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(g, textvariable=self.v[k], width=34).grid(row=i, column=1, sticky="w", pady=2)
            ttk.Label(g, text="e.g. " + eg, foreground="#888").grid(row=i, column=2, sticky="w", padx=8)

    def _name_typed(self):
        auto = internal_of(self.v["short_name"].get() or self.v["display_name"].get())
        if self.v["name"].get() in ("", self._auto_internal):
            self.v["name"].set(auto)
        self._auto_internal = auto

    def ok_names(self):
        from .build import RE_NAME
        n = self.v["name"].get().strip().lower()
        if not self.v["display_name"].get().strip():
            return "Type the faction's full name."
        if not RE_NAME.match(n):
            return "The internal name: lower case letters, digits and _, a letter first (like 'zorga')."
        if n in {x for x, _ in self.mod.factions()}:
            return "The mod has a faction called %s already - pick another internal name." % n
        return None

    # 3 colours
    def s_colours(self, f):
        self._hint(f, "Its colours on the map, the flags and every picture it gets (recoloured when it is "
                      "created). Pick them yourself or take one of the free pairs - none near any faction's.")
        row = ttk.Frame(f)
        row.pack(anchor="w")
        self.b_cols = []
        for i, label in enumerate(("primary", "secondary")):
            b = ttk.Button(row, text=label, width=12, command=lambda i=i: self._pick(i))
            b.pack(side="left", padx=(0, theme.BUTTON_GAP))
            self.b_cols.append(b)
        ttk.Label(f, text="Free colours (a click takes the pair):").pack(anchor="w", pady=(10, 2))
        sw = ttk.Frame(f)
        sw.pack(anchor="w")
        for p, s in Z.free_colours(self.mod, 8):
            cell = tk.Frame(sw, bd=1, relief="raised", cursor="hand2")
            cell.pack(side="left", padx=2)
            for c, h in ((p, 22), (s, 8)):
                x = tk.Frame(cell, width=34, height=h, bg="#%02x%02x%02x" % c)
                x.pack()
                x.bind("<Button-1>", lambda e, p=p, s=s: self._set_colours(p, s))
        self.l_alike = ttk.Label(f, wraplength=680, justify="left")
        self.l_alike.pack(anchor="w", pady=(10, 0))
        self._paint()

    def _pick(self, i):
        from tkinter import colorchooser
        c = self.colours[i]
        got = colorchooser.askcolor(color="#%02x%02x%02x" % c if c else None, parent=self.w,
                                    title=("primary", "secondary")[i] + " colour")
        if got and got[0]:
            self.colours[i] = tuple(int(x) for x in got[0])
            self._paint()

    def _set_colours(self, p, s):
        self.colours = [p, s]
        self._paint()

    def _paint(self):
        for b, c in zip(self.b_cols, self.colours):
            if c:
                theme.paint(b, c)
        alike = Z.colours_alike(self.mod, self.colours[0], self.colours[1])
        shown = self.app.shown_names()
        if not self.colours[0]:
            self.l_alike.configure(text="", foreground="#555")
        elif alike:
            self.l_alike.configure(foreground="#a60", text="Looks like: " + ", ".join(
                "%s (%s)" % (shown.get(x, x), "both colours" if how == "both" else "the primary")
                for x, how in alike) + " - on the map the two would be hard to tell apart.")
        else:
            self.l_alike.configure(foreground="#2a7", text="No faction has colours like these.")

    def ok_colours(self):
        if not self.colours[0]:
            return "Pick its primary colour (or click one of the free pairs)."
        if Z.colours_alike(self.mod, self.colours[0], self.colours[1]):
            if not messagebox.askyesno(TITLE, "Another faction's colours look like these. Keep them anyway?",
                                       parent=self.w):
                return "Pick other colours."
        return None

    # 4 emblem
    def s_emblem(self, f):
        self._hint(f, "Its symbol - a picture of yours (a square PNG with a clear background is best). Fitted once, "
                      "it is made into every sign of the faction: the menu buttons, the loading screen, logos, the "
                      "flag on the campaign map and its 3D symbol, the battle banners, the flag on its towns, the "
                      "captains' cards. Without it the new faction would show the signs of %s." %
                   self.app.shown_names().get(self.frame(), self.frame()))
        ttk.Button(f, text="Pick the emblem...", command=self._emblem).pack(anchor="w")
        self.l_emblem = ttk.Label(f, wraplength=680, justify="left")
        self.l_emblem.pack(anchor="w", pady=(10, 0))
        self.w.bind("<FocusIn>", lambda e: self._emblem_state(), add="+")
        self._emblem_state()

    def frame(self):
        return Z.frame_faction(self.mod, self.camp, self.v["culture"].get())

    def _emblem(self):
        self.to_form()
        self.app.art_editor.emblem_window()

    def _logo_pic(self):
        """The new faction's loading-screen logo as the emblem made it (a Pillow image) or None."""
        from . import factionart as FA
        frame, new = self.frame(), self.v["name"].get().strip().lower()
        try:
            pics = FA.faction_pictures(self.mod, self.camp, frame)
        except Exception:
            return None, False
        art = self.app.art_replace
        made = [p for p in pics if FA.picture_target(p, frame, new) in art]
        logo = next((p for p in made if p["label"].startswith("loading-screen logo")), None)
        if logo is None:
            return None, bool(made)
        got = art[FA.picture_target(logo, frame, new)]
        path = got.get("src") if isinstance(got, dict) else got
        try:
            from .recolour import read_picture
            return read_picture(path), True
        except Exception:
            return None, True

    def _emblem_state(self):
        try:
            if not self.l_emblem.winfo_exists():
                return
        except (tk.TclError, AttributeError):
            return
        pic, done = self._logo_pic()
        if not done:
            self.l_emblem.configure(foreground="#a60", text="No emblem yet.")
            return
        alike = []
        if pic is not None:
            if self._logos is None:
                self._logos = Z.faction_logos(self.mod, self.camp)
            alike = Z.symbols_alike(pic, self._logos)
        shown = self.app.shown_names()
        if alike:
            self.l_emblem.configure(foreground="#a60", text="Made - but its logo looks nearly the same as %s's. "
                                    "Another symbol would tell them apart." % ", ".join(
                                        shown.get(x, x) for x, _ in alike))
        else:
            self.l_emblem.configure(foreground="#2a7", text="Made: every sign of the faction carries it (written "
                                    "with Apply). Not like any faction's symbol.")

    def ok_emblem(self):
        if self._logo_pic()[1]:
            return None
        try:
            import PIL  # noqa: F401
        except ImportError:
            return None if messagebox.askyesno(TITLE, "The emblem needs Pillow (pip install pillow). Go on without "
                                               "it? The faction keeps the signs of %s then." % self.frame(),
                                               parent=self.w) else "Install Pillow, then pick the emblem."
        return "Pick the emblem first: without it the new faction shows another faction's signs."

    # 5 name list
    def s_name_list(self, f):
        c = self.v["culture"].get()
        if self.pools is None or self._pools_for != c:
            self.pools, self.pool_from = Z.culture_name_list(self.mod, c)
            self.pools = {p: [k.replace("_", " ") for k in v] for p, v in self.pools.items()}
            self._pools_for = c
        own = self.app.name_list.get("(new)") if self.app.v["name"].get().strip().lower() == \
            self.v["name"].get().strip().lower() else None
        shown = self.app.shown_names()
        from .namelists import counts
        if own:
            text = "Its own list (typed in Name list...): %s." % counts(own)
        elif len(self.pool_from) > 1:
            text = ("Mixed from the names of the whole culture - %s - so it is no one faction's list: %s." % (
                ", ".join(shown.get(x, x) for x in self.pool_from), counts(self.pools)))
        else:
            text = ("Only %s has names in this culture: its list is taken. Name list... makes one of its own." %
                    ", ".join(shown.get(x, x) for x in self.pool_from) if self.pool_from else
                    "No faction of this culture has names: type its own in Name list...")
        self._hint(f, "The names its leader, generals, agents and princesses get.")
        ttk.Label(f, text=text, wraplength=680, justify="left").pack(anchor="w")
        ttk.Button(f, text="Name list...", command=self._edit_names).pack(anchor="w", pady=(10, 0))

    def _edit_names(self):
        self.to_form()
        self.app.name_list_dialog()

    # 6 done
    def s_done(self, f):
        shown = self.app.shown_names()
        self._hint(f, "Fill the form puts all this on the New faction tab. There pick its towns and capital on the "
                      "map, its leader and heir, then Create faction: one Apply writes it, its emblem, and every "
                      "picture it gets recoloured in its colours. Check mod files lists anything it still shares "
                      "with another faction.")
        for label, val in (("Culture", self.v["culture"].get()),
                           ("Name", "%s (%s)" % (self.v["display_name"].get(), self.v["name"].get())),
                           ("Colours", " / ".join("%d %d %d" % c for c in self.colours if c)),
                           ("Lines in the game's lists made from", shown.get(self.frame(), self.frame()))):
            ttk.Label(f, text="%s: %s" % (label, val)).pack(anchor="w")
        frame = self.frame()
        own, common = Z.template_units(self.mod, frame, self.v["culture"].get())
        if own and len(common) >= Z.MIN_COMMON:
            ttk.Checkbutton(f, variable=self.v_common, text=(
                "Units: only the %d its culture shares - not the %d only %s has (Roster > By buildings gives it units "
                "of its own)" % (len(common), len(own), shown.get(frame, frame)))).pack(anchor="w", pady=(10, 0))
        elif own:
            ttk.Label(f, foreground="#a60", wraplength=680, justify="left", text=(
                "Units: its culture shares only %d, so it keeps the %d only %s has too - Roster > By buildings "
                "changes them." % (len(common), len(own), shown.get(frame, frame)))).pack(anchor="w", pady=(10, 0))

    # ---- the form ----
    def to_form(self):
        """The steps into the New faction form (its template: the frame - a change empties the form, so only then)."""
        a = self.app
        frame = self.frame()
        if a.v_work.get() != "new":
            a.v_work.set("new")
            a.work_changed()
        if a.v["template"].get().strip() != frame:
            a.v["template"].set(frame)
            a.template_changed()
        for k in ("name", "display_name", "short_name", "adjective", "people"):
            a.v[k].set(self.v[k].get().strip().lower() if k == "name" else self.v[k].get().strip())
        a.v["culture"].set(self.v["culture"].get())
        for which, c in zip(("primary", "secondary"), self.colours):
            a.colours[which] = c
            if c:
                theme.paint(a.b_primary if which == "primary" else a.b_secondary, c)
        if self.pools and not a.name_list.get("(new)"):
            a.name_list["(new)"] = {p: list(v) for p, v in self.pools.items()}
            a.refresh_name_combos()
        a.zero = {"culture": self.v["culture"].get(), "frame": frame, "campaign": self.camp,
                  "common_units": self.v_common.get()}
        a._from_zero_look()

    def finish(self):
        from .recolour import faction_colours
        self.to_form()
        a = self.app
        a.zero["from"] = faction_colours(self.mod).get(self.frame())
        keep_recolour(a)
        a.zero_sync()
        self.w.destroy()
        a.status.set("New faction from zero: the form is filled - pick its towns and capital on the map, its leader, "
                     "then Create faction.")


def open_from_zero(app):
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first.")
        return None
    return FromZeroWindow(app)


__all__ = ["FromZeroWindow", "open_from_zero", "keep_recolour"]
