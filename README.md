# JLPT_Voca2

간단한 JLPT 단어 순환 암기 데스크톱 프로그램입니다. `app.py`를 실행하면 작은 창이 항상 화면 위에 표시되며, 단어 → 발음/뜻 순으로 자동으로 보여 줍니다.

## 주요 기능
- `words.csv` 기본 단어 목록을 불러와 무작위 순서로 반복 재생
- 설정에서 `showMeaningTimer`(발음/뜻 표시 지연), `nextWordTimer`(다음 단어 지연), `alwaysOnTop`(항상 위) 조정 가능
- 설정 창에서 `단어 파일 가져오기...`를 통해 사용자 CSV 파일을 불러오기 가능
- 설정 창에서 현재 단어 목록을 표 형태로 확인하고 단어를 직접 추가/삭제 가능하며, 변경 사항은 현재 단어 CSV 파일에 즉시 저장
- 마지막으로 불러온 단어 CSV 경로가 `config.json`에 기록되어 재시작 시 자동으로 이어서 사용
- 일시정지/재생 버튼으로 순환 제어 가능
- 창 아무 곳이나 드래그하여 위치 이동 가능
- 설정은 `config.json`에 저장되어 재시작 후에도 유지 (`wordFile` 키에 현재 단어 파일 경로가 저장됨)

## 실행 방법
```bash
python app.py
```

CSV 파일은 `word,reading,meaning` 헤더를 포함해야 하며 UTF-8(또는 UTF-8 with BOM) 인코딩을 권장합니다.

### Windows용 실행 파일 만들기

파이썬이 설치되어 있지 않은 PC에서도 실행할 수 있도록 PyInstaller로 독립 실행형 EXE를 만들 수 있습니다.

#### GitHub Actions에서 바로 받기

저장소의 **Actions → Windows EXE build** 워크플로로 이동하면 최신 커밋 기준으로 자동 생성된 `JLPTVocab-win64.zip` 아티팩트를 다운로드할 수 있습니다. 압축을 풀면 `JLPTVocab.exe`와 기본 데이터 파일이 포함되어 있으며, 그대로 실행하면 됩니다. (GitHub 계정이 필요합니다.)

#### 로컬에서 직접 빌드하기

1. PyInstaller를 설치합니다.
   ```bash
   pip install pyinstaller
   ```
2. 저장소 루트에서 아래 명령을 실행합니다.
   ```bash
   python build_exe.py
   ```

`dist/JLPTVocab/JLPTVocab.exe`가 생성되며, 루트 디렉터리에 `JLPTVocab-win64.zip` 압축 파일도 함께 만들어집니다. 압축 파일 안에는 실행 파일과 기본 데이터가 들어 있어 그대로 배포하거나 USB 등에 옮겨 사용할 수 있습니다. 실행 파일을 배포하면 앱은 사용자별 데이터 디렉터리(`%APPDATA%/JLPTVocab` 또는 macOS의 `~/Library/Application Support/JLPTVocab`, Linux의 `~/.local/share/JLPTVocab`)에 설정과 단어 목록을 복사한 뒤 사용합니다.
