"""The Roster tab (Edit faction): every unit and building level of the mod, whether
the faction has it, and giving or taking it. The picks are kept by the window
(App.roster_set, with Undo) and written on Apply with everything tied to them -
see roster.py."""

import tkinter as tk
from tkinter import ttk

from .gui_util import ShortHint
from . import roster as R
from . import theme

HAS = {"own": "yes", "culture": "yes (culture)", "all": "yes (everyone)", None: "no"}


class RosterEditor(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self.data, self.faction, self._for = None, None, None
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.title = ttk.Label(top, text="Edit faction: pick the faction on the Faction tab", font=("", 10, "bold"))
        self.title.pack(side="left")
        ttk.Label(top, text="   Find").pack(side="left")
        self.v_find = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_find, width=20)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self.redraw())
        self.v_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="only what it has", variable=self.v_only, command=self.redraw).pack(side="left", padx=8)
        ttk.Button(top, text="Undo all changes here", command=self.reset).pack(side="right")
        ShortHint(self, foreground="#555", justify="left", wraplength=1000, text=(
            "Give or take a unit or a building level: double click, or select and use the buttons. On Apply the "
            "tool keeps every place in step - a unit: its ownership (export_descr_unit), the recruit lines that "
            "let the faction train it (export_descr_buildings) and its cards (ui/units, ui/unit_info); a building "
            "level: its 'requires factions' list. A culture or 'everyone' is written out as the other factions "
            "when only this one loses it. Armies and towns that already hold it keep it (the preview warns).")
                  ).pack(fill="x", pady=(2, 6))
        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)
        self.tv_units = self._table(panes, "Units", (("type", "unit", 230), ("cat", "category", 80),
                                                     ("has", "has it", 150), ("where", "recruited in (for it)", 260)))
        self.tv_build = self._table(panes, "Building levels", (("level", "chain / level", 280),
                                                               ("has", "may build", 120)), tree=True)
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(4, 0))
        ttk.Button(bar, text="Give", command=lambda: self.pick(True)).pack(side="left")
        ttk.Button(bar, text="Take away", command=lambda: self.pick(False)).pack(side="left", padx=4)
        ttk.Button(bar, text="As it is", command=lambda: self.pick(None)).pack(side="left")
        self.info = ttk.Label(bar, text="", foreground="#333")
        self.info.pack(side="left", padx=12)

    def _table(self, panes, label, cols, tree=False):
        box = ttk.LabelFrame(panes, text=label, padding=2)
        panes.add(box, weight=3 if not tree else 2)
        ids = [c[0] for c in cols]
        tv = ttk.Treeview(box, columns=ids[1:] if tree else ids, show="tree headings" if tree else "headings",
                          selectmode="extended")
        if tree:
            tv.heading("#0", text=cols[0][1])
            tv.column("#0", width=cols[0][2])
            cols = cols[1:]
        for cid, text, width in cols:
            tv.heading(cid, text=text)
            tv.column(cid, width=width, stretch=cid in ("where", "type"))
        sb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.tag_configure("give", background="#d9f2d0", foreground="#000000")
        tv.tag_configure("take", background="#f4c7c3", foreground="#000000")
        tv.tag_configure("no", foreground=theme.ink("#888", "field"))
        tv.bind("<Double-1>", lambda e, tv=tv: self.toggle(tv))
        return tv

    # ---- data ----
    def load(self):
        app = self.app
        faction = app.v["template"].get().strip() if app.editing() else ""
        if not app.mod or not faction:
            self.data, self.faction = None, None
            self.title.configure(text="The Roster is for Edit faction: pick the faction there. (A new faction "
                                      "gets its template's units and buildings; change them after, in Edit.)")
            for tv in (self.tv_units, self.tv_build):
                tv.delete(*tv.get_children())
            return
        if self.faction != faction or self.data is None or self._for is not app.mod:
            self.data = R.roster(app.mod, faction)
            self.faction, self._for = faction, app.mod
        self.title.configure(text="Roster of %s (%s)" % (faction, app.mod.culture(faction) or "?"))
        self.redraw()

    def forget(self):
        """The files changed (Apply, Restore, another mod): read again when shown."""
        self.data = None

    def _state(self, key, has):
        pick = self.app.roster_set.get(key)
        if pick is True and not has:
            return "give"
        if pick is False and has:
            return "take"
        return None

    def redraw(self):
        if not self.data:
            return
        q = self.v_find.get().strip().lower()
        only = self.v_only.get()
        tv = self.tv_units
        tv.delete(*tv.get_children())
        for u in self.data["units"]:
            key = "unit:" + u["type"]
            st = self._state(key, u["has"])
            has_now = (u["has"] and st != "take") or st == "give"
            if q and q not in u["type"].lower() and q not in u["category"].lower():
                continue
            if only and not has_now and not st:
                continue
            places = u["recruit"] if st != "give" else u["recruit_any"]
            where = ", ".join("%s/%s" % x for x in places[:3]) + (" ..." if len(places) > 3 else "")
            if st == "give":
                where = ("on Apply: " + where) if where else "no building recruits it (Buildings: Add line)"
            has = HAS[u["has"]] + {"give": "  -> give", "take": "  -> take away"}.get(st, "")
            tv.insert("", "end", iid=key, values=(u["type"], u["category"], has,
                                                  where or ("-" if u["has"] else "")),
                      tags=(st or ("no" if not u["has"] else "")),)
        tv = self.tv_build
        tv.delete(*tv.get_children())
        chains = {}
        for b in self.data["buildings"]:
            key = "building:%s:%s" % (b["chain"], b["level"])
            st = self._state(key, b["has"])
            has_now = (b["has"] and st != "take") or st == "give"
            if q and q not in b["chain"].lower() and q not in b["level"].lower():
                continue
            if only and not has_now and not st:
                continue
            if b["chain"] not in chains:
                chains[b["chain"]] = tv.insert("", "end", iid="chain:" + b["chain"], text=b["chain"], open=bool(q))
            has = HAS[b["has"]] + {"give": "  -> give", "take": "  -> take away"}.get(st, "")
            tv.insert(chains[b["chain"]], "end", iid=key, text=b["level"], values=(has,),
                      tags=(st or ("no" if not b["has"] else "")),)
        for chain, iid in chains.items():               # the chain's row: how many of its levels
            levels = [b for b in self.data["buildings"] if b["chain"] == chain]
            n = sum(1 for b in levels if (b["has"] and self._state("building:%s:%s" % (chain, b["level"]), b["has"])
                                          != "take") or self._state("building:%s:%s" % (chain, b["level"]),
                                                                    b["has"]) == "give")
            tv.item(iid, values=("%d of %d" % (n, len(levels)),))
        n = len(self.app.roster_set)
        self.info.configure(text="%d change(s) - Preview, then Apply changes" % n if n else "")

    def _keys(self, tv, items):
        out = []
        for i in items:
            if i.startswith("chain:"):
                out += list(tv.get_children(i))
            else:
                out.append(i)
        return out

    def _has(self, key):
        if not self.data:
            return None
        kind, _, rest = key.partition(":")
        if kind == "unit":
            return next((u["has"] for u in self.data["units"] if u["type"] == rest), None)
        chain, _, level = rest.partition(":")
        return next((b["has"] for b in self.data["buildings"] if b["chain"] == chain and b["level"] == level), None)

    def pick(self, give, tv=None):
        """give True / False, or None for 'as it is', for the selected rows of either table."""
        if not self.data:
            self.load()
        if not self.data:
            return
        keys = []
        for t in ([tv] if tv else (self.tv_units, self.tv_build)):
            keys += self._keys(t, t.selection())
        if not keys:
            self.app.status.set("Select a unit or a building level first.")
            return
        self.app.remember()
        extra = []
        if give is not None:
            keys, extra = self._chain_pull(keys, give)
        for key in keys:
            has = bool(self._has(key))
            if give is None or give == has:
                self.app.roster_set.pop(key, None)
            else:
                self.app.roster_set[key] = give
        self.app.roster_changed()
        self.redraw()
        if extra:
            self.app.status.set("%s too: %s (a chain is built level by level)" % (
                "The levels below were given" if give else "The levels above were taken away",
                ", ".join(k.split(":", 2)[2] for k in extra)))
        for t in (self.tv_units, self.tv_build):
            present = [k for k in keys if t.exists(k)]
            if present:
                t.selection_set(present)
                t.see(present[0])

    def _chain_pull(self, keys, give):
        """A building level pulls its chain along: giving one gives the levels below it, taking one takes
        the levels above (the game builds a chain level by level). Returns (all keys, the added ones)."""
        out, extra = list(keys), []
        for key in keys:
            if not key.startswith("building:"):
                continue
            chain, level = key.split(":", 2)[1:]
            levels = [b["level"] for b in self.data["buildings"] if b["chain"] == chain]
            if level not in levels:
                continue
            i = levels.index(level)
            for other in (levels[:i] if give else levels[i + 1:]):
                k = "building:%s:%s" % (chain, other)
                if k not in out and bool(self._has(k)) != give:
                    out.append(k)
                    extra.append(k)
        return out, extra

    def toggle(self, tv):
        if not self.data:
            self.load()                              # the files changed meanwhile (Apply): read them again
        item = tv.focus()
        if not self.data or not item or item.startswith("chain:") or not tv.exists(item):
            return
        has = bool(self._has(item))
        pick = self.app.roster_set.get(item)
        now = pick if pick is not None else has
        tv.selection_set([item])
        self.pick(not now, tv)

    def reset(self):
        if self.app.roster_set:
            self.app.remember()
            self.app.roster_set.clear()
            self.app.roster_changed()
        self.redraw()
