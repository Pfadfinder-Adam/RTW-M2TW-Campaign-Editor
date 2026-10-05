"""Answers to my reports: the second tab of the Report window. The author answers a report on GitHub (a comment, or
closes it as fixed / not planned); the reporter cannot see the private reports repo, so the editor asks the relay for
the answers to the reports it sent (report.answers) - on start every few hours (check_on_start) and with Check now.
A new answer puts a count on the Report button and a line in the status bar; Send the answer adds the reporter's
words (and new screenshots / logs) to the same report (report.send_reply)."""

import datetime
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import log, report, settings, theme

APP = "RTW & M2TW Campaign Editor"
REPORT_BUTTON = "Report a bug / Suggest"


def _version():
    from .gui import VERSION
    return VERSION


def _fetch(app, done, timeout=30):
    """Ask the relay in a thread; done(answers or None, error or None) runs in the window's thread."""
    rows = report.sent_reports()
    if not rows or not report.url():
        done({}, None)
        return
    result = {}

    def work():
        try:
            result["a"] = report.answers(rows, _version(), timeout)
        except Exception as e:                 # RuntimeError in plain words; anything else still shown
            result["e"] = str(e)
    th = threading.Thread(target=work, daemon=True)
    th.start()

    def wait():
        if th.is_alive():
            app.after(300, wait)
            return
        if "a" in result:
            app._report_answers = result["a"]
            settings.put("reports_checked_at", time.time())
        done(result.get("a"), result.get("e"))
    wait()


def show_count(app):
    """The Report button says how many reports have a new answer."""
    n = len(report.news(getattr(app, "_report_answers", {}), settings.get("reports_seen") or {}))
    b = getattr(app, "b_report", None)
    if b is not None:
        try:
            b.configure(text=REPORT_BUTTON + (" (%d new)" % n if n else ""))
        except tk.TclError:
            pass
    return n


def check_on_start(app):
    """Once in report.CHECK_EVERY seconds, when this editor ever sent a report: ask for answers quietly (no message
    when offline); a new one -> the count on the Report button and a line in the status bar."""
    if settings.get("reports_check", True) is False:
        return
    try:
        last = float(settings.get("reports_checked_at") or 0)
    except (TypeError, ValueError):
        last = 0
    if time.time() - last < report.CHECK_EVERY or not report.sent_reports():
        return

    def done(answers, error):
        if error:
            log.write("Answers to my reports not checked: %s" % error)
            return
        new = report.news(answers, settings.get("reports_seen") or {})
        show_count(app)
        if new:
            log.write("Answers to my reports: new for %s" % ", ".join(new))
            app.status.set("An answer came to your report %s - press '%s' to read it." % (
                ", ".join(new[:3]) + (" ..." if len(new) > 3 else ""), REPORT_BUTTON))
    _fetch(app, done)


