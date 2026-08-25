import os
import sys

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CONFIG_DATA_START = 3   # データ開始行（1-indexed）


# ══════════════════════════════════════════════════════════════════════════════
#  PyInstaller 対応: exe からでも相対ファイルを正しく参照する
# ══════════════════════════════════════════════════════════════════════════════
def _exe_dir() -> str:
    """
    exe 実行時   → exe ファイルと同じフォルダを返す
    python 実行時 → このスクリプトと同じフォルダを返す
    """
    if getattr(sys, "frozen", False):
        # PyInstaller で freeze された場合
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(filename: str) -> str:
    """
    exe / python どちらで実行しても正しいファイルパスを返す。

    例:
        resource_path("service-account.json")
        → C:/Tools/AirWorkTool/service-account.json  (exe 実行時)
        → /project/service-account.json              (python 実行時)
    """
    return os.path.join(_exe_dir(), filename)


CREDS_FILE = "service-account.json"   # exe / .py と同じフォルダに置くこと


# ══════════════════════════════════════════════════════════════════════════════
class FileConfig:
    """1ファイル分の設定をラップするオブジェクト。"""

    def __init__(self, file_name: str, tab_name: str, start_row: int,
                 col_map: dict, letter_map: dict):
        self.file_name   = file_name
        self.tab_name    = tab_name
        self.start_row   = start_row
        self._col_map    = col_map      # {"COL_STATUS": 1, ...}
        self._letter_map = letter_map   # {"COL_STATUS": "A", ...}

    def __getitem__(self, key):
        return self._col_map[key]

    def __contains__(self, key):
        return key in self._col_map

    def get(self, key, default=None):
        return self._col_map.get(key, default)

    def col(self, variable_name: str) -> int:
        """列インデックス（1-based）を返す。"""
        if variable_name not in self._col_map:
            raise KeyError(
                f"[ConfigLoader] '{variable_name}' が Config タブに未定義です。"
                f" (ファイル: {self.file_name})"
            )
        return self._col_map[variable_name]

    def letter(self, variable_name: str) -> str:
        """列アルファベット（A, B, AA ...）を返す。"""
        if variable_name not in self._letter_map:
            raise KeyError(
                f"[ConfigLoader] '{variable_name}' の列アルファベットが未定義です。"
            )
        return self._letter_map[variable_name]

    def all_vars(self) -> dict:
        return dict(self._col_map)

    def __repr__(self):
        return (
            f"FileConfig(file={self.file_name!r}, tab={self.tab_name!r}, "
            f"start_row={self.start_row}, vars={list(self._col_map.keys())})"
        )


# ══════════════════════════════════════════════════════════════════════════════
class ConfigLoader:
    """
    Google Sheets の Config タブを読み込み、各 .py の FileConfig を返す。
    1インスタンスで全ファイル設定をキャッシュする（接続は初回のみ）。

    ★ v2.3: sheet_id はデフォルト None に変更した。ConfigLoader() を
    引数無しで生成すること自体は常に可能で、実際に Google Sheets への
    接続が必要になるのは get() / get_all()（内部で _connect() を呼ぶ）
    が呼ばれた時点のみ。sheet_id が未設定のままこれらのメソッドを
    呼んだ場合は、その時点で分かりやすいエラーを出す。
    """

    def __init__(self, sheet_id: str = None, config_tab_name: str = "Config"):
        self._sheet_id        = sheet_id
        self._config_tab_name = config_tab_name
        self._cache: dict     = {}
        self._ws              = None
        self._all_values      = None

    def _connect(self):
        if self._ws is not None:
            return

        # ★ v2.3: sheet_id が渡されていない状態で実際に接続しようと
        # した場合、従来は gspread.open_by_key(None) 等で分かりにくい
        # エラーになっていた。ここで明示的にチェックし、原因が
        # 一目で分かるメッセージを出すようにした。
        if not self._sheet_id:
            raise ValueError(
                "[ConfigLoader] sheet_id が設定されていないため、"
                "Google Sheets の Config タブに接続できません。\n"
                "ConfigLoader(sheet_id=...) のように、有効なスプレッド"
                "シートIDを渡してインスタンスを作成し直してください。"
            )

        creds_path = resource_path(CREDS_FILE)

        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"[ConfigLoader] 認証ファイルが見つかりません: {creds_path}\n"
                f"exe / .py と同じフォルダに '{CREDS_FILE}' を置いてください。"
            )

        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        gc    = gspread.authorize(creds)
        sh    = gc.open_by_key(self._sheet_id)
        self._ws         = sh.worksheet(self._config_tab_name)
        self._all_values = self._ws.get_all_values()

    def _parse_all(self):
        self._connect()
        data_rows = self._all_values[CONFIG_DATA_START - 1:]

        IDX_FILE = 0; IDX_TAB = 1; IDX_VAR = 2
        IDX_LETTER = 3; IDX_COL = 4; IDX_START = 5

        buffers = {}
        current_file = ""

        for row in data_rows:
            if not any(c.strip() for c in row):
                continue

            cell_file = row[IDX_FILE].strip() if len(row) > IDX_FILE else ""
            if cell_file and not cell_file.startswith("【"):
                current_file = cell_file

            if not current_file:
                continue

            if current_file not in buffers:
                buffers[current_file] = {"tab": "", "start": 1, "cols": {}, "letters": {}}

            buf = buffers[current_file]
            cell_tab    = row[IDX_TAB].strip()    if len(row) > IDX_TAB    else ""
            cell_var    = row[IDX_VAR].strip()    if len(row) > IDX_VAR    else ""
            cell_letter = row[IDX_LETTER].strip() if len(row) > IDX_LETTER else ""
            cell_col    = row[IDX_COL].strip()    if len(row) > IDX_COL    else ""
            cell_start  = row[IDX_START].strip()  if len(row) > IDX_START  else ""

            if cell_tab and not buf["tab"]:
                buf["tab"] = cell_tab
            if cell_start and buf["start"] == 1:
                try:
                    buf["start"] = int(cell_start)
                except ValueError:
                    pass
            if cell_var and cell_col:
                try:
                    buf["cols"][cell_var] = int(cell_col)
                except ValueError:
                    pass
            if cell_var and cell_letter:
                buf["letters"][cell_var] = cell_letter

        for fname, buf in buffers.items():
            self._cache[fname] = FileConfig(
                file_name=fname, tab_name=buf["tab"],
                start_row=buf["start"], col_map=buf["cols"],
                letter_map=buf["letters"],
            )

    def get(self, file_name: str) -> "FileConfig":
        """指定ファイル名の FileConfig を返す（初回のみ全パース）。"""
        if not self._cache:
            self._parse_all()
        key = file_name.strip().lower()
        for k, v in self._cache.items():
            if k.lower() == key:
                return v
        raise ValueError(
            f"[ConfigLoader] '{file_name}' が Config タブに見つかりません。\n"
            f"登録済み: {list(self._cache.keys())}"
        )

    def get_all(self) -> dict:
        if not self._cache:
            self._parse_all()
        return dict(self._cache)

    def reload(self):
        """キャッシュクリア → 次回 get() 時に再読み込み。"""
        self._cache = {}; self._ws = None; self._all_values = None