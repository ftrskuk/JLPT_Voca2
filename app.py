"""JLPT Vocabulary cycling desktop app.

This script implements a tkinter-based application that cycles through vocabulary
entries loaded from a CSV file, revealing readings/meanings on timers that can be
configured by the user. Configuration persists to a JSON file in the same
directory as the script.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_WORDS_PATH = APP_DIR / "words.csv"


DEFAULT_CONFIG = {
    "showMeaningTimer": 3,
    "nextWordTimer": 5,
    "alwaysOnTop": True,
}


@dataclass
class WordEntry:
    word: str
    reading: str
    meaning: str


class SettingsWindow(tk.Toplevel):
    """Popup window that lets the user modify timers and load word lists."""

    def __init__(self, app: "JLPTVocabApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.show_timer_var = tk.StringVar(value=str(self.app.config_data["showMeaningTimer"]))
        self.next_timer_var = tk.StringVar(value=str(self.app.config_data["nextWordTimer"]))
        self.always_on_top_var = tk.BooleanVar(value=self.app.config_data["alwaysOnTop"])

        container = ttk.Frame(self, padding=12)
        container.grid(row=0, column=0, sticky="nsew")

        ttk.Label(container, text="발음/뜻 표시 시간 (초)").grid(row=0, column=0, sticky="w")
        self.show_timer_entry = ttk.Entry(container, textvariable=self.show_timer_var, width=10)
        self.show_timer_entry.grid(row=0, column=1, sticky="e")

        ttk.Label(container, text="다음 단어 표시 시간 (초)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.next_timer_entry = ttk.Entry(container, textvariable=self.next_timer_var, width=10)
        self.next_timer_entry.grid(row=1, column=1, sticky="e", pady=(8, 0))

        self.always_on_top_check = ttk.Checkbutton(
            container,
            text="항상 위에 표시",
            variable=self.always_on_top_var,
        )
        self.always_on_top_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.import_button = ttk.Button(
            container,
            text="단어 파일 가져오기...",
            command=self.import_words,
        )
        self.import_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        self.save_button = ttk.Button(container, text="저장", command=self.save_settings)
        self.save_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)

    def focus_initial(self) -> None:
        self.show_timer_entry.focus_set()

    def on_close(self) -> None:
        self.destroy()

    def import_words(self) -> None:
        path_str = filedialog.askopenfilename(
            parent=self,
            title="단어 CSV 파일 선택",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        success = self.app.load_words_from_path(path)
        if success:
            messagebox.showinfo("단어 불러오기", f"{path.name} 파일에서 단어를 불러왔습니다.")

    def save_settings(self) -> None:
        try:
            show_timer = self._validate_timer(self.show_timer_var.get(), "발음/뜻 표시 시간")
            next_timer = self._validate_timer(self.next_timer_var.get(), "다음 단어 표시 시간")
        except ValueError as exc:
            messagebox.showerror("설정 오류", str(exc))
            return

        config = {
            "showMeaningTimer": show_timer,
            "nextWordTimer": next_timer,
            "alwaysOnTop": self.always_on_top_var.get(),
        }
        self.app.update_config(config)
        messagebox.showinfo("설정", "설정을 저장했습니다.")
        self.destroy()

    @staticmethod
    def _validate_timer(value: str, field_name: str) -> int:
        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} 값을 입력하세요.")
        try:
            number = int(value)
        except ValueError as exc:  # pragma: no cover - user input validation
            raise ValueError(f"{field_name}은(는) 정수여야 합니다.") from exc
        if number < 0:
            raise ValueError(f"{field_name}은(는) 0 이상이어야 합니다.")
        return number


class JLPTVocabApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("JLPT 단어 암기")
        self.resizable(False, False)
        self.geometry("320x220")

        self.config_data = load_config(CONFIG_PATH)
        if not CONFIG_PATH.exists():
            save_config(CONFIG_PATH, self.config_data)

        try:
            self.words = load_words_from_csv(DEFAULT_WORDS_PATH)
        except Exception as exc:  # pragma: no cover - startup failure display
            messagebox.showerror("오류", f"기본 단어 파일을 불러오지 못했습니다: {exc}")
            self.words = []

        self.settings_window: Optional[SettingsWindow] = None
        self.current_index = 0
        self.paused = False
        self.pending_jobs: List[str] = []
        self.stage = "word"

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        random.shuffle(self.words)

        self.create_widgets()
        self.apply_topmost_setting()
        self.bind_drag_events()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.show_current_word()

    def create_widgets(self) -> None:
        style = ttk.Style(self)
        if sys.platform == "darwin":
            style.theme_use("aqua")

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        self.word_label = ttk.Label(container, text="", font=("Helvetica", 20, "bold"))
        self.word_label.pack(anchor="center")

        self.reading_label = ttk.Label(container, text="", font=("Helvetica", 16))
        self.reading_label.pack(anchor="center", pady=(8, 0))

        self.meaning_label = ttk.Label(container, text="", font=("Helvetica", 14), wraplength=280)
        self.meaning_label.pack(anchor="center", pady=(4, 8))

        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x", pady=(8, 0))

        self.pause_button = ttk.Button(button_frame, text="일시정지", command=self.toggle_pause)
        self.pause_button.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.settings_button = ttk.Button(button_frame, text="⚙", width=3, command=self.open_settings)
        self.settings_button.pack(side="right")

        if not self.words:
            self.word_label.config(text="단어 목록이 없습니다.")

    def bind_drag_events(self) -> None:
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

    def start_move(self, event: tk.Event[tk.Misc]) -> None:
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def do_move(self, event: tk.Event[tk.Misc]) -> None:
        new_x = event.x_root - self._drag_offset_x
        new_y = event.y_root - self._drag_offset_y
        self.geometry(f"+{new_x}+{new_y}")

    def apply_topmost_setting(self) -> None:
        self.attributes("-topmost", bool(self.config_data.get("alwaysOnTop", True)))

    def open_settings(self) -> None:
        if self.settings_window and tk.Toplevel.winfo_exists(self.settings_window):
            self.settings_window.lift()
            return
        self.settings_window = SettingsWindow(self)
        self.settings_window.transient(self)
        self.settings_window.grab_set()
        self.settings_window.focus_initial()

    def toggle_pause(self) -> None:
        if self.paused:
            self.paused = False
            self.pause_button.config(text="일시정지")
            self.show_current_word()
        else:
            self.paused = True
            self.pause_button.config(text="재생")
            self.cancel_pending_jobs()

    def update_config(self, config: Dict[str, int | bool]) -> None:
        self.config_data = config
        save_config(CONFIG_PATH, self.config_data)
        self.apply_topmost_setting()
        if not self.paused:
            self.show_current_word()

    def load_words_from_path(self, path: Path) -> bool:
        try:
            entries = load_words_from_csv(path)
        except Exception as exc:
            messagebox.showerror("단어 불러오기", f"CSV 파일을 불러오는 중 오류가 발생했습니다: {exc}")
            return False
        if not entries:
            messagebox.showwarning("단어 불러오기", "CSV 파일에 단어가 없습니다.")
            return False

        self.words = entries
        random.shuffle(self.words)
        self.current_index = 0
        if self.paused:
            self.word_label.config(text="단어를 불러왔습니다. 재생을 눌러 시작하세요.")
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
        else:
            self.show_current_word()
        return True

    def cancel_pending_jobs(self) -> None:
        for job in self.pending_jobs:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self.pending_jobs.clear()

    def show_current_word(self) -> None:
        self.cancel_pending_jobs()
        if not self.words:
            self.word_label.config(text="단어 목록이 없습니다.")
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
            return

        entry = self.words[self.current_index]
        self.word_label.config(text=entry.word)
        self.reading_label.config(text="")
        self.meaning_label.config(text="")
        self.stage = "word"

        if not self.paused:
            delay_ms = max(0, int(self.config_data.get("showMeaningTimer", 0))) * 1000
            job = self.after(delay_ms, self.reveal_current_word)
            self.pending_jobs.append(job)

    def reveal_current_word(self) -> None:
        if not self.words:
            return
        entry = self.words[self.current_index]
        self.reading_label.config(text=entry.reading)
        self.meaning_label.config(text=entry.meaning)
        self.stage = "meaning"

        if not self.paused:
            delay_ms = max(0, int(self.config_data.get("nextWordTimer", 0))) * 1000
            job = self.after(delay_ms, self.advance_to_next_word)
            self.pending_jobs.append(job)

    def advance_to_next_word(self) -> None:
        if not self.words:
            return
        self.current_index = (self.current_index + 1) % len(self.words)
        if self.current_index == 0:
            random.shuffle(self.words)
        self.show_current_word()

    def on_close(self) -> None:
        self.cancel_pending_jobs()
        self.destroy()


def load_config(path: Path) -> Dict[str, int | bool]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "showMeaningTimer": int(data.get("showMeaningTimer", DEFAULT_CONFIG["showMeaningTimer"])),
                "nextWordTimer": int(data.get("nextWordTimer", DEFAULT_CONFIG["nextWordTimer"])),
                "alwaysOnTop": bool(data.get("alwaysOnTop", DEFAULT_CONFIG["alwaysOnTop"])),
            }
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(path: Path, config: Dict[str, int | bool]) -> None:
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_words_from_csv(path: Path) -> List[WordEntry]:
    if not path.exists():
        raise FileNotFoundError(f"{path} 파일이 존재하지 않습니다.")

    entries: List[WordEntry] = []
    with path.open(encoding="utf-8-sig", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        required_fields = {"word", "reading", "meaning"}
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError("CSV 헤더는 word, reading, meaning 을 포함해야 합니다.")
        for row in reader:
            word = (row.get("word") or "").strip()
            reading = (row.get("reading") or "").strip()
            meaning = (row.get("meaning") or "").strip()
            if not word:
                continue
            entries.append(WordEntry(word=word, reading=reading, meaning=meaning))
    return entries


def main() -> None:
    app = JLPTVocabApp()
    app.mainloop()


if __name__ == "__main__":
    main()