def build_tab(app, nb, w):
    """The 'Answers to my reports' tab in the Report window's notebook nb; returns (frame, refresh)."""
    frm = ttk.Frame(nb, padding=10)
    ttk.Label(frm, justify="left", wraplength=640, text=(
        "The author's answers to the reports you sent from this editor. They come by the report's number, which "
        "only you know - nobody else sees them. The editor looks for new answers when it starts (every few hours); "
        "Check now looks at once.")).pack(anchor="w")
    top = ttk.Frame(frm)
    top.pack(fill="x", pady=(8, 4))
    b_check = ttk.Button(top, text="Check now")
    b_check.pack(side="left")
    lbl_state = ttk.Label(top, foreground="#666")
    lbl_state.pack(side="left", padx=8)

    panes = ttk.Panedwindow(frm, orient="vertical")
    panes.pack(fill="both", expand=True)
    up = ttk.Frame(panes)
    tree = ttk.Treeview(up, columns=("id", "sent", "what", "state"), show="headings", height=6, selectmode="browse")
    for c, t, wd in (("id", "Report", 200), ("sent", "Sent", 120), ("what", "What it was about", 260),
                     ("state", "State", 170)):
        tree.heading(c, text=t)
        tree.column(c, width=wd, stretch=(c == "what"))
    tree.tag_configure("new", font=("TkDefaultFont", 9, "bold"))
    tree.pack(fill="both", expand=True)
    panes.add(up, weight=1)

    down = ttk.Frame(panes)
    talk = tk.Text(down, height=10, wrap="word", state="disabled", font="TkDefaultFont")
    talk.tag_configure("who", font=("TkDefaultFont", 9, "bold"))
    talk.pack(fill="both", expand=True)
    reply_box = ttk.LabelFrame(down, text="Your answer to the author (a question answered, more details, 'still "
                                          "broken in the new build'...)", padding=6)
    reply_box.pack(fill="x", pady=(6, 0))
    reply = tk.Text(reply_box, height=4, wrap="word")
    reply.pack(fill="x")
    pictures = []
    row = ttk.Frame(reply_box)
    row.pack(fill="x", pady=(4, 0))
    v_logs = tk.BooleanVar(value=False)
    lbl_pics = ttk.Label(row, foreground="#666", text="No pictures.")

    def add_pictures():
        for p in filedialog.askopenfilenames(parent=w, title="Pictures for the answer (up to %d)" % report.PICTURES,
                                             filetypes=[("Pictures", " ".join("*" + e for e in report.PICTURE_EXT))]):
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
    ttk.Button(row, text="Add a screenshot...", command=add_pictures).pack(side="left")
    ttk.Checkbutton(row, text="with the newest logs (names cut out, as in a report)", variable=v_logs).pack(
        side="left", padx=8)
    lbl_pics.pack(side="left", padx=4)
    b_reply = ttk.Button(row, text="Send the answer")
    b_reply.pack(side="right")
    panes.add(down, weight=2)

    state = {"rows": [], "pick": None}

    def answers():
        return getattr(app, "_report_answers", None) or {}

    def fill():
        state["rows"] = report.sent_reports()
        a = answers()
        new = set(report.news(a, settings.get("reports_seen") or {}))
        tree.delete(*tree.get_children())
        for r in state["rows"]:
            what = r.get("title") or ("an idea" if r.get("kind") == "suggestion" else "")
            st = report.state_words(a.get(r["id"]))
            n = sum(1 for m in (a.get(r["id"]) or {}).get("messages", []) if m.get("from") == "author")
            if n:
                st += " - %d answer%s" % (n, "" if n == 1 else "s")
            tree.insert("", "end", iid=r["id"], values=(r["id"] + ("  NEW" if r["id"] in new else ""),
                                                        r.get("at", ""), what, st),
                        tags=("new",) if r["id"] in new else ())
        if not state["rows"]:
            lbl_state.configure(text="No reports sent from this editor yet.")
        pick = state["pick"] if state["pick"] in tree.get_children() else (
            next((r["id"] for r in state["rows"] if r["id"] in new), None) or (state["rows"][0]["id"] if state["rows"] else None))
        if pick:
            tree.selection_set(pick)
            tree.see(pick)
        show(pick)

    def show(rid):
        state["pick"] = rid
        talk.configure(state="normal")
        talk.delete("1.0", "end")
        a = answers().get(rid) if rid else None
        if rid and a:
            for m in a.get("messages", []):
                who = "The author" if m.get("from") == "author" else "You"
                at = (m.get("at") or "").replace("T", " ")[:16]
                talk.insert("end", "%s  %s\n" % (who, at), "who")
                talk.insert("end", (m.get("text") or "") + "\n\n")
            if not a.get("messages"):
                talk.insert("end", "No answer yet. The author has seen the report when its state changes.\n")
            if a.get("state") == "closed":
                talk.insert("end", "The report is %s.\n" % report.state_words(a), "who")
            report.mark_seen(answers(), [rid])
        elif rid:
            talk.insert("end", "No answer found yet (or not checked - press Check now).\n")
        talk.configure(state="disabled")
        b_reply.configure(state="normal" if rid else "disabled")

    def picked(ev=None):
        sel = tree.selection()
        if sel:
            show(sel[0])
            n = show_count(app)
            try:
                nb.tab(frm, text="Answers to my reports" + (" (%d new)" % n if n else ""))
            except tk.TclError:
                pass                                   # not added to the notebook yet
            # the NEW mark goes once it was read
            vals = list(tree.item(sel[0], "values"))
            if vals and vals[0].endswith("NEW"):
                vals[0] = sel[0]
                tree.item(sel[0], values=vals, tags=())
    tree.bind("<<TreeviewSelect>>", picked)

    def check():
        b_check.configure(state="disabled")
        lbl_state.configure(text="Looking for answers...")

        def done(a, error):
            b_check.configure(state="normal")
            if error:
                lbl_state.configure(text="Not checked: %s" % error)
                return
            lbl_state.configure(text="Checked %s." % datetime.datetime.now().strftime("%H:%M"))
            fill()
            n = show_count(app)
            nb.tab(frm, text="Answers to my reports" + (" (%d new)" % n if n else ""))
        _fetch(app, done)
    b_check.configure(command=check)

    def send_reply():
        rid = state["pick"]
        msg = reply.get("1.0", "end").strip()
        if not rid:
            return
        if not msg:
            messagebox.showerror(APP, "Write your answer first - a few words are enough.", parent=w)
            return
        hide = [x.strip() for x in (settings.get("report_hide") or "").split(",") if x.strip()]
        data = None
        if pictures or v_logs.get():
            texts = []
            if v_logs.get():
                game = mod_dir = None
                if app.mod:
                    from .newmod import game_of
                    game = game_of(app.mod.data)
                    mod_dir = os.path.dirname(os.path.abspath(app.mod.data))
                files = report.found(game, mod_dir)
                hide = report.hidden_words(files, hide)
                texts = report.contents(files, hide)
            data = report.build_zip(texts, msg, "", report.about(app.mod, _version()), pictures, hide)
        row_ = next((r for r in state["rows"] if r["id"] == rid), {})
        issue = (answers().get(rid) or {}).get("issue") or row_.get("issue") or 0
        b_reply.configure(state="disabled")
        lbl_state.configure(text="Sending the answer...")
        result = {}

        def work():
            try:
                report.send_reply(rid, issue, report.scrub(msg, hide), data, _version())
                result["ok"] = True
            except Exception as e:
                result["e"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def wait():
            if th.is_alive():
                w.after(200, wait)
                return
            b_reply.configure(state="normal")
            if result.get("ok"):
                log.write("Answer sent to report %s" % rid)
                reply.delete("1.0", "end")
                del pictures[:]
                lbl_pics.configure(text="No pictures.")
                lbl_state.configure(text="Your answer went to %s." % rid)
                a = answers().setdefault(rid, {"issue": issue, "state": "open", "reason": "", "messages": []})
                a.setdefault("messages", []).append({"from": "you", "text": msg, "at": datetime.datetime.now(
                    ).strftime("%Y-%m-%d %H:%M")})
                show(rid)
            else:
                log.write("Answer to %s not sent: %s" % (rid, result["e"]))
                lbl_state.configure(text="")
                messagebox.showerror(APP, "The answer was not sent: %s" % result["e"], parent=w)
        wait()
    b_reply.configure(command=send_reply)

    if not report.url():
        lbl_state.configure(text="The report service is not set up in this version.", foreground=theme.ink("#a60"))
        b_check.configure(state="disabled")
    fill()
    return frm, check
