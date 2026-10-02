"""The window of a wonder, as the game's own scroll shows it when one double-clicks it on the campaign map: its
picture, title, what it does, its short and long description - and its campaign-map model in 3D (wonders.py)."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import wonders as W


def show(parent, mod, kind):
    w_info = W.info(mod, kind)
    w = tk.Toplevel(parent)
    w.title("Wonder - %s" % w_info["title"])
    w.transient(parent.winfo_toplevel())
    frm = ttk.Frame(w, padding=10)
    frm.pack(fill="both", expand=True)
    top = ttk.Frame(frm)
    top.pack(fill="x")
    pic = tk.Label(top)
    pic.pack(side="left", anchor="n")
    if w_info["image"]:
        try:
            from PIL import Image, ImageTk
            with Image.open(w_info["image"]) as im:
                im = im.convert("RGBA")
                im.thumbnail((360, 260))
                w._ph = ImageTk.PhotoImage(im)
            pic.configure(image=w._ph)
        except Exception:
            pic.configure(text="(the picture cannot be read)")
    else:
        pic.configure(text="(no picture)")
    side = ttk.Frame(top, padding=(12, 0))
    side.pack(side="left", fill="both", expand=True)
    ttk.Label(side, text=w_info["title"], font=("", 13, "bold"), wraplength=380).pack(anchor="w")
    if w_info["effects"]:
        ttk.Label(side, text=w_info["effects"], wraplength=380, justify="left",
                  font=("", 10, "bold")).pack(anchor="w", pady=(6, 0))
    if w_info["short"]:
        ttk.Label(side, text=w_info["short"], wraplength=380, justify="left").pack(anchor="w", pady=(6, 0))
    bb = ttk.Frame(side)
    bb.pack(anchor="w", pady=(10, 0))

    def view():
        from .gui_meshview import ModelViewer
        mi = W.model_info(mod, kind)
        if mi is None:
            messagebox.showinfo("Wonder", "%s names no model (item) in descr_sm_landmarks.txt." % kind, parent=w)
            return
        ModelViewer(w, mod, mi, title="Wonder on the campaign map, in 3D")
    ttk.Button(bb, text="View in 3D", command=view).pack(side="left")
    if w_info["long"]:
        t = tk.Text(frm, height=10, width=80, wrap="word", font="TkDefaultFont")
        t.insert("1.0", w_info["long"])
        t.configure(state="disabled")
        t.pack(fill="both", expand=True, pady=(10, 0))
    ttk.Label(frm, foreground="#666", justify="left", wraplength=640, text=(
        "type %s - model %s, picture %s; texts in text/landmarks.txt (%s_title, _short_descr, _long_descr, "
        "_effects). What it does is the game's own for this type: the game knows these seven wonders only."
        % (kind, w_info["item"] or "-", w_info["image"] and "ui/wonders" or "-", kind))).pack(anchor="w",
                                                                                           pady=(8, 0))
    ttk.Button(frm, text="Close", command=w.destroy).pack(anchor="e", pady=(8, 0))
    return w
