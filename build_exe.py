"""Build script that packages the JLPT vocab app into a Windows executable.

Running this helper will invoke PyInstaller and then compress the dist folder so
the resulting archive mirrors the artifact produced in CI.  The zip file is
written next to this script as ``JLPTVocab-win64.zip``.
"""

from __future__ import annotations

import os
from pathlib import Path
import zipfile

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
APP_DIR = DIST_DIR / "JLPTVocab"
ARCHIVE_PATH = ROOT / "JLPTVocab-win64.zip"


def build() -> None:
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


def create_archive() -> None:
    if not APP_DIR.exists():
        raise SystemExit(
            "빌드 결과를 찾을 수 없습니다. dist/JLPTVocab 폴더가 생성됐는지 확인하세요."
        )

    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in APP_DIR.rglob("*"):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(APP_DIR))

    print(f"생성 완료: {ARCHIVE_PATH}")


def main() -> None:
    build()
    create_archive()


if __name__ == "__main__":
    main()
