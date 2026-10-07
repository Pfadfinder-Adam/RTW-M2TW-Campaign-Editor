"""The Module builder's blocks the Scratch way: the kinds of blocks in coloured groups on the left (events yellow,
control orange, conditions green, actions blue), the module on the right as blocks that fit into each other - the WHEN
hat on top, FOR EACH and IF / ELSE as C-shaped blocks holding the actions. A block is dragged from the left into its
place (a line shows where it goes) or clicked to go in at the end; a block of the module is dragged to another place,
or out (back onto the blocks on the left, or a right click) to take it out. The recipe underneath is the list view's
(modbuilder): both views show the same module, old modules open in either."""

import tkinter as tk
from tkinter import ttk

from . import modbuilder as MB, theme
from .gui_util import ScrollFrame, hint, scroll_y, wheel

# Scratch's own colours for its groups; a darker tint of each for the dark look
COL = {"event": "#ffbf00", "control": "#ffab19", "cond": "#59c059", "act": "#4c97ff", "empty": "#e6e6e6"}
COL_DARK = {"event": "#a87e00", "control": "#b26f0a", "cond": "#3b8a3b", "act": "#2f68c0", "empty": "#3a3d43"}
ARM = 22                        # the C-block's left arm
BAR = 20                        # the C-block's 'else' and bottom bars
GAP = 3                         # between two blocks of a stack
GRIP = "⠇"                 # the dots a block is dragged by


def colour(kind):
    return (COL_DARK if theme.dark() else COL)[kind]


