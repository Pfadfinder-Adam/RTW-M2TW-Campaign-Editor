"""Settings: everything the tool keeps between starts, in one window (CampaignEditor_settings.json in its own folder)
 - the look, the language, the game folder and the mod opened last, the map's look, what a report says about
you, the set-up fixes you said no to, and the tool's own folders. Each change is kept at once."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import log, settings
from .gui_util import one_window, hint



def open_folder(path):
    """The folder in the system's file manager."""
    if not path or not os.path.isdir(path):
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa - Windows only
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as e:
        log.write("open folder %s: %s" % (path, e))
        return False


@one_window
class SettingsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.transient(app)
        self.resizable(True, True)
        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)
        self._look(body)
        self._language(body)
        self._game(body)
        self._map(body)
        self._report(body)
        self._updates(body)
        self._fixes(body)
        self._folders(body)
        ttk.Button(body, text="Close", command=self.destroy).pack(side="bottom", anchor="e", pady=(8, 0))

    def _box(self, parent, title, help_text=None):
        lf = ttk.LabelFrame(parent, text=title, padding=6)
        lf.pack(fill="x", pady=(0, 6))
        if help_text:
            row = ttk.Frame(lf)
            row.pack(fill="x")
            hint(row, help_text).pack(side="right")
            return lf, row
        return lf, lf

    # ------------------------------------------------------------------
    def _look(self, body):
        from . import theme
        _, row = self._box(body, "Look")
        self.v_theme = tk.StringVar(value="dark" if theme.dark() else "light")
        for val, text in (("light", "Light"), ("dark", "Dark")):
            ttk.Radiobutton(row, text=text, value=val, variable=self.v_theme,
                            command=self._theme).pack(side="left", padx=(0, 10))

    def _theme(self):
        from . import theme
        if (self.v_theme.get() == "dark") != theme.dark():
            self.app.toggle_theme()

    def _language(self, body):
        from . import look as LK
        lf, row = self._box(body, "Language of the window", "The editor's words in another language: a language "
                            "file the community translated (Add a language file... puts one in). Words to "
                            "translate... writes every word of the windows into a file to fill - send it back and "
                            "it comes with the editor. What a file has no word for stays English.")
        names = sorted(LK.languages())
        self.v_lang = tk.StringVar(value=settings.get("language") or "English")
        cb = ttk.Combobox(row, textvariable=self.v_lang, values=["English"] + names, state="readonly", width=18)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._language_picked())
        ttk.Button(row, text="Add a language file...", command=lambda: self._language_add(cb)).pack(
            side="left", padx=(6, 0))
        ttk.Button(row, text="Words to translate...", command=self._language_words).pack(side="left", padx=(6, 0))

    def _language_picked(self):
        name = self.v_lang.get()
        name = "" if name == "English" else name
        settings.put("language", name)
        look = getattr(self.app, "look", None)
        if look is not None:
            look.set_language(name)

    def _language_add(self, cb):
        from . import look as LK
        p = filedialog.askopenfilename(parent=self, title="A language file of the editor",
                                       filetypes=(("Language", "*.json"),))
        if not p:
            return
        try:
            name = LK.add_language(p)
        except (OSError, ValueError) as e:
            messagebox.showerror("Settings", str(e), parent=self)
            return
        cb.configure(values=["English"] + sorted(LK.languages()))
        self.v_lang.set(name)
        self._language_picked()

    def _language_words(self):
        import json
        from . import look as LK
        look = getattr(self.app, "look", None)
        have = look.words if look is not None else {}
        seen = sorted(look.seen_words) if look is not None else []
        p = filedialog.asksaveasfilename(parent=self, title="Words to translate", defaultextension=".json",
                                         initialfile="language.json", filetypes=(("Language", "*.json"),))
        if not p:
            return
        data = LK.template(have, seen)
        if look is not None and look.language:
            data["language"] = look.language
        try:
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=1, ensure_ascii=False)
        except OSError as e:
            messagebox.showerror("Settings", str(e), parent=self)
            return
        messagebox.showinfo("Settings", "%d words written. Fill each \"\" with its translation, put the language's "
                                        "own name in \"language\" and yours in \"by\", then Add a language file..."
                                        % len(data["words"]), parent=self)

    def _game(self, body):
        lf, row = self._box(body, "Game and mod", "The game folder is where the mods list (top left) is looked for; "
                                                  "the mod opened last opens by itself at the next start.")
        self.l_game = ttk.Label(row, text="")
        self.l_game.pack(side="left")
        r2 = ttk.Frame(lf)
        r2.pack(fill="x", pady=(4, 0))
        ttk.Button(r2, text="Pick the game folder...", command=self._pick_game).pack(side="left")
        ttk.Button(r2, text="Forget the game and the last mod", command=self._forget).pack(side="left", padx=6)
        self._show_game()

    def _show_game(self):
        self.l_game.configure(text="Game: %s\nLast mod: %s" % (settings.get("game") or "(not picked yet)",
                                                              settings.get("mod_data") or "(none)"))

    def _pick_game(self):
        d = filedialog.askdirectory(parent=self, title="The game's folder (where RomeTW.exe / medieval2.exe is)",
                                    initialdir=settings.get("game") or "")
        if d:
            settings.put("game", d)
            try:
                self.app.fill_mods(d)
            except Exception as e:
                log.write("fill mods: %s" % e)
            self._show_game()

    def _forget(self):
        settings.put("game", None)
        settings.put("mod_data", None)
        self._show_game()

    def _map(self, body):
        _, row = self._box(body, "Campaign map", "How the Map tab draws the ground and whether its legend shows; the "
                                                 "same switches as the map's Layers panel and Signs and tools box.")
        mv = getattr(self.app, "map_view", None)
        if mv is None:
            ttk.Label(row, text="(the map is not open yet)").pack(side="left")
            return
        for var, text in ((mv.v_relief, "relief"), (mv.v_rivers, "rivers"),
                          (mv.v_grid, "tile grid up close")):
            ttk.Checkbutton(row, text=text, variable=var, command=self._map_look).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(row, text="legend", variable=mv.v_legend, command=mv._legend_toggled).pack(side="left")
        from .gui_map import ZOOM_SETTINGS, zoom_setting
        z = ttk.Frame(row.master)
        z.pack(fill="x", pady=(4, 0))
        for key, text, most in (("map_zoom_step", "Wheel zoom step, %", 100),
                                ("map_zoom_step_fine", "with Ctrl, %", 50),
                                ("map_signs_from", "armies, agents, fleets and ports shown from zoom %", 2000),
                                ("map_shore_from", "shore line (Terrain editor) from zoom %", 2000)):
            ttk.Label(z, text=text).pack(side="left", padx=(0, 4))
            v = tk.StringVar(value="%g" % zoom_setting(key))

            def keep(*_, key=key, v=v, most=most):
                try:
                    n = float(v.get())
                except ValueError:
                    return
                if 0 < n <= most:
                    settings.put(key, n)
                    self._render_soon()
            v.trace_add("write", keep)
            ttk.Spinbox(z, from_=1, to=most, increment=50 if key in ("map_signs_from", "map_shore_from") else 1, textvariable=v,
                        width=6).pack(side="left", padx=(0, 12))
        hint(z, "The wheel zooms the map by this step (the zoom shown beside - / + / Fit stays a round number: 100, "
                "110, 120 %%...); Ctrl + wheel by the finer step; Shift + wheel slowly and smoothly. Towns are always "
                "drawn; armies, agents, fleets and ports only from the zoom given; the Terrain editor's Shore line too "
                "(defaults %d / %d / %d / %d)." % (
                    ZOOM_SETTINGS["map_zoom_step"], ZOOM_SETTINGS["map_zoom_step_fine"],
                    ZOOM_SETTINGS["map_signs_from"], ZOOM_SETTINGS["map_shore_from"])).pack(side="left")

    def _render_soon(self):
        """The map drawn again once the typing stops, not at each key: a big map's drawing held the window, so the
        first click on Close was lost (the tester, 2026-10-22)."""
        if getattr(self, "_render_job", None):
            self.after_cancel(self._render_job)

        def go():
            self._render_job = None
            try:
                self.app.map_view.render()
            except Exception as e:
                log.write("map render: %s" % e)
        self._render_job = self.after(400, go)

    def _map_look(self):
        mv = self.app.map_view
        settings.put("map_look", {"relief": mv.v_relief.get(),
                                  "rivers": mv.v_rivers.get(), "grid": mv.v_grid.get()})
        try:
            mv.render()
        except Exception as e:
            log.write("map render: %s" % e)

    def _report(self, body):
        lf, row = self._box(body, "Reports (Report a bug / Suggest)", "Filled in for you in the report window. "
                                                                      "A report is sent only with your click there; "
                                                                      "answers are looked for only for the reports "
                                                                      "you sent.")
        ttk.Label(row, text="Your contact (Discord name / e-mail, optional)").pack(side="left")
        self.v_contact = tk.StringVar(value=settings.get("report_contact", "") or "")
        e = ttk.Entry(lf, textvariable=self.v_contact, width=40)
        e.pack(anchor="w", pady=(2, 0))
        self.v_contact.trace_add("write", lambda *a: settings.put("report_contact", self.v_contact.get().strip()))
        self.v_answers = tk.BooleanVar(value=settings.get("reports_check", True) is not False)
        ttk.Checkbutton(lf, variable=self.v_answers, text="Look for the author's answers to my reports when the editor "
                        "starts (every few hours; asks only by the reports' numbers)",
                        command=lambda: settings.put("reports_check", bool(self.v_answers.get()))).pack(
            anchor="w", pady=(6, 0))
        self.v_crash = tk.BooleanVar(value=settings.get("crash_offer", True) is not False)
        ttk.Checkbutton(lf, variable=self.v_crash, text="When the game has stopped (crashed), ask once whether to send "
                        "a report (looked at after Start the game and when the editor starts; nothing is sent "
                        "without your click)",
                        command=lambda: settings.put("crash_offer", bool(self.v_crash.get()))).pack(anchor="w")

    def _updates(self, body):
        lf, _ = self._box(body, "New versions", "Only the number of the newest release is asked for - nothing is "
                                                "sent. A newer one turns the GitHub button at the bottom green with "
                                                "its number; it then opens its page.")
        self.v_release = tk.BooleanVar(value=settings.get("release_check", True) is not False)
        ttk.Checkbutton(lf, variable=self.v_release, text="Look for a new version of the editor when it starts "
                        "(on GitHub; again every 6 hours while it is open)",
                        command=lambda: settings.put("release_check", bool(self.v_release.get()))).pack(anchor="w")

    def _fixes(self, body):
        _, row = self._box(body, "Set-up questions on Load", "When a mod is loaded the tool looks for set-up "
                                                             "problems and offers to put them right; a 'no' is "
                                                             "remembered per mod, so it does not ask again.")
        self.l_fixes = ttk.Label(row, text="")
        self.l_fixes.pack(side="left")
        ttk.Button(row, text="Ask again", command=self._ask_again).pack(side="left", padx=8)
        self._show_fixes()

    def _show_fixes(self):
        n = sum(len(v) for v in (settings.get("fixes_declined") or {}).values())
        self.l_fixes.configure(text="%d fix(es) you said no to" % n)

    def _ask_again(self):
        settings.put("fixes_declined", {})
        self._show_fixes()

    def _folders(self, body):
        _, row = self._box(body, "Folders", "The exe is meant to lie in the game's folder (beside RomeTW.exe / "
                                            "medieval2.exe). Beside it, in its own folder CampaignEditor: "
                                            "CampaignEditor_settings.json (these settings) and CampaignEditor_logs (the log, and on every close the "
                                            "session's log with a copy of the game's system.log.txt as "
                                            "game_system.log.txt in sessions/). A mod's backups (Restore) lie beside "
                                            "its data folder in CampaignEditor_backups (older versions' "
                                            "backups are listed too).")
        ttk.Button(row, text="Open the logs folder", command=lambda: open_folder(log.logs_dir())).pack(side="left")
        from .relocate import running_exe
        mv = ttk.Button(row, text="Put the editor into the game's folder...", command=lambda: self.app.offer_move(True))
        mv.pack(side="left", padx=6)
        if not running_exe() or log.exe_game():
            mv.state(["disabled"])               # from the source, or it lies in a game folder already
        mod = getattr(self.app, "mod", None)
        if mod is not None:
            from .plan import BACKUP_DIRS
            b = next((x for x in (os.path.join(os.path.dirname(mod.data), n) for n in BACKUP_DIRS)
                      if os.path.isdir(x)), os.path.join(os.path.dirname(mod.data), BACKUP_DIRS[0]))
            btn = ttk.Button(row, text="Open this mod's backups", command=lambda: open_folder(b))
            btn.pack(side="left", padx=6)
            if not os.path.isdir(b):
                btn.state(["disabled"])
            dele = ttk.Button(row, text="Delete this mod's backups...", command=self._delete_backups)
            dele.pack(side="left", padx=(18, 0))           # destructive: set apart from the others
            if not os.path.isdir(b):
                dele.state(["disabled"])

    def _delete_backups(self):
        """Every backup of the loaded mod goes, after a yes: the files stay as they are, Restore / Undo this write
        have nothing left to put back."""
        from .gui_util import ask
        from .plan import backups, delete_backups
        mod = self.app.mod
        n = len(backups(mod))
        if not ask("Settings", "Delete all %d backup(s) of this mod?\n\nThe mod's files stay as they are now; "
                   "only the way back goes - Restore a backup and Undo this write will have nothing to put back. "
                   "This cannot be undone." % n, yes="Delete them", no="Keep them", danger=True, parent=self):
            return
        gone = delete_backups(mod)
        log.write("Backups deleted: %d folder(s) of %s" % (gone, mod.data))
        gone_undo = getattr(self.app, "_undo_gone", None)
        if gone_undo:
            gone_undo()
        from tkinter import messagebox
        messagebox.showinfo("Settings", "%d backup folder(s) deleted." % gone, parent=self)
