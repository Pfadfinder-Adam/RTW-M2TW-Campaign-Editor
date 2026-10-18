"""The Send a report window: a problem or an idea (a suggestion), a few words of what happened or what is wished, the logs found (ticked), pictures the user picks, words to
hide - Show what is sent, Save as zip, Send. The texts are anonymised by report.scrub before they are shown, saved or
sent; nothing leaves without the Send button."""

import datetime
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .gui_util import ask, one_line
from . import log, report, settings

APP = "RTW & M2TW Campaign Editor"



SEND_LIMIT = 90                 # seconds without an answer before the report is given up (then: save the zip)

def snap_window(widget, path):
    """A picture of the editor's own window as it stands (Windows: PrintWindow - this window only, even under
    another one; nothing else of the screen) saved as path; True when made. Anywhere else, or on any trouble:
    False, nothing made (the user, 2026-10-18: 'a screenshot of the program alone')."""
    import sys
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image
        u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
        hwnd = u32.GetParent(widget.winfo_toplevel().winfo_id()) or widget.winfo_toplevel().winfo_id()
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w <= 0 or h <= 0:
            return False
        src = u32.GetWindowDC(hwnd)
        dc = g32.CreateCompatibleDC(src)
        bmp = g32.CreateCompatibleBitmap(src, w, h)
        g32.SelectObject(dc, bmp)
        ok = u32.PrintWindow(hwnd, dc, 2)                  # PW_RENDERFULLCONTENT
        buf = ctypes.create_string_buffer(w * h * 4)

        class BMI(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("w", wintypes.LONG), ("h", wintypes.LONG),
                        ("planes", wintypes.WORD), ("bits", wintypes.WORD), ("comp", wintypes.DWORD),
                        ("img", wintypes.DWORD), ("xpm", wintypes.LONG), ("ypm", wintypes.LONG),
                        ("used", wintypes.DWORD), ("imp", wintypes.DWORD)]
        bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)    # top row first
        got = g32.GetDIBits(dc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
        g32.DeleteObject(bmp)
        g32.DeleteDC(dc)
        u32.ReleaseDC(hwnd, src)
        if not ok or not got:
            return False
        Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1).save(path)
        return True
    except Exception:
        return False


