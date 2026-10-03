"""The Send a report window: a problem or an idea (a suggestion), a few words of what happened or what is wished, the logs found (ticked), pictures the user picks, words to
hide - Show what is sent, Save as zip, Send. The texts are anonymised by report.scrub before they are shown, saved or
sent; nothing leaves without the Send button."""

import datetime
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import log, report, settings

APP = "RTW & M2TW Campaign Editor"


def open_report(app, message="", kind="bug", tab=None):
    """tab 'answers' opens on Answers to my reports (the Report button does when one came)."""
    game = mod_dir = None
    if app.mod:
        from .newmod import game_of
        game = game_of(app.mod.data)
        mod_dir = os.path.dirname(os.path.abspath(app.mod.data))
    files = report.found(game, mod_dir)
    pictures = []

    w = tk.Toplevel(app)
    w.title("Report a bug or suggest an idea")
    w.transient(app)
    nb = ttk.Notebook(w)
    nb.pack(fill="both", expand=True)
    frm = ttk.Frame(nb, padding=10)
    nb.add(frm, text="Send a report or an idea")
    ttk.Label(frm, justify="left", wraplength=620, text=(
        "Sends a problem or an idea to the editor's author - no account needed. A problem takes the logs along, "
        "with anything that could tell who you are cut out. 'Show what is sent' shows it all. "
        "Nothing is sent before you press Send.")).pack(anchor="w")

    v_kind = tk.StringVar(value=kind)
    kinds = ttk.Frame(frm)
    kinds.pack(anchor="w", pady=(10, 0))
    ttk.Label(kinds, text="It is").pack(side="left")
    ttk.Radiobutton(kinds, text="a problem (a bug, a crash, something confusing)", value="bug", variable=v_kind,
                    command=lambda: kind_changed()).pack(side="left", padx=6)
    ttk.Radiobutton(kinds, text="an idea (a suggestion, a wish)", value="suggestion", variable=v_kind,
                    command=lambda: kind_changed()).pack(side="left")
    PROMPTS = {"bug": "What happened? (what you did, what you expected, what the game or the editor did)",
               "suggestion": "Your idea: what should the editor do, and what would it help you with?"}
    lbl_prompt = ttk.Label(frm, text=PROMPTS[kind])
    lbl_prompt.pack(anchor="w", pady=(6, 2))
    txt = tk.Text(frm, width=70, height=6, wrap="word")
    txt.pack(fill="x")
    if message:
        txt.insert("1.0", message)

    grid = ttk.Frame(frm)
    grid.pack(fill="x", pady=(8, 0))
    v_contact = tk.StringVar(value=settings.get("report_contact", ""))
    v_hide = tk.StringVar(value=settings.get("report_hide", ""))
    ttk.Label(grid, text="Contact for questions (optional)").grid(row=0, column=0, sticky="w")
    ttk.Entry(grid, textvariable=v_contact, width=40).grid(row=0, column=1, sticky="w", padx=6)
    # remembered for every next report (a tester: 'save our contact so each report fills it in') - also in Settings
    v_keep = tk.BooleanVar(value=settings.get("report_contact_keep", True) is not False)
    keep_row = ttk.Frame(grid)
    keep_row.grid(row=1, column=1, sticky="w", padx=6)
    ttk.Checkbutton(keep_row, text="remember it - every next report fills it in by itself", variable=v_keep).pack(
        side="left")
    ttk.Label(keep_row, text="(only if you want an answer; also in Settings)", foreground="#666").pack(
        side="left", padx=4)
    ttk.Label(grid, text="Hide also these words").grid(row=2, column=0, sticky="w", pady=(4, 0))
    ttk.Entry(grid, textvariable=v_hide, width=40).grid(row=2, column=1, sticky="w", padx=6, pady=(4, 0))
    ttk.Label(grid, text="a comma between them: your nick in the game, your real name...", foreground="#666").grid(
        row=3, column=1, sticky="w", padx=6)

    box = ttk.LabelFrame(frm, text="What goes with it", padding=6)
    box.pack(fill="x", pady=(10, 0))
    ticks = []
    for f, name, what in files:
        v = tk.BooleanVar(value=True)              # the logs always go along (an idea too) - untick to leave out
        ticks.append((v, (f, name, what)))
        ttk.Checkbutton(box, variable=v, text="%s - %s (%d KB)" % (name, what, os.path.getsize(f) // 1024)).pack(
            anchor="w")
    if not any(n.endswith("system.log.txt") for _, n, _ in files):
        row = ttk.Frame(box)
        row.pack(anchor="w", fill="x")
        ttk.Label(row, foreground="#a60", text="No system.log.txt of the game found%s - without it a game crash is "
                  "guesswork." % (" (load the mod first)" if not app.mod and not game else
                                  " in %s or its mods" % (game or settings.get("game") or "the game folder"))
                  ).pack(side="left")
        ttk.Button(row, text="How to switch the game's log on",
                   command=lambda: messagebox.showinfo(APP, report.LOG_HOWTO, parent=w)).pack(side="left", padx=6)
    def kind_changed():
        lbl_prompt.configure(text=PROMPTS[v_kind.get()])
    lbl_pics = ttk.Label(box, foreground="#666", text="No pictures.")
    lbl_pics.pack(anchor="w", pady=(4, 0))

    def add_pictures():
        picked = filedialog.askopenfilenames(parent=w, title="Pictures for the report (up to %d)" % report.PICTURES,
                                             filetypes=[("Pictures", " ".join("*" + e for e in report.PICTURE_EXT))])
        for p in picked:
            why = report.picture_problem(p)
            if why:
                messagebox.showerror(APP, why, parent=w)
            elif p not in pictures and len(pictures) < report.PICTURES:
                pictures.append(p)
        lbl_pics.configure(text=("Pictures: " + ", ".join(os.path.basename(p) for p in pictures)) if pictures
                           else "No pictures.")
    def paste_picture(ev=None):
        """A screenshot from the clipboard (Ctrl+V; Win+Shift+S / PrintScreen first) - saved as a PNG beside the
        logs and added like a picked one."""
        try:
            from PIL import ImageGrab
            got = ImageGrab.grabclipboard()
        except Exception:
            got = None
        paths = []
        if isinstance(got, list):                     # files copied in Explorer
            paths = [p for p in got if str(p).lower().endswith(report.PICTURE_EXT)]
        elif got is not None and hasattr(got, "save"):
            folder = os.path.join(log.logs_dir() or os.path.expanduser("~"), "pasted")
            try:
                os.makedirs(folder, exist_ok=True)
                p = os.path.join(folder, "screenshot_%s.png" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
                got.save(p)
                paths = [p]
            except Exception as e:
                messagebox.showerror(APP, "The picture from the clipboard could not be kept: %s" % e, parent=w)
                return "break"
        if not paths:
            if ev is None:
                messagebox.showinfo(APP, "No picture in the clipboard. Take a screenshot first (Win+Shift+S or "
                                         "PrintScreen), then Ctrl+V here.", parent=w)
            return None                               # plain text: pasted as usual
        for p in paths:
            why = report.picture_problem(p)
            if why:
                messagebox.showerror(APP, why, parent=w)
            elif p not in pictures and len(pictures) < report.PICTURES:
                pictures.append(p)
        lbl_pics.configure(text=("Pictures: " + ", ".join(os.path.basename(p) for p in pictures)) if pictures
                           else "No pictures.")
        return "break"
    pics_row = ttk.Frame(box)
    pics_row.pack(anchor="w", pady=(4, 0))
    ttk.Button(pics_row, text="Add a screenshot...", command=add_pictures).pack(side="left")
    ttk.Button(pics_row, text="Paste a screenshot (Ctrl+V)", command=paste_picture).pack(side="left", padx=6)
    w.bind("<Control-v>", paste_picture)
    w.bind("<Control-V>", paste_picture)

    def words():
        return [x.strip() for x in v_hide.get().split(",") if x.strip()]

    def gather():
        picked = [f for v, f in ticks if v.get()]
        hide = report.hidden_words(picked, words())
        texts = report.contents(picked, hide)
        info = dict(kind=v_kind.get(), **report.about(app.mod, _version()))
        msg = txt.get("1.0", "end").strip()
        data = report.build_zip(texts, msg, v_contact.get(), info, pictures, hide)
        return texts, info, msg, hide, data

    def remember():
        settings.put("report_contact_keep", bool(v_keep.get()))
        settings.put("report_contact", v_contact.get().strip() if v_keep.get() else "")
        settings.put("report_hide", v_hide.get().strip())

    def show():
        texts, info, msg, hide, data = gather()
        parts = ["report.txt", "=" * 60, zip_text(data, "report.txt")]
        for name, text in texts:
            parts += ["", name, "=" * 60, text if len(text) < 200000 else
                      "[... %d KB before this ...]\n" % ((len(text) - 200000) // 1024) + text[-200000:]]
        parts += ["", "pictures: %s" % (", ".join(os.path.basename(p) for p in pictures) or "none"),
                  "", "zip: %d KB" % (len(data) // 1024)]
        app.show_text("What is sent - with the names cut out", "\n".join(parts))

    def save_zip():
        remember()
        _, _, _, _, data = gather()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = filedialog.asksaveasfilename(parent=w, title="Save the report", defaultextension=".zip",
                                           initialdir=log.logs_dir() or "", initialfile="report_%s.zip" % stamp,
                                           filetypes=[("Zip", "*.zip")])
        if not out:
            return
        try:
            with open(out, "wb") as fh:
                fh.write(data)
        except OSError as e:
            messagebox.showerror(APP, "Could not write %s: %s" % (out, e), parent=w)
            return
        log.write("Report saved to %s" % out)
        messagebox.showinfo(APP, "Saved %s\n\nSend it on Discord or GitHub." % out, parent=w)

    def send():
        texts, info, msg, hide, data = gather()
        if not msg:
            if v_kind.get() == "suggestion":
                messagebox.showerror(APP, "Write your idea first - a few words are enough.", parent=w)
                return
            if not messagebox.askyesno(APP, "Nothing written under 'What happened?' - a report with a few words is "
                                            "much easier to fix. Send it anyway?", parent=w):
                return
        remember()
        b_send.configure(state="disabled")
        lbl_state.configure(text="Sending...")
        result = {}

        def work():
            try:
                result["id"], result["issue"] = report.send(
                    data, ("Idea: " if info["kind"] == "suggestion" else "Bug: ") + report.scrub(msg, hide),
                    v_contact.get().strip(), info, full=True)
            except Exception as e:           # RuntimeError in plain words; anything else still shown
                result["error"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def wait():
            if th.is_alive():
                w.after(200, wait)
                return
            b_send.configure(state="normal")
            if "id" in result:
                log.write("Report sent: %s (%d KB)" % (result["id"], len(data) // 1024))
                report.remember_sent(result["id"], result.get("issue"), info["kind"],
                                     report.scrub(msg, hide).split("\n")[0])
                lbl_state.configure(text="Sent: %s" % result["id"])
                messagebox.showinfo(APP, "Sent - thank you! Your report's number is %s.\n\nThe author's answer "
                                         "comes to this window, tab 'Answers to my reports' - the Report button "
                                         "shows when one came." % result["id"], parent=w)
                w.destroy()
            else:
                log.write("Report not sent: %s" % result["error"])
                lbl_state.configure(text="")
                if messagebox.askyesno(APP, "The report was not sent: %s.\n\nSave it as a zip instead (to send on "
                                            "Discord or GitHub)?" % result["error"], parent=w):
                    save_zip()
        wait()

    bar = ttk.Frame(frm)
    bar.pack(fill="x", pady=(10, 0))
    lbl_state = ttk.Label(bar, foreground="#666")
    lbl_state.pack(side="left")
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="right")
    b_send = ttk.Button(bar, text="Send", command=send)
    b_send.pack(side="right", padx=4)
    ttk.Button(bar, text="Save as zip...", command=save_zip).pack(side="right")
    ttk.Button(bar, text="Show what is sent", command=show).pack(side="right", padx=4)
    if not report.url():
        lbl_state.configure(text="The report service is not set up in this version yet - Save as zip works.",
                            foreground="#a60")
    from .gui_answers import build_tab, show_count
    tab_answers, _check = build_tab(app, nb, w)
    n = show_count(app)
    nb.add(tab_answers, text="Answers to my reports" + (" (%d new)" % n if n else ""))
    if tab == "answers" or (tab is None and n and not message):
        nb.select(tab_answers)
    return w


def zip_text(data, name):
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read(name).decode("utf-8")


def _version():
    from .gui import VERSION
    return VERSION
