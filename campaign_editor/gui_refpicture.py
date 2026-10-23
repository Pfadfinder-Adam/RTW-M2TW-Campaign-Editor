"""Reference picture... (under the map, beside Save picture...): the modder's own picture laid over the campaign map,
see-through, to trace by or to look at - refpicture.RefPicture holds it, MapView draws it. The window and the keys
on the map do the same things (PureRef's keys, refpicture.SHORTCUTS); each shows what the other did at once."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .gui_util import ShortHint
from . import refpicture

APP = "RTW & M2TW Campaign Editor"
PICTURES = [("Pictures", "*.png *.jpg *.jpeg *.bmp *.tga *.dds *.tif *.tiff *.gif *.webp"), ("All files", "*.*")]


def pick_picture(view):
    """Open a picture over the map (the button and Ctrl+I); True when one was opened."""
    if not view.cmap:
        return False
    path = filedialog.askopenfilename(parent=view.winfo_toplevel(), title="A picture to lay over the map",
                                      filetypes=PICTURES)
    if not path:
        return False
    try:
        view.ref.open(path, view.cmap.w, view.cmap.h)
    except (OSError, ValueError) as e:
        messagebox.showerror(APP, "%s cannot be read as a picture: %s" % (path, e), parent=view.winfo_toplevel())
        return False
    view.ref_changed()
    return True


class RefWindow(tk.Toplevel):
    """One per map view; closed = hidden settings stay (the picture stays on the map as it is)."""

    def __init__(self, view):
        super().__init__(view.winfo_toplevel())
        self.view, self.ref = view, view.ref
        self.title("Reference picture over the map")
        self.transient(view.winfo_toplevel())
        from .gui_util import window_body
        frm, bottom = window_body(self, 560, 640)
        top = view.winfo_toplevel()
        try:                                              # at the window's right, over the legend: the map stays seen
            self.geometry("+%d+%d" % (max(0, top.winfo_rootx() + top.winfo_width() - 580), top.winfo_rooty() + 110))
        except tk.TclError:
            pass
        ttk.Label(frm, text="A picture of your own over the map", font=("", 12, "bold")).pack(anchor="w")
        ShortHint(frm, text=(
            "Lay any picture over the campaign map - a real map of the land, a sketch, another mod's map - to trace "
            "the coasts, rivers and borders by, or to look at while you work. It is only shown in the editor: "
            "nothing of it is written into the mod. Where it lies, its size and how see-through it is are kept for "
            "this mod and campaign, so it is there again next time. The keys are PureRef's: whoever knows PureRef "
            "knows them (the list below); they work when the map has been clicked.")).pack(anchor="w", fill="x")
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Open a picture... (Ctrl+I)", command=lambda: pick_picture(view)).pack(side="left")
        self.b_remove = ttk.Button(row, text="Take it away", command=self._remove)
        self.b_remove.pack(side="left", padx=6)
        self.lbl_file = ttk.Label(frm, text="", foreground="#555", wraplength=500, justify="left")
        self.lbl_file.pack(anchor="w", fill="x", pady=(4, 0))

        self.v_shown = tk.BooleanVar()
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(row, text="Show it (Ctrl+Shift+Y)", variable=self.v_shown,
                        command=lambda: self._set(shown=self.v_shown.get())).pack(side="left")
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="How much of it shows").pack(side="left")
        self.v_opacity = tk.DoubleVar()
        self.scale = ttk.Scale(row, from_=refpicture.LEAST_OPACITY * 100, to=100, variable=self.v_opacity,
                               orient="horizontal", length=220, command=self._slid)
        self.scale.pack(side="left", padx=6)
        self.lbl_op = ttk.Label(row, text="", width=6)
        self.lbl_op.pack(side="left")
        ttk.Label(frm, text="Ctrl+Shift+= / Ctrl+Shift+- by 10 %, or Ctrl+Alt+Shift and drag on the map",
                  foreground="#555").pack(anchor="w")

        self.v_front = tk.BooleanVar()
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(10, 0))
        ttk.Radiobutton(row, text="Under the towns and armies (Down)", value=False, variable=self.v_front,
                        command=lambda: self._set(front=False)).pack(side="left")
        ttk.Radiobutton(row, text="Over them (Up)", value=True, variable=self.v_front,
                        command=lambda: self._set(front=True)).pack(side="left", padx=(10, 0))

        self.v_unlocked = tk.BooleanVar()
        ttk.Checkbutton(frm, text="Move and size it with the left button on the map (Alt+L)", variable=self.v_unlocked,
                        command=lambda: self._set(locked=not self.v_unlocked.get())).pack(anchor="w", pady=(10, 0))
        ttk.Label(frm, text="Drag = move (Shift: straight), Ctrl+Alt + drag = size. While it is on, the left button "
                            "moves the picture, not the map's towns and armies - take the tick off (Alt+L) to work on "
                            "the map again.", foreground="#555", wraplength=500, justify="left").pack(anchor="w", fill="x")
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(6, 0))
        ttk.Button(row, text="On the whole map (Ctrl+Shift+T)", command=lambda: self._do("fit")).pack(side="left")
        ttk.Button(row, text="Its own shape (Ctrl+Alt+Down)", command=lambda: self._do("own_shape")).pack(
            side="left", padx=6)

        grid = ttk.Frame(frm)
        grid.pack(anchor="w", pady=(8, 0))
        self.v_box, self.sp_box = {}, {}
        for i, (k, text) in enumerate((("x", "Left edge"), ("y", "Top edge"), ("w", "Width"), ("h", "Height"))):
            ttk.Label(grid, text=text).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=(0 if i % 2 == 0 else 14, 4))
            v = tk.StringVar()
            sp = ttk.Spinbox(grid, textvariable=v, from_=-100000, to=100000, increment=1, width=9,
                             command=self._typed)
            sp.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", pady=2)
            sp.bind("<Return>", lambda e: self._typed())
            sp.bind("<FocusOut>", lambda e: self._typed())
            self.v_box[k], self.sp_box[k] = v, sp
        ttk.Label(frm, text="In tiles: the left edge counted from the map's left, the top edge from its top row.",
                  foreground="#555").pack(anchor="w")

        self.v_fh, self.v_fv, self.v_grey, self.v_smooth = (tk.BooleanVar() for _ in range(4))
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(10, 0))
        for var, text, key in ((self.v_fh, "Mirror left-right (Alt+Shift+H)", "flip_h"),
                               (self.v_fv, "Upside down (Alt+Shift+V)", "flip_v")):
            ttk.Checkbutton(row, text=text, variable=var,
                            command=lambda var=var, key=key: self._set(**{key: var.get()})).pack(side="left", padx=(0, 10))
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(4, 0))
        for var, text, key in ((self.v_grey, "Grey (Alt+G)", "grey"), (self.v_smooth, "Smooth (Alt+T)", "smooth")):
            ttk.Checkbutton(row, text=text, variable=var,
                            command=lambda var=var, key=key: self._set(**{key: var.get()})).pack(side="left", padx=(0, 10))

        ttk.Label(frm, text="The keys (PureRef's own)", font=("", 10, "bold")).pack(anchor="w", pady=(12, 2))
        keys = ttk.Frame(frm)
        keys.pack(anchor="w", fill="x")
        for i, (k, what, _pure) in enumerate(refpicture.SHORTCUTS):
            ttk.Label(keys, text=k, font=("", 9, "bold")).grid(row=i, column=0, sticky="w", padx=(0, 10))
            ttk.Label(keys, text=what).grid(row=i, column=1, sticky="w")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")
        self.bind("<KeyPress>", view._ref_key)            # the same keys in the window as on the map
        self.sync()

    def sync(self):
        """The window shows the picture as it is now (after a key or a drag on the map)."""
        r = self.ref
        has = r.loaded()
        self.lbl_file.configure(text=("%s - %d x %d pixels" % (os.path.basename(r.path), r.src.width, r.src.height))
                                if has else "No picture yet: open one.")
        self.b_remove.configure(state="normal" if has else "disabled")
        self.v_shown.set(r.shown)
        self.v_opacity.set(round(r.opacity * 100))
        self.lbl_op.configure(text="%d %%" % round(r.opacity * 100))
        self.v_front.set(r.front)
        self.v_unlocked.set(not r.locked)
        for k, v in self.v_box.items():
            if self.focus_get() is not self.sp_box[k]:          # not under the modder's typing
                v.set(("%.1f" % getattr(r, k)).rstrip("0").rstrip("."))
        self.v_fh.set(r.flip_h)
        self.v_fv.set(r.flip_v)
        self.v_grey.set(r.grey)
        self.v_smooth.set(r.smooth)

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self.ref, k, v)
        self.view.ref_changed()

    def _do(self, action):
        self.view.ref_action(action)

    def _slid(self, v):
        self.ref.set_opacity(float(v) / 100.0)
        self.lbl_op.configure(text="%d %%" % round(self.ref.opacity * 100))
        self.view.ref_changed(sync=False)

    def _typed(self):
        r = self.ref
        try:
            vals = {k: float(v.get().replace(",", ".")) for k, v in self.v_box.items()}
        except ValueError:
            return self.sync()
        if vals["w"] <= 0 or vals["h"] <= 0:
            return self.sync()
        if any(abs(vals[k] - getattr(r, k)) > 1e-6 for k in vals):
            for k, v in vals.items():
                setattr(r, k, v)
            self.view.ref_changed()

    def _remove(self):
        self.ref.clear()
        self.view.ref_changed()


def open_window(view):
    w = getattr(view, "_ref_win", None)
    if w is not None and w.winfo_exists():
        w.deiconify()
        w.lift()
        return w
    view._ref_win = RefWindow(view)
    return view._ref_win