def open_report(app, message="", kind="bug", tab=None):
    """tab 'answers' opens on Answers to my reports (the Report button does when one came)."""
    game = mod_dir = None
    if app.mod:
        from .newmod import game_of
        game = game_of(app.mod.data)
        mod_dir = os.path.dirname(os.path.abspath(app.mod.data))
    files = report.found(game, mod_dir)
    pictures = []
    # the editor's window as it is now - before this window covers it (an error box of the editor too)
    shot = os.path.join(log.logs_dir() or os.path.expanduser("~"), "editor_window.png")
    if kind == "bug" and snap_window(app, shot):
        pictures.append(shot)

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
    # the crash doctor's word on the game's last run, in sight and on the report's first line (the user,
    # 2026-10-18: 'what happened, on the first line, so it is seen at once')
    said = report.doctor(files)
    if said:
        ttk.Label(frm, text="The game's log says: " + said, wraplength=620, justify="left",
                  font=("", 9, "bold")).pack(anchor="w", pady=(6, 0))

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
    # the box grows with the window and by its grip under it (report #176: 'make the text window resizable')
    txt = tk.Text(frm, width=70, height=6, wrap="word")
    txt.pack(fill="both", expand=True)
    if message:
        txt.insert("1.0", message)
    grip = ttk.Frame(frm, height=7, cursor="sb_v_double_arrow")
    grip.pack(fill="x")
    held = {}

    def grip_press(ev):
        held.update(y=ev.y_root, lines=int(txt.cget("height")))

    def grip_drag(ev):
        if not held:
            return
        import tkinter.font as tkfont
        step = max(1, tkfont.Font(font=txt.cget("font")).metrics("linespace"))
        txt.configure(height=max(3, min(60, held["lines"] + (ev.y_root - held["y"]) // step)))
    grip.bind("<ButtonPress-1>", grip_press)
    grip.bind("<B1-Motion>", grip_drag)
    w.resizable(True, True)

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
        sent = report.already_sent(f)
        # the logs go along (an idea too) - untick to leave out; one already sent unchanged stays out (a tester's wish)
        v = tk.BooleanVar(value=not sent)
        ticks.append((v, (f, name, what)))
        # one line each - what does not fit hides behind '...', the whole line on hover (a tester, R-20261014-AE0007)
        one_line(ttk.Checkbutton(box, variable=v, width=1), "%s - %s (%s)%s" % (
            name, what, report.size_words(os.path.getsize(f)), " - already sent with %s, not changed since" % sent
            if sent else ""), extra=28, anchor="w")
    # the mod's file list (names, sizes, dates - no contents): what the mod has and changes against the game
    files_sent = report.files_sent(app.mod)        # sent already, the mod not written since: stays out (#269)
    v_files = tk.BooleanVar(value=app.mod is not None and not files_sent)
    if app.mod is not None:
        one_line(ttk.Checkbutton(box, variable=v_files, width=1), "%s - the list of the mod's files: name, size, "
                 "date, new / other size than the game's (no contents)%s" % (
                     report.MOD_FILES, " - already sent with %s, the mod not changed since" % files_sent
                     if files_sent else ""), extra=28, anchor="w")
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
    lbl_pics = ttk.Label(box, foreground="#666", text=(
        "Pictures: %s (the editor's window as it was)" % os.path.basename(shot)) if pictures else "No pictures.",
        wraplength=620, justify="left")                     # many names: more lines, never a wider window
    lbl_pics.pack(anchor="w", pady=(4, 0))
    if shot in pictures:                                   # the opposite in the same place: it can stay out
        def drop_shot():
            if shot in pictures:
                pictures.remove(shot)
            lbl_pics.configure(text=("Pictures: " + ", ".join(os.path.basename(p) for p in pictures))
                               if pictures else "No pictures.")
            b_drop.destroy()
        b_drop = ttk.Button(box, text="Leave the window's picture out", command=drop_shot)
        b_drop.pack(anchor="w")

    def add_pictures():
        picked = filedialog.askopenfilenames(parent=w, title="Pictures for the report (up to %d)" % report.PICTURES,
                                             filetypes=[("Pictures", " ".join("*" + e for e in report.PICTURE_EXT))])
        for p in picked:
            why = report.picture_problem(p)
            if why:
                messagebox.showerror(APP, why, parent=w)
            elif p not in pictures and len(pictures) < report.PICTURES:
                pictures.append(p)
            elif p not in pictures:
                messagebox.showinfo(APP, "Up to %d pictures go with one report - %s and the ones after it were left "
                                         "out. Send the rest in another report." % (report.PICTURES,
                                                                                     os.path.basename(p)), parent=w)
                break
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
            elif p not in pictures:
                messagebox.showinfo(APP, "Up to %d pictures go with one report - %s and the ones after it were left "
                                         "out. Send the rest in another report." % (report.PICTURES,
                                                                                     os.path.basename(p)), parent=w)
                break
        lbl_pics.configure(text=("Pictures: " + ", ".join(os.path.basename(p) for p in pictures)) if pictures
                           else "No pictures.")
        return "break"
    pics_row = ttk.Frame(box)
    pics_row.pack(anchor="w", pady=(4, 0))
    ttk.Button(pics_row, text="Add a screenshot...", command=add_pictures).pack(side="left")
    ttk.Button(pics_row, text="Paste a screenshot (Ctrl+V)", command=paste_picture).pack(side="left", padx=6)
    w.bind("<Control-v>", paste_picture)
    w.bind("<Control-V>", paste_picture)
    w.bind("<Control-KeyPress>", lambda e: paste_picture(e) if e.keycode == 86 and not (
        len(e.keysym) == 1 and e.keysym.isascii()) else None)       # Ctrl+V in a non-Latin keyboard layout

    def words():
        return [x.strip() for x in v_hide.get().split(",") if x.strip()]

    def read_window():
        """What the window holds (read on Tk's own thread)."""
        return dict(picked=[f for v, f in ticks if v.get()], words=words(), files=v_files.get(), kind=v_kind.get(),
                    msg=txt.get("1.0", "end").strip(), contact=v_contact.get())

    def pack(ui):
        """The logs cut, the mod's file list and the zip - the slow part (a big mod's 30 000 files: seconds), so Send
        runs it beside the window (a tester: 'a pause like a hang after Send', R-20261014-C76F52)."""
        hide = report.hidden_words(ui["picked"], ui["words"])
        texts = report.contents(ui["picked"], hide)
        listing = report.mod_files(app.mod, hide) if ui["files"] else None
        if listing:
            texts.append((report.MOD_FILES, listing))
        info = dict(kind=ui["kind"], **report.about(app.mod, _version()))
        data = report.build_zip(texts, ui["msg"], ui["contact"], info, pictures, hide, doctor=said)
        return texts, info, ui["msg"], hide, data

    def gather():
        return pack(read_window())

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
        ui = read_window()
        msg = ui["msg"]
        if not msg:
            if ui["kind"] == "suggestion":
                messagebox.showerror(APP, "Write your idea first - a few words are enough.", parent=w)
                return
            if not ask(APP, "Nothing written under 'What happened?' - a report with a few words is "
                                            "much easier to fix. Send it anyway?", parent=w, yes='Send it anyway', no='Write a few words'):
                return
        remember()
        b_send.configure(state="disabled")
        lbl_state.configure(text="Packing the logs...")
        result = {}

        def work():
            try:
                result["packed"] = _, info, _, hide, data = pack(ui)
                result["sending"] = True
                result["id"], result["issue"] = report.send(
                    data, ("Idea: " if info["kind"] == "suggestion" else "Bug: ") + report.scrub(
                        ("The game's log says: %s\n\n" % said if said and info["kind"] != "suggestion" else "") + msg,
                        hide),
                    ui["contact"].strip(), info, full=True, timeout=SEND_LIMIT)
            except Exception as e:           # RuntimeError in plain words; anything else still shown
                result["error"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()
        import time
        started = time.monotonic()

        def wait():
            if th.is_alive():                # the seconds go on: it is working, not stuck (a report with pictures
                n = int(time.monotonic() - started)     # takes up to a minute - the user thought it hung)
                lbl_state.configure(text="Sending... %d s (up to a minute with pictures; it gives up after %d s)"
                                    % (n, SEND_LIMIT) if result.get("sending") else
                                    "Packing the logs... %d s" % n)
                w.after(500, wait)
                return
            b_send.configure(state="normal")
            if "packed" in result:
                _, info, _, hide, data = result["packed"]
            if "id" in result:
                log.write("Report sent: %s (%d KB)" % (result["id"], len(data) // 1024))
                report.remember_sent(result["id"], result.get("issue"), info["kind"],
                                     report.scrub(msg, hide).split("\n")[0])
                report.remember_sent_logs([fl for v, fl in ticks if v.get()], result["id"])
                if v_files.get() and app.mod is not None:
                    report.remember_files_sent(app.mod, result["id"])
                lbl_state.configure(text="Sent: %s" % result["id"])
                messagebox.showinfo(APP, "Sent - thank you! Your report's number is %s.\n\nThe author's answer "
                                         "comes to this window, tab 'Answers to my reports' - the Report button "
                                         "shows when one came." % result["id"], parent=w)
                w.destroy()
            else:
                log.write("Report not sent: %s" % result["error"])
                lbl_state.configure(text="")
                if ask(APP, "The report was not sent: %s.\n\nSave it as a zip instead (to send on "
                                            "Discord or GitHub)?" % result["error"], parent=w, yes='Save as a zip...', no='Not now'):
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
