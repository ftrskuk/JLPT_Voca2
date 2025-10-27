"""Build script that packages the JLPT vocab app into a Windows executable."""

from __future__ import annotations

import os
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent

PyInstaller.__main__.run(
    [
        str(ROOT / "app.py"),
        "--name=JLPTVocab",
        "--noconsole",
        "--clean",
        f"--add-data={ROOT / 'words.csv'}{os.pathsep}.",
        f"--add-data={ROOT / 'config.json'}{os.pathsep}.",
    ]
)