class ScratchView(ttk.Frame):
    """Lives in the builder's window in place of the list view; render() draws builder.recipe."""

    def __init__(self, master, builder):
        super().__init__(master)
        self.b = builder
        self.zones = []                        # [(x1, y1, x2, y2, kind, group, index)] where a dragged block may go
        self.drag = None
        side = ttk.Frame(self, width=250)
        side.pack(side="left", fill="y", padx=(0, 6))
        side.pack_propagate(False)                # the blocks' column keeps its width: the module gets the rest
        ttk.Label(side, text="Blocks - drag one into the module, or click it", font=("", 9, "bold"),
                  wraplength=240).pack(anchor="w")
        self.pal = ScrollFrame(side)
        self.pal.pack(fill="both", expand=True)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(right, highlightthickness=0, background=theme.palette()["field"])
        sy = ttk.Scrollbar(right, orient="vertical", command=self.cv.yview)
        sx = ttk.Scrollbar(right, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        tip = ttk.Label(right, foreground=theme.palette()["muted"], wraplength=600, justify="left",
                        text="Drag a block by its %s to move it; take it out with its \u2715, by dragging it back to "
                             "the left, or with a right click on its %s." % (GRIP, GRIP))
        tip.pack(side="bottom", anchor="w", fill="x")
        tip.bind("<Configure>", lambda e: tip.configure(wraplength=max(120, e.width - 4)))   # never cut at the edge
        sx.pack(side="bottom", fill="x")
        self.cv.pack(fill="both", expand=True)
        wheel(self.cv, scroll_y(self.cv))
        self.palette()

    # ---- the blocks on the left ----
    def palette(self):
        inner = self.pal.inner
        for w in inner.winfo_children():
            w.destroy()

        def head(text):
            ttk.Label(inner, text=text, font=("", 9, "bold")).pack(anchor="w", pady=(8, 2))

        head("Events - WHEN (one per module)")
        for e in MB.EVENTS:
            self.chip(inner, "event", e.label, ("event", e.key))
        more = ttk.Button(inner, text="More events...", command=lambda: self._more())
        more.pack(anchor="w", pady=(2, 0))
        from .gui_util import tip
        tip(more, "Every event of the engines' own lists (REX and M2EX), with a search")
        head("Control")
        self.chip(inner, "control", "for each town / army / faction", ("each", None))
        self.chip(inner, "control", "if ... else", ("if", None))
        head("Conditions - IF")
        for p in MB.CONDITIONS:
            self.chip(inner, "cond", p.label, ("cond", p.key), part=p)
        head("Actions - DO / ELSE")
        for p in MB.ACTIONS:
            self.chip(inner, "act", p.label, ("act", p.key), part=p)

    def _more(self):
        from .gui_modbuilder import EnginePicker
        ev = self.b.event()
        EnginePicker(self.b, "events", self.b.set_engine_event,
                     current=ev.engine if ev and ev.key not in MB.EVENT else "")

    def chip(self, parent, kind, text, src, part=None):
        c = colour(kind)
        lbl = tk.Label(parent, text=text, bg=c, fg=theme.on_colour(c), padx=8, pady=3, anchor="w", cursor="hand2",
                       relief="raised", bd=1, wraplength=205, justify="left")     # never cut at the edge
        lbl.pack(anchor="w", fill="x", pady=1)
        self._draggable(lbl, ("new",) + src, text, c)
        if part is not None and part.help:
            from .gui_util import tip
            tip(lbl, part.help)
        return lbl

    # ---- the module on the right ----
    def render(self):
        b, cv = self.b, self.cv
        top = cv.yview()[0] if cv.winfo_exists() else 0
        cv.delete("all")
        for w in cv.winfo_children():
            w.destroy()
        self.zones = []
        r = b.recipe
        x, y = 10, 10
        # the WHEN hat: the builder's own WHEN block in the events' colour
        b.block_colours = {"when": colour("event")}
        try:
            hat = tk.Frame(cv, bg=colour("event"))
            b._when(hat, each=False)
        finally:
            b.block_colours = {}
        cv.create_window(x, y, window=hat, anchor="nw")
        h, w = self._size(hat)
        self.zones.append((x, y, x + max(w, 400), y + h, "event", None, 0))
        y += h + GAP
        each = r.get("each") or ""
        if each:
            y = self._each(x, y)
        else:
            y = self._body(x, y)
        cv.configure(scrollregion=(0, 0, max(cv.bbox("all")[2] + 20, 600), y + 60))
        cv.yview_moveto(top)

    def _size(self, frame):
        frame.update_idletasks()
        return frame.winfo_reqheight(), frame.winfo_reqwidth()

    def _cblock(self, x, y, header, inside, kind, bottom_words=""):
        """A C-shaped block at (x, y): header (a frame filled by the caller), then inside(x, y) -> the y after what it
        holds, drawn in the arm; the arm and the bottom bar under it. Returns the y below the block."""
        c = colour(kind)
        hwin = self.cv.create_window(x, y, window=header, anchor="nw")
        hh, hw = self._size(header)
        y2 = inside(x + ARM, y + hh + GAP)
        right = max(hw, self._widest(y + hh, y2) - x, 320)
        self.cv.itemconfigure(hwin, width=right)
        self.cv.create_rectangle(x, y + hh, x + ARM, y2, fill=c, outline="")
        self.cv.create_rectangle(x, y2, x + right, y2 + BAR, fill=c, outline="")
        for item in self.cv.find_withtag("cwide"):     # this C's 'else' bar as wide as the C
            x1, y1, _, y3 = self.cv.coords(item)
            if y + hh <= y1 <= y2:
                self.cv.coords(item, x1, y1, x + right, y3)
                self.cv.dtag(item, "cwide")
        if bottom_words:
            self.cv.create_text(x + 8, y2 + BAR // 2, text=bottom_words, anchor="w", fill=theme.on_colour(c),
                                font=("", 8), tags="words")
        self.cv.tag_raise("words")                  # the bars' words above every bar
        return y2 + BAR + GAP

    def _widest(self, y1, y2):
        """The right edge of what stands between y1 and y2."""
        right = 0
        for item in self.cv.find_overlapping(0, y1 + 1, 10000, y2 - 1):
            bx = self.cv.bbox(item)
            if bx:
                right = max(right, bx[2])
        return right

    def _each(self, x, y):
        c = colour("control")
        head = tk.Frame(self.cv, bg=c)
        row = tk.Frame(head, bg=c)
        row.pack(anchor="w", fill="x")
        self._grip(row, c, ("move", "each", 0), "for each")
        tk.Label(row, text="FOR EACH", bg=c, fg=theme.on_colour(c), font=("", 10, "bold")).pack(side="left")
        self.b.block_colours = {}
        self.b._each_row(head, c)
        return self._cblock(x, y, head, self._body, "control", "end of for each")

    def _body(self, x, y):
        r = self.b.recipe
        if r.get("ifs") or r.get("else"):
            return self._if(x, y)
        return self._stack(x, y, "dos")

    def _if(self, x, y):
        c = colour("control")
        cc = colour("cond")
        head = tk.Frame(self.cv, bg=c)
        row = tk.Frame(head, bg=c)
        row.pack(anchor="w", fill="x", padx=2, pady=(2, 0))
        self._grip(row, c, ("move", "if", 0), "if ... else")
        tk.Label(row, text="IF", bg=c, fg=theme.on_colour(c), font=("", 10, "bold")).pack(side="left")
        tk.Label(row, text="only when", bg=c, fg=theme.on_colour(c)).pack(side="left", padx=(6, 2))
        v = tk.StringVar(value=dict(MB.MATCH).get(self.b.recipe.get("match") or "all"))
        cb = ttk.Combobox(row, textvariable=v, values=[lab for _, lab in MB.MATCH], state="readonly",
                          width=max(len(lab) for _, lab in MB.MATCH) + 1)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.b.set_match(v.get()))
        hint(row, "All: every condition must be true (and). Any one: one is enough (or). None: no condition may "
                  "be true. 'not' turns one condition round.").pack(side="left")
        conds = []
        for i, it in enumerate(self.b.recipe.get("ifs") or []):
            box = tk.Frame(head, bg=cc, bd=1, relief="raised")
            box.pack(anchor="w", padx=(ARM, 6), pady=2, fill="x")
            self.b.item_row(box, cc, "ifs", i, it, grip=lambda r, n=i: self._grip(r, cc, ("move", "ifs", n),
                                                                                   self._label("ifs", n)), padx=2)
            conds.append(box)
        if not conds:
            tk.Label(head, text="drop a green condition here", bg=c, fg=theme.on_colour(c),
                     font=("", 8, "italic")).pack(anchor="w", padx=ARM, pady=(2, 4))
        else:
            tk.Frame(head, bg=c, height=4).pack()

        def inside(ix, iy):
            iy = self._stack(ix, iy, "dos")
            # the 'else' bar across the C, then the ELSE actions in the same arm
            self.cv.create_rectangle(ix - ARM, iy, ix - ARM + 320, iy + BAR, fill=c, outline="", tags="cwide")
            self.cv.create_text(ix - ARM + 8, iy + BAR // 2, text="ELSE - when the IF does not hold", anchor="w",
                                fill=theme.on_colour(c), font=("", 9, "bold"), tags="words")
            return self._stack(ix, iy + BAR + GAP, "else")
        yb = self._cblock(x, y, head, inside, "control", "end of if")
        # where a dragged condition goes: before each one, after the last (canvas y of the boxes)
        self.cv.update_idletasks()
        top = y
        for i, box in enumerate(conds):
            by = top + box.winfo_y()
            self.zones.append((x, by - 6, x + 600, by + 8, "ifs", "ifs", i))
        if conds:
            last = top + conds[-1].winfo_y() + conds[-1].winfo_height()
            self.zones.append((x, last - 6, x + 600, last + 10, "ifs", "ifs", len(conds)))
        else:
            self.zones.append((x, y, x + 600, y + head.winfo_height(), "ifs", "ifs", 0))
        return yb

    def _label(self, group, i):
        it = (self.b.recipe.get(group) or [])[i]
        part = MB.table_of(group).get(it.get("k"))
        return part.label if part else it.get("k", "")

    def _stack(self, x, y, group):
        """The actions of group as blocks one under another from (x, y); the places a dragged action may go."""
        items = self.b.recipe.get(group) or []
        c = colour("act")
        if not items:
            e = colour("empty")
            self.cv.create_rectangle(x, y, x + 300, y + 26, fill=e, outline=colour("act"), dash=(3, 2))
            self.cv.create_text(x + 8, y + 13, anchor="w", fill=theme.on_colour(e), font=("", 8, "italic"),
                                text="drop blue actions here" if group == "dos" else
                                "ELSE: drop actions here (or leave it empty)")
            self.zones.append((x, y - 4, x + 600, y + 30, "act", group, 0))
            return y + 26 + GAP
        for i, it in enumerate(items):
            box = tk.Frame(self.cv, bg=c, bd=1, relief="raised")
            self.b.item_row(box, c, group, i, it, grip=lambda r, n=i: self._grip(r, c, ("move", group, n),
                                                                                 self._label(group, n)), padx=2)
            self.cv.create_window(x, y, window=box, anchor="nw")
            h, _ = self._size(box)
            self.zones.append((x, y - 6, x + 600, y + 8, "act", group, i))
            y += h + GAP
        self.zones.append((x, y - 6, x + 600, y + 12, "act", group, len(items)))
        return y

    def _grip(self, row, c, src, text):
        g = tk.Label(row, text=GRIP, bg=c, fg=theme.on_colour(c), cursor="fleur", font=("", 12, "bold"), padx=2)
        g.pack(side="left")
        self._draggable(g, src, text, c)
        g.bind("<Button-3>", lambda e: self.take_out(src))
        from .gui_util import tip
        tip(g, "Drag to move it - drag it back to the blocks on the left (or right click) to take it out.")
        # taking a block out in sight (a tester found the right click only by guessing): a small x on the block
        x = tk.Label(row, text="\u2715", bg=c, fg=theme.on_colour(c), cursor="hand2", font=("", 9), padx=1)
        x.pack(side="left")
        x.bind("<ButtonRelease-1>", lambda e: self.take_out(src))
        tip(x, "Take this block out")
        return g

    # ---- dragging ----
    def _draggable(self, w, src, text, c):
        w.bind("<ButtonPress-1>", lambda e: self._start(e, src, text, c))
        w.bind("<B1-Motion>", self._move)
        w.bind("<ButtonRelease-1>", self._drop)

    def _start(self, e, src, text, c):
        self.drag = {"src": src, "text": text, "c": c, "x": e.x_root, "y": e.y_root, "moved": False, "ghost": None}

    def _move(self, e):
        d = self.drag
        if d is None:
            return
        if not d["moved"] and abs(e.x_root - d["x"]) + abs(e.y_root - d["y"]) < 6:
            return
        if not d["moved"]:
            d["moved"] = True
            g = tk.Toplevel(self)
            g.wm_overrideredirect(True)
            try:
                g.attributes("-alpha", 0.85)
            except tk.TclError:
                pass
            tk.Label(g, text=d["text"], bg=d["c"], fg=theme.on_colour(d["c"]), padx=8, pady=3, relief="raised",
                     bd=1).pack()
            d["ghost"] = g
        d["ghost"].wm_geometry("+%d+%d" % (e.x_root + 12, e.y_root + 6))
        self.cv.delete("drop_line")
        z = self._zone(e.x_root, e.y_root)
        if z is not None:
            x1, y1, x2, y2 = z[:4]
            mid = (y1 + y2) // 2 if z[4] in ("ifs", "act") and y2 - y1 < 20 else y1 + 2
            self.cv.create_line(x1, mid, x1 + 300, mid, fill="#ff3355", width=3, tags="drop_line")

    def _kind(self, src):
        """What a dragged block is: 'event', 'each', 'if', 'cond', 'act'."""
        if src[0] == "new":
            return src[1]
        return {"each": "each", "if": "if", "ifs": "cond"}.get(src[1], "act")

    def _zone(self, xr, yr, src=None):
        """The place under the pointer a block of the dragged kind may go, or None."""
        src = src or (self.drag or {}).get("src")
        if src is None:
            return None
        kind = self._kind(src)
        cx = self.cv.canvasx(xr - self.cv.winfo_rootx())
        cy = self.cv.canvasy(yr - self.cv.winfo_rooty())
        if not (0 <= xr - self.cv.winfo_rootx() <= self.cv.winfo_width() and
                0 <= yr - self.cv.winfo_rooty() <= self.cv.winfo_height()):
            return None
        want = {"cond": "ifs", "act": "act", "event": "event"}.get(kind)
        if want is None:
            return None
        hits = [z for z in self.zones if z[4] == want and z[0] <= cx <= z[2] and z[1] <= cy <= z[3]]
        if hits:
            return min(hits, key=lambda z: abs((z[1] + z[3]) / 2 - cy))
        return None

    def _over_palette(self, xr, yr):
        p = self.pal
        return p.winfo_rootx() <= xr <= p.winfo_rootx() + p.winfo_width() and \
            p.winfo_rooty() <= yr <= p.winfo_rooty() + p.winfo_height()

    def _drop(self, e):
        d, self.drag = self.drag, None
        self.cv.delete("drop_line")
        if d is None:
            return
        if d["ghost"] is not None:
            d["ghost"].destroy()
        src = d["src"]
        if not d["moved"]:
            if src[0] == "new":
                self.put(src, None)              # a click: in at the end
            return
        if src[0] == "move" and self._over_palette(e.x_root, e.y_root):
            self.take_out(src)
            return
        z = self._zone(e.x_root, e.y_root, src)
        inside = 0 <= e.x_root - self.cv.winfo_rootx() <= self.cv.winfo_width() and \
            0 <= e.y_root - self.cv.winfo_rooty() <= self.cv.winfo_height()
        if z is None and not inside:
            return                               # dropped outside the module: nothing changes
        if src[0] == "new":
            self.put(src, z, e)
        elif z is not None:
            self.move(src, z)

    # ---- what a drop does ----
    def _changes(self, act):
        """Run act() on the recipe's lists; the settings follow their lines to where they went (gone with them)."""
        r = self.b.recipe
        groups = ("ifs",) + MB.ACTION_GROUPS
        before = {g: list(r.get(g) or []) for g in groups}
        act()
        pos = {id(it): (g, n) for g in groups for n, it in enumerate(r.get(g) or [])}
        out = {}
        for path, label in (r.get("settings") or {}).items():
            g, n, name = path.split(".")
            try:
                it = before[g][int(n)]
            except (KeyError, IndexError, ValueError):
                continue
            if id(it) in pos:
                g2, n2 = pos[id(it)]
                out["%s.%d.%s" % (g2, n2, name)] = label
        r["settings"] = out
        self.b.changed = True
        self.b.rebuild()

    def put(self, src, z, e=None):
        """A new block from the left: an event becomes the WHEN, FOR EACH wraps the module, IF asks for its first
        condition, a condition / an action goes where it was dropped (at the end after a click)."""
        r, kind, key = self.b.recipe, src[1], src[2]
        if kind == "event":
            self.b.set_when(next(ev.label for ev in MB.EVENTS if ev.key == key))
        elif kind == "each":
            if not r.get("each"):
                self.b.set_each("each", "town")
        elif kind == "if":
            if not r.get("ifs"):
                self._first_condition(e)
        elif kind == "cond":
            at = z[6] if z else len(r.get("ifs") or [])
            self._changes(lambda: r.setdefault("ifs", []).insert(at, self.b._new_item("ifs", key)))
        elif kind == "act":
            g, at = (z[5], z[6]) if z else ("dos", len(r.get("dos") or []))
            self._changes(lambda: r.setdefault(g, []).insert(at, self.b._new_item(g, key)))

    def _first_condition(self, e):
        m = tk.Menu(self, tearoff=False)
        m.add_command(label="IF needs a condition - pick the first one:", state="disabled")
        for p in MB.CONDITIONS:
            m.add_command(label=p.label, command=lambda k=p.key: self.put(("new", "cond", k), None))
        x, y = (e.x_root, e.y_root) if e is not None else (self.winfo_rootx() + 300, self.winfo_rooty() + 100)
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def move(self, src, z):
        r = self.b.recipe
        g1, i1 = src[1], src[2]
        if g1 in ("each", "if"):
            return                               # the C-blocks stay where they are; drag them out to take them out
        g2, i2 = z[5], z[6]
        if (g1 == "ifs") != (g2 == "ifs"):
            return                               # a condition goes among conditions, an action among actions

        def act():
            it = r[g1].pop(i1)
            at = i2 - 1 if g1 == g2 and i2 > i1 else i2
            r.setdefault(g2, []).insert(at, it)
        self._changes(act)

    def take_out(self, src):
        r = self.b.recipe
        g, i = src[1], src[2]
        if g == "each":
            self.b.set_each("each", "")
            return
        if g == "if":
            if r.get("ifs") or r.get("else"):
                from .gui_util import ask
                if not ask("Module builder", "Take the IF out with its %d condition(s) and %d ELSE action(s)? The "
                           "DO actions stay." % (len(r.get("ifs") or []), len(r.get("else") or [])),
                           yes="Take it out", no="Keep it", danger=True, parent=self):
                    return
            self._changes(lambda: (r.__setitem__("ifs", []), r.__setitem__("else", [])))
            return
        self._changes(lambda: r[g].pop(i))
