"""The Buildings work's 'By faction' tab: a faction's buildings as the game shows them. On the left the chains it may
build, as tiles with the game's pictures, grouped by type; in the middle the picked chain's window - its levels as
steps from left to right (picture, cost, turns, the town they need) and, under the picked level, the units the
faction recruits there as cards (the hover tells how); on the right the picked unit's card, numbers and where else
it is recruited, with a way to its lines in Units. Both games; it only shows - the lines are changed on the
'Lines' tab and in Units (factionbuildings reads, nothing here writes)."""

import tkinter as tk
from tkinter import ttk

from . import factionbuildings as FB
from . import settings, theme
from .gui_util import ScrollFrame, ShortHint, flow, tip

TILE = (78, 62)                  # a building picture in the list (the game's small ones are 78 x 62)
STEP = (110, 90)                 # a level's picture in the chain's window
CARD = (48, 64)                  # a unit card (Rome's are 48 x 64; Medieval II's are scaled down to it)


class FactionBuildings(ttk.Frame):
    """editor: the Buildings work's RecordEditor (its file as typed, and its Lines tab to jump to)."""

    PICK_FACTION = True              # its own faction box (the Roster's tab follows Edit faction's pick instead)

    def __init__(self, master, app, editor):
        super().__init__(master, padding=4)
        self.app, self.editor = app, editor
        self.mod, self.items, self.chain, self.level, self.unit = None, [], None, None, None
        self._stale = True
        self._pics = self._texts = self._utexts = self._units = None
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 4))
        self.lbl_fac = ttk.Label(bar, text="Faction")
        self.v_fac = tk.StringVar()
        self.cb_fac = ttk.Combobox(bar, textvariable=self.v_fac, state="readonly", width=30)
        if self.PICK_FACTION:
            self.lbl_fac.pack(side="left")
            self.cb_fac.pack(side="left", padx=4)
        self.cb_fac.bind("<<ComboboxSelected>>", lambda e: self._faction_picked())
        ttk.Label(bar, text="Find").pack(side="left", padx=(8, 0))
        self.v_find = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.v_find, width=18)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self._tiles())
        self.v_all = tk.BooleanVar(value=bool(settings.get("byfaction_everyone")))
        ttk.Checkbutton(bar, text="also what it cannot build (grey)", variable=self.v_all,
                        command=self._all_toggled).pack(side="left", padx=8)
        self.lbl_count = ttk.Label(bar, text="", foreground=theme.ink("#666", "bg"))
        self.lbl_count.pack(side="left", padx=4)
        self.hint = ShortHint(bar, text="A faction's buildings as the game shows them: pick a building on the left, a level "
                            "of it in the middle, a unit card to see it on the right. A card's hover tells how the "
                            "unit is recruited there. Change the lines on the Lines tab (Lines of this building) "
                            "and in Units (Open in Units); this tab follows what you type there.",
                  foreground="#555", wraplength=700, justify="left")
        self.hint.pack(side="left", padx=8)
        self.bar = bar
        self._bar_extra(bar)
        flow(bar)
        pane = self.pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        self.left = ScrollFrame(pane)
        pane.add(self.left, weight=1)
        self.mid = ScrollFrame(pane, padding=(6, 0))
        pane.add(self.mid, weight=2)
        right = ttk.Frame(pane, padding=(6, 0, 0, 0))
        pane.add(right, weight=1)
        self._build_right(right)
        self.lbl_empty = ttk.Label(self.mid.inner, text="Pick a building on the left", font=("", 10, "bold"))
        self.lbl_empty.pack(anchor="w")

    # ---- what a tab built on this one adds (the Roster's 'By buildings' - gui_rosterbuildings) ----
    def _bar_extra(self, bar):
        """More pieces on the top bar."""

    def _changed(self, items):
        """The chains as shown (picks not yet written laid over them)."""
        return items

    def _tile_made(self, box, c):
        """A chain's tile is on the left."""

    def _level_made(self, box, lv):
        """A level's step is in the chain's window."""

    def _card_made(self, box, u, lv):
        """A unit's card is under the picked level."""

    def _level_tail(self, parent, c, lv):
        """Under the picked level's cards."""

    def _build_right(self, right):
        """The right side: the picked unit."""
        from .gui_preview import UnitPreview
        self.preview = UnitPreview(right)
        self.preview.pack(fill="both", expand=True)
        rb = ttk.Frame(right)
        rb.pack(fill="x", pady=(4, 0))
        self.b_unit = ttk.Button(rb, text="Open in Units", command=self.open_unit, state="disabled")
        self.b_unit.pack(side="left")
        tip(self.b_unit, "The Units work with this unit picked: every line of it, its cards, models and voice.")
        self.where = ttk.Frame(right)
        self.where.pack(fill="x", pady=(4, 0))

    # ---- reading ----
    def load(self, mod):
        """A new mod (or the same one after Apply): read again when next shown."""
        if mod is not self.mod:
            self._pics = self._texts = self._utexts = self._units = None
        self.mod = mod
        self._stale = True
        if self.winfo_ismapped():
            self.refresh()

    def shown(self):
        """The tab came up: read what changed since (the Lines tab's typing, another mod)."""
        if self._stale:
            self.refresh()

    def _faction(self):
        return self.v_fac.get().split(" - ")[0].strip()

    def refresh(self):
        self._stale = False
        mod = self.mod
        if mod is None:
            self.cb_fac["values"] = []
            self._clear(self.left.inner)
            return
        from .build import faction_label
        shown = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
        facs = [n for n, _ in mod.factions()]
        labels = [faction_label(n, shown.get(n)) for n in facs]
        self.cb_fac["values"] = labels
        if self._faction() not in facs:
            try:                                     # the faction the window has picked, else the one picked
                t = self.app.v["template"].get().strip()     # here last time, else the first
            except Exception:
                t = ""
            first = next((f for f in (t, settings.get("byfaction_faction")) if f in facs), facs[0] if facs else "")
            self.v_fac.set(labels[facs.index(first)] if first else "")
        self._read()

    def _read(self):
        mod, fac = self.mod, self._faction()
        if self._pics is None:
            from .buildings import BuildingPictures
            from .units import read_units
            self._pics = BuildingPictures(mod)
            self._texts = FB.text_index(mod, "export_buildings.txt")
            self._utexts = FB.text_index(mod, "export_units.txt")
            edu = mod.file("edu")
            self._units = {u.type: u for u in (read_units(mod.load(edu)) if edu else [])}
        try:
            f = self.editor._src() if self.editor is not None and self.editor.mod is mod else None
        except Exception:
            f = None
        self.items = self._changed(FB.faction_chains(mod, fac, f)) if fac else []
        self.preview.faction = fac
        self._tiles()
        keep = next((c for c in self.items if self.chain and c["chain"] == self.chain["chain"]), None)
        self.show_chain(keep, self.level["name"] if keep and self.level else None)

    def _faction_picked(self):
        settings.put("byfaction_faction", self._faction())
        self._read()

    def _all_toggled(self):
        settings.put("byfaction_everyone", bool(self.v_all.get()))
        self._tiles()

    # ---- pictures and names ----
    def _culture(self):
        return self.mod.culture(self._faction()) if self.mod else None

    def _level_pic(self, level, size):
        """The picture of a level for the faction's culture (never another culture's - BuildingPictures)."""
        path = self._pics.find(self._culture(), level) if self._pics else None
        return self.app.pictures.get(path, size=size) if path and hasattr(self.app, "pictures") else None

    def _level_name(self, level):
        name, _ = FB.level_shown(self._texts or {}, level, self._faction(), self._culture())
        return name or level.replace("_", " ")

    def _unit_card(self, unit):
        from .units import unit_card
        u = (self._units or {}).get(unit)
        if u is None or not hasattr(self.app, "pictures"):
            return None
        try:
            path = unit_card(self.mod, u, self._faction())
        except Exception:
            path = None
        img = self.app.pictures.get(path, size=CARD) if path else None
        return img if img is not None else self.app.pictures.missing(unit, size=CARD)

    def _unit_name(self, unit):
        u = (self._units or {}).get(unit)
        return (self._utexts or {}).get(u.dictionary.lower(), "") if u is not None and u.dictionary else ""

    @staticmethod
    def _clear(frame):
        for w in frame.winfo_children():
            w.destroy()

    def _box(self, parent, image, text, picked=False, grey=False, width=12, mark=None):
        """A tile: a picture over its words, a frame around it (the picked one stands out); the click on any part.
        mark: 'give' / 'take' - a change not yet written (green / red, theme.mark)."""
        pal = theme.palette()
        bg = theme.mark(mark) if mark else pal["accent"] if picked else pal["field"]
        fg = pal["muted"] if grey else pal["fg"]
        box = tk.Frame(parent, background=bg, highlightthickness=1, cursor="hand2",
                       highlightbackground=pal["select"] if picked else pal["border"])
        if image is not None:
            lb = tk.Label(box, image=image, background=bg)
            lb.image = image
            lb.pack(padx=2, pady=(2, 0))
        tk.Label(box, text=text, background=bg, foreground=fg, wraplength=width * 8, justify="center",
                 font=("", 8)).pack(padx=2, pady=(0, 2))
        return box

    @staticmethod
    def _wrapped(label):
        """A label whose words wrap at the width the pane gives it (a fixed width ran under the scroll bar)."""
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(120, e.width - 4)), add="+")
        return label

    @staticmethod
    def _on_click(box, command):
        for w in [box] + box.winfo_children():
            w.bind("<Button-1>", lambda e: command())

    # ---- the left: the chains as tiles ----
    def _tiles(self):
        self._clear(self.left.inner)
        groups = FB.grouped(self.items, self.v_all.get(), self.v_find.get())
        n = sum(len(cs) for _, cs in groups)
        can = sum(1 for c in self.items if c["builds"])
        self.lbl_count.configure(text="%d building chain(s) it may build, of %d" % (can, len(self.items))
                                 if self.items else ("" if self.mod is None else "no export_descr_buildings.txt"))
        if not n and self.items:
            ttk.Label(self.left.inner, text="None of its chains match.", foreground="#888").pack(anchor="w")
        for g, cs in groups:
            lf = ttk.LabelFrame(self.left.inner, text="%s (%d)" % (FB.GROUP_TITLES[g], len(cs)), padding=4)
            lf.pack(fill="x", pady=(0, 6))
            row = ttk.Frame(lf)
            row.pack(fill="x")
            for c in cs:
                first = next((lv for lv in c["levels"] if lv["has"]), c["levels"][0] if c["levels"] else None)
                img = self._level_pic(first["name"], TILE) if first else None
                picked = self.chain is not None and self.chain["chain"] == c["chain"]
                words = self._level_name(first["name"]) if first else c["chain"]
                box = self._box(row, img, words + (" (castle)" if c["castle"] else ""), picked, grey=not c["builds"],
                                mark=self._chain_mark(c))
                box.pack(side="left", padx=2, pady=2)
                self._on_click(box, lambda c=c: self.show_chain(c))
                tip(box, self._chain_words(c))
                self._tile_made(box, c)
            flow(row, top=True)

    @staticmethod
    def _chain_mark(c):
        """'give' / 'take' when a level of the chain is given / taken away and not yet written."""
        marks = {x.get("pending") for x in c["levels"]} - {None}
        return "give" if marks == {"give"} else "take" if marks == {"take"} else None

    def _chain_words(self, c):
        lv = [x["name"] for x in c["levels"]]
        units = sorted({u["unit"] for x in c["levels"] if x["has"] for u in x["units"]})
        return "%s - %s level(s): %s%s%s" % (
            c["chain"], len(lv), ", ".join(lv[:8]) + (" ..." if len(lv) > 8 else ""),
            ("\nrecruits: %s" % ", ".join(units[:10]) + (" ..." if len(units) > 10 else "")) if units else "",
            "" if c["builds"] else "\n%s cannot build any level of it" % self._faction())

    # ---- the middle: the chain's window ----
    def show_chain(self, c, level=None):
        old = self.chain
        self.chain = c
        if old is not c and (old is None or c is None or old["chain"] != c["chain"]):
            self._tiles()                              # the picked tile stands out
        self._clear(self.mid.inner)
        if c is None:
            self.level = None
            ttk.Label(self.mid.inner, text="Pick a building on the left", font=("", 10, "bold")).pack(anchor="w")
            return
        head = ttk.Frame(self.mid.inner)
        head.pack(fill="x")
        ttk.Label(head, text="building %s" % c["chain"], font=("", 11, "bold")).pack(side="left")
        b = ttk.Button(head, text="Lines of this building", command=lambda: self.open_lines(c["chain"]))
        b.pack(side="left", padx=8)
        tip(b, "The Lines tab with this chain picked: every line of it, its pictures and texts.")
        lv = next((x for x in c["levels"] if x["name"] == level), None) or \
            next((x for x in c["levels"] if x["has"]), c["levels"][0] if c["levels"] else None)
        self.level = lv
        steps = ttk.Frame(self.mid.inner)
        steps.pack(fill="x", pady=(6, 4))
        for n, x in enumerate(c["levels"]):
            if n:
                ttk.Label(steps, text="→", font=("", 14)).pack(side="left")
            words = [self._level_name(x["name"])]
            if x["kind"]:
                words.append(x["kind"])
            nums = ", ".join(p for p in (("%d" % x["cost"]) if x["cost"] else "",
                                         ("%d turn(s)" % x["turns"]) if x["turns"] else "") if p)
            if nums:
                words.append(nums)
            if x["town"]:
                words.append("from %s" % x["town"].replace("_", " "))
            if not x["has"]:
                words.append("(not for %s)" % self._faction())
            box = self._box(steps, self._level_pic(x["name"], STEP), "\n".join(words), x is lv, not x["has"],
                            width=15, mark=x.get("pending"))
            box.pack(side="left", padx=2, pady=2)
            self._on_click(box, lambda x=x: self.show_chain(c, x["name"]))
            self._level_made(box, x)
            tip(box, "%s: costs %d, %d turn(s) to build, a town at least %s%s%s" % (
                x["name"], x["cost"], x["turns"], x["town"] or "village",
                "; needs %s" % x["needs"] if x["needs"] else "",
                "" if x["has"] else "; %s may not build it (its factions list)" % self._faction()))
        flow(steps, top=True)
        if lv is None:
            return
        units = lv["units"] if lv["has"] else []
        ttk.Label(self.mid.inner, text="Recruits here (%d)%s" % (
            len(units), "" if lv["has"] else " - %s may not build this level" % self._faction()),
            font=("", 10, "bold")).pack(anchor="w", pady=(6, 2))
        cards = ttk.Frame(self.mid.inner)
        cards.pack(fill="x")
        for u in units:
            shown = self._unit_name(u["unit"])
            box = self._box(cards, self._unit_card(u["unit"]), shown or u["unit"],
                            self.unit == u["unit"], grey=not u["known"], width=10, mark=u.get("pending"))
            box.pack(side="left", padx=2, pady=2)
            self._on_click(box, lambda u=u: self.show_unit(u["unit"]))
            words = FB.unit_words(u)
            un = (self._units or {}).get(u["unit"])
            tip(box, "%s\n%s%s" % (shown or u["unit"], un.summary() if un is not None else u["unit"],
                                   "\n" + words if words else ""))
            self._card_made(box, u, lv)
        if units:
            flow(cards, top=True)
        elif lv["has"]:
            ttk.Label(cards, text="No unit is recruited in this level by %s." % self._faction(),
                      foreground="#888").pack(anchor="w")
        self._level_tail(self.mid.inner, c, lv)
        if lv["others"]:
            ttk.Label(self.mid.inner, text="%d more recruit line(s) here are for other factions." % lv["others"],
                      foreground="#888").pack(anchor="w", pady=(4, 0))
        _, desc = FB.level_shown(self._texts or {}, lv["name"], self._faction(), self._culture())
        if desc:
            self._wrapped(ttk.Label(self.mid.inner, text=desc, justify="left")).pack(fill="x", anchor="w", pady=(8, 2))
        if lv["needs"]:
            self._wrapped(ttk.Label(self.mid.inner, text="Needs: %s" % lv["needs"], justify="left",
                                    foreground=theme.ink("#555", "bg"))).pack(fill="x", anchor="w")

    # ---- the right: the unit ----
    def show_unit(self, unit):
        self.unit = unit
        self.preview.faction = self._faction()
        self.preview.show(unit, self.mod)
        self.b_unit.configure(state="normal")
        self._clear(self.where)
        places = FB.recruited_in(self.items, unit)
        ttk.Label(self.where, text="%s recruits it in:" % self._faction() if places else
                  "%s recruits it in no building." % self._faction(), font=("", 9, "bold")).pack(anchor="w")
        for chain, level in places:
            c = next(x for x in self.items if x["chain"] == chain)
            lb = ttk.Label(self.where, text="%s / %s" % (chain, level), foreground=theme.palette()["link"],
                           cursor="hand2")
            lb.pack(anchor="w")
            lb.bind("<Button-1>", lambda e, c=c, level=level: self.show_chain(c, level))
        if self.chain is not None:                        # the picked card stands out
            self.show_chain(self.chain, self.level["name"] if self.level else None)

    # ---- the ways out ----
    def open_lines(self, chain):
        if self.editor is not None:
            self.editor.show_lines_tab()
            self.editor.pick(chain)
        elif hasattr(self.app, "open_building"):    # Edit faction > By buildings: the Buildings work opens (#422)
            self.app.open_building(chain)

    def open_unit(self):
        if self.unit and hasattr(self.app, "open_unit"):
            self.app.open_unit(self.unit)
