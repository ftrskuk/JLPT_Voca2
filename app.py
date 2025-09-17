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
from typing import Any, Dict, List, Mapping, Optional, Sequence

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_WORDS_PATH = APP_DIR / "words.csv"
DEFAULT_WORDS_PATH_RESOLVED = DEFAULT_WORDS_PATH.resolve()


DEFAULT_CONFIG: Dict[str, Any] = {
    "showMeaningTimer": 3,
    "nextWordTimer": 5,
    "alwaysOnTop": True,
    "wordFile": "",

}


@dataclass
class WordEntry:
    word: str
    reading: str
    meaning: str


class WordEditDialog(tk.Toplevel):
    """Simple dialog that collects word information from the user."""

    def __init__(self, parent: tk.Misc, title: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self.result: Optional[WordEntry] = None

        container = ttk.Frame(self, padding=12)
        container.grid(row=0, column=0, sticky="nsew")

        ttk.Label(container, text="단어").grid(row=0, column=0, sticky="w")
        self.word_var = tk.StringVar()
        self.word_entry = ttk.Entry(container, textvariable=self.word_var, width=30)
        self.word_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(container, text="발음").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.reading_var = tk.StringVar()
        self.reading_entry = ttk.Entry(container, textvariable=self.reading_var, width=30)
        self.reading_entry.grid(row=1, column=1, sticky="ew", pady=(8, 0))

        ttk.Label(container, text="뜻").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.meaning_var = tk.StringVar()
        self.meaning_entry = ttk.Entry(container, textvariable=self.meaning_var, width=30)
        self.meaning_entry.grid(row=2, column=1, sticky="ew", pady=(8, 0))

        button_frame = ttk.Frame(container)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        ttk.Button(button_frame, text="취소", command=self.on_cancel).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(button_frame, text="추가", command=self.on_submit).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        container.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.bind("<Return>", self.on_submit)
        self.bind("<Escape>", self.on_cancel)

        self.after(100, self.word_entry.focus_set)

    def on_submit(self, event: Optional[tk.Event[tk.Misc]] = None) -> None:
        word = self.word_var.get().strip()
        reading = self.reading_var.get().strip()
        meaning = self.meaning_var.get().strip()
        if not word:
            messagebox.showerror("단어 추가", "단어를 입력하세요.", parent=self)
            self.word_entry.focus_set()
            return
        self.result = WordEntry(word=word, reading=reading, meaning=meaning)
        self.destroy()

    def on_cancel(self, event: Optional[tk.Event[tk.Misc]] = None) -> None:
        self.result = None
        self.destroy()


class SettingsWindow(tk.Toplevel):
    """Popup window that lets the user modify timers and manage word lists."""


    def __init__(self, app: "JLPTVocabApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Settings")

        self.resizable(True, True)
        self.minsize(420, 400)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.show_timer_var = tk.StringVar(value=str(self.app.config_data["showMeaningTimer"]))
        self.next_timer_var = tk.StringVar(value=str(self.app.config_data["nextWordTimer"]))
        self.always_on_top_var = tk.BooleanVar(value=self.app.config_data["alwaysOnTop"])

        container = ttk.Frame(self, padding=12)
        container.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)


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

        self.word_file_var = tk.StringVar()
        self.word_file_label = ttk.Label(
            container,
            textvariable=self.word_file_var,
            foreground="#555555",
            wraplength=360,
        )
        self.word_file_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.save_button = ttk.Button(container, text="저장", command=self.save_settings)
        self.save_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        list_frame = ttk.LabelFrame(container, text="단어 목록")
        list_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        columns = ("word", "reading", "meaning")
        self.word_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=8,
        )
        self.word_tree.heading("word", text="단어")
        self.word_tree.heading("reading", text="발음")
        self.word_tree.heading("meaning", text="뜻")
        self.word_tree.column("word", anchor="center", width=120)
        self.word_tree.column("reading", anchor="center", width=120)
        self.word_tree.column("meaning", anchor="w", width=200)
        self.word_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.word_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.word_tree.configure(yscrollcommand=scrollbar.set)

        table_button_frame = ttk.Frame(list_frame)
        table_button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        table_button_frame.columnconfigure(0, weight=1)
        table_button_frame.columnconfigure(1, weight=1)

        self.add_word_button = ttk.Button(table_button_frame, text="추가", command=self.add_word)
        self.add_word_button.grid(row=0, column=0, sticky="ew")

        self.delete_word_button = ttk.Button(
            table_button_frame, text="삭제", command=self.delete_selected_words
        )
        self.delete_word_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(6, weight=1)

        self.word_tree.bind("<Delete>", self._on_delete_key)

        self.update_word_file_label()
        self.refresh_word_table()


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
            self.update_word_file_label()
            self.refresh_word_table()

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


    def refresh_word_table(self) -> None:
        if not hasattr(self, "word_tree"):
            return
        for item in self.word_tree.get_children():
            self.word_tree.delete(item)
        for entry in self.app.words:
            self.word_tree.insert(
                "",
                "end",
                iid=str(id(entry)),
                values=(entry.word, entry.reading, entry.meaning),
            )
        self.update_word_file_label()

    def add_word(self) -> None:
        dialog = WordEditDialog(self, "단어 추가")
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self.app.add_word(dialog.result)
        self.refresh_word_table()

    def delete_selected_words(self) -> None:
        selection = self.word_tree.selection()
        if not selection:
            messagebox.showinfo("단어 삭제", "삭제할 단어를 선택하세요.", parent=self)
            return
        ids = [int(item) for item in selection]
        self.app.delete_words_by_ids(ids)
        self.refresh_word_table()

    def _on_delete_key(self, event: tk.Event[tk.Misc]) -> str:
        self.delete_selected_words()
        return "break"

    def update_word_file_label(self) -> None:
        if not hasattr(self, "word_file_var"):
            return
        display_text = self.app.get_current_word_file_display()
        self.word_file_var.set(f"현재 파일: {display_text}")


class JLPTVocabApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("JLPT 단어 암기")
        self.resizable(False, False)
        self.geometry("320x220")

        self.config_data = load_config(CONFIG_PATH)
        if not CONFIG_PATH.exists():
            save_config(CONFIG_PATH, self.config_data)

        self.current_words_path = DEFAULT_WORDS_PATH_RESOLVED
        initial_word_path = self._resolve_configured_word_file()
        self.set_current_words_path(initial_word_path, persist=False)

        self.words: List[WordEntry] = []
        self._load_initial_words()


        self.settings_window: Optional[SettingsWindow] = None
        self.current_index = 0
        self.paused = False
        self.pending_jobs: List[str] = []
        self.stage = "word"

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        if self.words:
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

    def update_config(self, updates: Mapping[str, Any]) -> None:
        self.config_data.update(updates)

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


        self.replace_words(entries)
        self.set_current_words_path(path, persist=True)
        return True

    def set_current_words_path(self, path: Path, persist: bool = True) -> None:
        resolved = path.resolve()
        self.current_words_path = resolved
        if persist:
            if resolved == DEFAULT_WORDS_PATH_RESOLVED:
                self.config_data["wordFile"] = ""
            else:
                self.config_data["wordFile"] = str(resolved)
            save_config(CONFIG_PATH, self.config_data)

    def get_current_word_file_display(self) -> str:
        path = getattr(self, "current_words_path", DEFAULT_WORDS_PATH_RESOLVED)
        if path == DEFAULT_WORDS_PATH_RESOLVED:
            return f"{DEFAULT_WORDS_PATH.name} (기본)"
        try:
            relative = Path(path).relative_to(APP_DIR)
            return str(relative)
        except ValueError:
            return str(path)

    def persist_words(self) -> None:
        path = getattr(self, "current_words_path", DEFAULT_WORDS_PATH_RESOLVED)
        try:
            save_words_to_csv(path, self.words)
        except Exception as exc:
            messagebox.showerror("단어 저장", f"단어 목록을 저장하지 못했습니다: {exc}", parent=self)

    def _resolve_configured_word_file(self) -> Path:
        raw_value = self.config_data.get("wordFile", "")
        if isinstance(raw_value, str):
            trimmed = raw_value.strip()
        else:
            trimmed = str(raw_value).strip() if raw_value else ""
        if not trimmed:
            return DEFAULT_WORDS_PATH
        path = Path(trimmed)
        if not path.is_absolute():
            path = (APP_DIR / path).resolve()
        return path

    def _load_initial_words(self) -> None:
        try:
            self.words = load_words_from_csv(self.current_words_path)
        except Exception as exc:  # pragma: no cover - startup fallback path
            if self.current_words_path != DEFAULT_WORDS_PATH_RESOLVED:
                messagebox.showwarning(
                    "단어 불러오기",
                    "저장된 단어 파일을 불러올 수 없어 기본 목록을 사용합니다: "
                    f"{exc}",
                    parent=self,
                )
                self.set_current_words_path(DEFAULT_WORDS_PATH, persist=True)
                try:
                    self.words = load_words_from_csv(self.current_words_path)
                except Exception as default_exc:  # pragma: no cover - fatal failure
                    messagebox.showerror(
                        "오류",
                        f"기본 단어 파일을 불러오지 못했습니다: {default_exc}",
                        parent=self,
                    )
                    self.words = []
            else:
                messagebox.showerror(
                    "오류", f"기본 단어 파일을 불러오지 못했습니다: {exc}", parent=self
                )
                self.words = []


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


    def replace_words(self, entries: List[WordEntry], shuffle: bool = True) -> None:
        self.cancel_pending_jobs()
        self.words = list(entries)
        if shuffle and self.words:
            random.shuffle(self.words)
        self.current_index = 0
        if not self.words:
            self.stage = "word"
            self.word_label.config(text="단어 목록이 없습니다.")
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
            return
        if self.paused:
            entry = self.words[self.current_index]
            self.stage = "word"
            self.word_label.config(text=entry.word)
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
        else:
            self.show_current_word()

    def add_word(self, entry: WordEntry) -> None:
        self.words.append(entry)
        if len(self.words) == 1:
            self.current_index = 0
            if self.paused:
                self.stage = "word"
                self.word_label.config(text=entry.word)
                self.reading_label.config(text="")
                self.meaning_label.config(text="")
            else:
                self.show_current_word()
        self.persist_words()

    def delete_words_by_ids(self, entry_ids: List[int]) -> None:
        if not entry_ids:
            return
        id_set = set(entry_ids)
        if not id_set:
            return

        current_entry: Optional[WordEntry]
        if self.words and 0 <= self.current_index < len(self.words):
            current_entry = self.words[self.current_index]
        else:
            current_entry = None

        new_words = [entry for entry in self.words if id(entry) not in id_set]
        if len(new_words) == len(self.words):
            return
        self.words = new_words

        if not self.words:
            self.cancel_pending_jobs()
            self.current_index = 0
            self.stage = "word"
            self.word_label.config(text="단어 목록이 없습니다.")
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
            self.persist_words()
            return

        if current_entry and current_entry in self.words:
            self.current_index = self.words.index(current_entry)
        else:
            self.current_index = min(self.current_index, len(self.words) - 1)

        self.cancel_pending_jobs()
        if self.paused:
            entry = self.words[self.current_index]
            self.stage = "word"
            self.word_label.config(text=entry.word)
            self.reading_label.config(text="")
            self.meaning_label.config(text="")
        else:
            self.show_current_word()
        self.persist_words()


def load_config(path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    raw_word_file = data.get("wordFile")
    if isinstance(raw_word_file, str):
        word_file_value = raw_word_file.strip()
    elif raw_word_file:
        word_file_value = str(raw_word_file)
    else:
        word_file_value = DEFAULT_CONFIG["wordFile"]
    config: Dict[str, Any] = {
        "showMeaningTimer": int(data.get("showMeaningTimer", DEFAULT_CONFIG["showMeaningTimer"])),
        "nextWordTimer": int(data.get("nextWordTimer", DEFAULT_CONFIG["nextWordTimer"])),
        "alwaysOnTop": bool(data.get("alwaysOnTop", DEFAULT_CONFIG["alwaysOnTop"])),
        "wordFile": word_file_value,
    }
    for key, value in data.items():
        if key not in config:
            config[key] = value
    return config


def save_config(path: Path, config: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def save_words_to_csv(path: Path, entries: Sequence[WordEntry]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["word", "reading", "meaning"])
        for entry in entries:
            writer.writerow([entry.word, entry.reading, entry.meaning])



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
