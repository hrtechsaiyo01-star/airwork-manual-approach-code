import hashlib
import os
import subprocess
import sys
import tempfile
from typing import Callable, Optional, Tuple

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.service_account import Credentials

# ═══════════════════════════════════════════════════════════════════════
#  設定 — リリースのたびに更新すること
# ═══════════════════════════════════════════════════════════════════════

# このビルドの現在のバージョン。新しいバージョンをリリースするたびに、
# この値を新バージョンに書き換えてから pyinstaller でビルドすること。
CURRENT_VERSION = "1.1.3"

# Google Drive 上の latest_version.json のファイルID。
# 一度設定すれば、以降のバージョンアップではこの値は変更不要
# （latest_version.json の「中身」だけを都度更新すればよい）。
LATEST_VERSION_FILE_ID = "1CXRUSKDVHkz0_noQBw6VTkiXNc5f1Yw8"

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ★ v3で追加。
# 共有ドライブ（Shared Drive／チームドライブ）内のファイルを操作する際、
# Google Drive API v3 はこのパラメータが無いと正しい権限があっても
# 404 を返す。マイドライブ上のファイルに対しては無害（無視される）ため、
# 全てのリクエストに常時付与する。
_SUPPORTS_ALL_DRIVES = "supportsAllDrives=true"


# ═══════════════════════════════════════════════════════════════════════
#  バージョン比較
# ═══════════════════════════════════════════════════════════════════════

def _version_tuple(v: str) -> Tuple[int, ...]:
    """'1.2.10' → (1, 2, 10) のようにバージョン文字列を比較可能な形に変換する。"""
    parts = []
    for p in (v or "").strip().split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote_version: str, current_version: str = CURRENT_VERSION) -> bool:
    """remote_version が current_version より新しければ True。"""
    return _version_tuple(remote_version) > _version_tuple(current_version)


# ═══════════════════════════════════════════════════════════════════════
#  Google Drive アクセス
# ═══════════════════════════════════════════════════════════════════════

def _get_drive_credentials() -> Credentials:
    """
    airwork_manual_approach.py の _find_service_account_file() と同じ
    認証ファイルを再利用する（同じフォルダに service_account.json 等が
    置かれている想定）。
    """
    from airwork_manual_approach import _find_service_account_file

    cred_file = _find_service_account_file()
    creds = Credentials.from_service_account_file(cred_file, scopes=DRIVE_SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds


def _drive_download(
    file_id: str,
    dest_path: str,
    access_token: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Google Drive API (v3) の files.get?alt=media エンドポイントを使い、
    ファイルをストリーミングダウンロードして dest_path に保存する。
    progress_callback(downloaded_bytes, total_bytes) が指定されていれば
    チャンクごとに呼び出す（total_bytes は不明な場合 0）。

    ★ v3: 共有ドライブ上のファイルにも対応できるよう
    `supportsAllDrives=true` を付与した。
    """
    url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}"
        f"?alt=media&{_SUPPORTS_ALL_DRIVES}"
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    with requests.get(url, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)


def fetch_latest_manifest() -> dict:
    """
    latest_version.json の内容を取得して dict で返す。
    例: {"version": "1.1.0", "file_id": "...", "notes": "..."}

    v2: 単に resp.json() を呼ぶだけだと、レスポンスがJSONでない場合
    （例: 権限不足で空のbody、間違ったfile_idでの404エラーページ等）に
    「Expecting value: line 1 column 1 (char 0)」という分かりにくい
    エラーになってしまっていた。ここでは、実際のHTTPステータスコードと
    レスポンス本文（先頭300文字）を含めた分かりやすいエラーメッセージに
    変換するようにした。

    ★ v3: 共有ドライブ上のファイルにも対応できるよう
    `supportsAllDrives=true` を付与した。また、404発生時のエラー
    メッセージに、共有ドライブが原因である可能性を追記した。
    """
    creds = _get_drive_credentials()
    url = (
        f"https://www.googleapis.com/drive/v3/files/{LATEST_VERSION_FILE_ID}"
        f"?alt=media&{_SUPPORTS_ALL_DRIVES}"
    )
    resp = requests.get(
        url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=15
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"latest_version.json の取得に失敗しました "
            f"(HTTPステータス: {resp.status_code})。\n"
            f"考えられる原因:\n"
            f"  ・LATEST_VERSION_FILE_ID が正しいファイルIDになっていない\n"
            f"  ・latest_version.json がサービスアカウントのメールアドレスと"
            f"共有されていない（Driveフォルダごと共有されているか確認）\n"
            f"  ・このファイルが「共有ドライブ」に置かれており、かつ"
            f"サービスアカウントがその共有ドライブのメンバーに追加されて"
            f"いない（共有ドライブはファイル単位の共有だけでは"
            f"不十分な場合があります）\n"
            f"レスポンス内容: {resp.text[:300]!r}"
        )

    try:
        return resp.json()
    except ValueError as e:
        raise RuntimeError(
            "latest_version.json の内容がJSONとして解析できませんでした。\n"
            "考えられる原因:\n"
            "  ・アップロード時にGoogleドキュメント形式に自動変換されて"
            "しまっている（Driveの設定「アップロードしたファイルを変換する」"
            "がオンになっていないか確認してください）\n"
            "  ・LATEST_VERSION_FILE_ID が .json ファイルではなく別の"
            "ファイル（フォルダ等）を指している\n"
            f"レスポンス本文（先頭300文字）: {resp.text[:300]!r}"
        ) from e


# ═══════════════════════════════════════════════════════════════════════
#  アップデートチェック／適用
# ═══════════════════════════════════════════════════════════════════════

def check_for_update() -> Optional[dict]:
    """
    最新バージョン情報を取得し、現在のバージョンより新しければ
    manifest（dict）を返す。新しくなければ（＝既に最新なら）None を返す。
    ネットワークエラー等が起きた場合は例外をそのまま呼び出し元に投げる
    （呼び出し側でtry/exceptしてユーザーに通知すること）。
    """
    manifest = fetch_latest_manifest()
    remote_version = manifest.get("version", "")
    if remote_version and is_newer(remote_version):
        return manifest
    return None


def _drive_get_metadata(file_id: str, access_token: str) -> dict:
    """
    Google Drive上のファイルのメタデータ（サイズ・md5Checksum）を取得する。
    Driveはアップロード時に自動的にmd5Checksumを計算して保持しているため、
    リリース側で手動でチェックサムを用意する必要がない。

    戻り値の例: {"size": "52428800", "md5Checksum": "d41d8cd98f00b204e9800998ecf8427e"}

    ★ v3: 共有ドライブ上のファイルにも対応できるよう
    `supportsAllDrives=true` を付与した。また、従来は
    `resp.raise_for_status()` のみで例外の中身がそっけない
    `requests.exceptions.HTTPError` だったため、404発生時に
    「共有ドライブが原因かもしれない」という手がかりが一切
    ユーザーに伝わっていなかった。`fetch_latest_manifest()` と同様、
    ステータスコード・原因の候補・レスポンス本文を含めた
    分かりやすいエラーメッセージに変換するようにした。
    """
    url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}"
        f"?fields=size,md5Checksum&{_SUPPORTS_ALL_DRIVES}"
    )
    resp = requests.get(
        url, headers={"Authorization": f"Bearer {access_token}"}, timeout=15
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"ファイル情報の取得に失敗しました "
            f"(HTTPステータス: {resp.status_code}、file_id={file_id})。\n"
            f"考えられる原因:\n"
            f"  ・manifest内のfile_idが正しいファイルIDになっていない"
            f"（latest_version.jsonの内容を確認してください）\n"
            f"  ・このファイルがサービスアカウントのメールアドレスと"
            f"共有されていない\n"
            f"  ・このファイルが「共有ドライブ」に置かれており、かつ"
            f"サービスアカウントがその共有ドライブのメンバーに追加されて"
            f"いない（共有ドライブはファイル単位の共有だけでは"
            f"不十分な場合があります）\n"
            f"レスポンス内容: {resp.text[:300]!r}"
        )

    return resp.json()


def _md5_of_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_update_batch_script(current_exe: str, new_exe: str) -> str:
    """
    現在の .exe を新しい .exe で置き換えて再起動するバッチスクリプトを
    生成する。

    v2: 万一、チェックサム検証をすり抜けた壊れた実行ファイルが適用され、
    起動直後にクラッシュしてしまった場合の保険として、自動ロールバック
    機能を追加した。

      1. まず ping コマンドで数秒待つ（直後に呼び出し元プロセスが終了
         するため、Windows がファイルのロックを解放するまでの猶予）。
      2. 現在の .exe を "<元のファイル名>.bak" にリネームしてバックアップ
         する。
      3. 新しい .exe を元のファイル名でコピーする（失敗時は数回リトライ）。
      4. 新しい .exe を起動する。
      5. 数秒待った後、tasklist でそのプロセスがまだ実行中かを確認する。
           * まだ実行中 → 起動に成功したとみなし、バックアップを削除
             して終了。
           * 実行中でない（＝起動直後にクラッシュした可能性が高い）
             → バックアップから元の .exe を復元し、元のバージョンを
               再起動する。
      6. 最後に、ダウンロードした一時ファイルと、このバッチファイル
         自身を削除する（自己削除の定番テクニック）。
    """
    exe_dir = os.path.dirname(current_exe)
    exe_name = os.path.basename(current_exe)
    backup_path = os.path.join(exe_dir, exe_name + ".bak")

    return f'''@echo off
setlocal
set RETRY=0
ping 127.0.0.1 -n 3 > nul

if exist "{backup_path}" del "{backup_path}" > nul 2>&1
ren "{current_exe}" "{exe_name}.bak"

:retry
copy /y "{new_exe}" "{current_exe}" > nul
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% GEQ 10 (
        echo Update copy failed, restoring backup.
        copy /y "{backup_path}" "{current_exe}" > nul
        exit /b 1
    )
    ping 127.0.0.1 -n 2 > nul
    goto retry
)

start "" "{current_exe}"
ping 127.0.0.1 -n 5 > nul

tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul
if errorlevel 1 (
    echo New version did not stay running, rolling back to previous version.
    copy /y "{backup_path}" "{current_exe}" > nul
    start "" "{current_exe}"
) else (
    del "{backup_path}" > nul 2>&1
)

del "{new_exe}" > nul 2>&1
(goto) 2>nul & del "%~f0"
'''


def download_and_apply_update(
    manifest: dict,
    log_callback: Optional[Callable[[str, str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    manifest（{"version":..., "file_id":..., "notes":...}）を元に
    新しい .exe をダウンロードし、自分自身を新しい .exe に置き換えて
    再起動する。

    この関数は正常終了しない（最後に os._exit(0) でプロセスを終了する）
    ことに注意。呼び出し側は、この関数を呼ぶ前にユーザーへの確認
    ダイアログ等を済ませておくこと。

    ★ v2: ダウンロードが途中で切れた／壊れたファイルがそのまま適用
    されてしまい、新バージョンが「Failed to load Python DLL」等で
    起動できなくなる不具合が確認されたため、以下の対策を追加した。

      1. ダウンロード前に、Google Drive が自動計算している
         md5Checksum（アップロード時に自動生成されるため、リリース側で
         手動計算する必要はない）を取得しておく。
      2. ダウンロード完了後、実際にダウンロードしたファイルの
         MD5 を計算し、Drive側のmd5Checksumと一致するか検証する。
         一致しない場合は、ダウンロードが壊れているとみなし、
         最大2回まで再ダウンロードを試みる。
      3. それでも一致しない場合は、アップデートを完全に中止し、
         現在のバージョンをそのまま使い続ける
         （＝壊れたファイルで現在のexeを上書きすることは絶対にしない）。
      4. 検証に成功した場合のみ、実際の置き換え処理（.batスクリプト）に
         進む。.batスクリプト自体にも自動ロールバック機能を追加済み
         （_build_update_batch_script のdocstring参照）。
    """

    def _log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(msg, level)

    if not getattr(sys, "frozen", False):
        _log(
            "アップデート機能は配布用の .exe でのみ利用できます"
            "（ソースから直接実行している場合は、手動でファイルを"
            "更新してください）。",
            "WARN",
        )
        return

    current_exe = sys.executable  # 例: C:\\...\\airwork_manual_approach_gui.exe
    file_id = manifest["file_id"]

    creds = _get_drive_credentials()

    _log("ダウンロード先ファイルの情報を確認中...", "INFO")
    try:
        metadata = _drive_get_metadata(file_id, creds.token)
    except Exception as e:
        _log(f"ファイル情報の取得に失敗しました: {e}", "ERROR")
        return

    expected_md5 = metadata.get("md5Checksum")
    if not expected_md5:
        _log(
            "Drive側のチェックサム情報が取得できませんでした。"
            "整合性チェック無しでアップデートを進めることはできないため、"
            "アップデートを中止します。",
            "ERROR",
        )
        return

    tmp_dir = tempfile.mkdtemp(prefix="airwork_update_")
    new_exe_path = os.path.join(tmp_dir, "new_version.exe")

    max_attempts = 3
    verified = False
    for attempt in range(1, max_attempts + 1):
        _log(
            f"新しいバージョン {manifest.get('version')} をダウンロード中... "
            f"({attempt}/{max_attempts})",
            "INFO",
        )
        try:
            _drive_download(file_id, new_exe_path, creds.token, progress_callback)
        except Exception as e:
            _log(f"ダウンロードに失敗しました: {e}", "WARN")
            continue

        actual_md5 = _md5_of_file(new_exe_path)
        if actual_md5.lower() == str(expected_md5).lower():
            verified = True
            break

        _log(
            f"ダウンロードしたファイルのチェックサムが一致しません"
            f"（{attempt}/{max_attempts}回目）。再試行します...",
            "WARN",
        )

    if not verified:
        _log(
            "ダウンロードの整合性検証に何度失敗しました。ネットワークが"
            "不安定である可能性があります。現在のバージョンのまま"
            "アップデートを中止しました（既存のアプリには一切影響が"
            "ありません）。時間をおいて再度お試しください。",
            "ERROR",
        )
        return

    _log("チェックサムを確認しました。アプリを再起動して更新を適用します...", "OK")

    bat_path = os.path.join(tmp_dir, "apply_update.bat")
    with open(bat_path, "w", encoding="mbcs") as f:
        f.write(_build_update_batch_script(current_exe, new_exe_path))

    # ★ v4: 従来は DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP を使用して
    # いたが、Windows 11 + Windows Terminal（既定の端末アプリ）環境では、
    # .bat スクリプト内のパイプを使ったコマンド（tasklist | find）を
    # 実行する際に、DETACHED_PROCESS では抑制しきれない新しいコンソール
    # ウィンドウが生成され、それが空白のまま画面に残ってしまう不具合が
    # 実運用で確認された（ウィンドウタイトルが実行中のコマンドそのもの
    # 「find /I "..."」になった状態でスタックする）。この状態では
    # バッチスクリプトの以降の処理（バックアップ削除・自己削除等）に
    # 進めず、結果としてアップデートが実際には適用されない。
    #
    # CREATE_NO_WINDOW は「コンソールを一切生成しない」ことを明示的に
    # 指示するフラグで、cmd.exe がパイプ処理のために子コンソールを
    # 生成しようとするケースを含めて確実に非表示にできるため、
    # DETACHED_PROCESS よりこの用途に適している。
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )

    # 自分自身（現在起動中のexe）を終了する。
    # ここで確実にプロセスを終了させないと、.bat側のリネーム／copyが
    # ファイルロックのため失敗し続けてしまう。
    os._exit(0)


# ═══════════════════════════════════════════════════════════════════════
#  GUI連携用の簡易ヘルパー（tkinter / customtkinter 想定）
# ═══════════════════════════════════════════════════════════════════════

def check_and_prompt_update(
    parent_window,
    log_callback: Optional[Callable[[str, str], None]] = None,
    silent_if_up_to_date: bool = False,
) -> None:
    """
    「アップデートを確認」ボタンから呼び出す想定のヘルパー。
    tkinter の messagebox を使ってユーザーに確認・通知を行う。

    Parameters
    ----------
    parent_window : tkinter.Tk / customtkinter.CTk
        メッセージボックスの親ウィンドウ。
    log_callback : Callable[[str, str], None], optional
        GUIのログ欄などに進捗を出したい場合に渡す。
    silent_if_up_to_date : bool
        True の場合、既に最新バージョンであってもメッセージボックスを
        出さない（アプリ起動時の自動チェックなど、ユーザーの操作を
        伴わない場面での利用を想定）。
    """
    from tkinter import messagebox

    def _log(msg, level="INFO"):
        if log_callback:
            log_callback(msg, level)

    try:
        manifest = check_for_update()
    except Exception as e:
        _log(f"アップデートの確認に失敗しました: {e}", "ERROR")
        messagebox.showerror(
            "アップデート確認エラー",
            f"アップデート情報の取得に失敗しました。\n\n{e}",
            parent=parent_window,
        )
        return

    if manifest is None:
        _log(f"現在のバージョン（{CURRENT_VERSION}）は最新です。", "INFO")
        if not silent_if_up_to_date:
            messagebox.showinfo(
                "アップデート確認",
                f"お使いのバージョン（{CURRENT_VERSION}）は最新です。",
                parent=parent_window,
            )
        return

    notes = manifest.get("notes", "")
    remote_version = manifest.get("version", "?")
    proceed = messagebox.askyesno(
        "アップデートがあります",
        f"新しいバージョン {remote_version} が利用可能です"
        f"（現在: {CURRENT_VERSION}）。\n\n"
        f"更新内容:\n{notes}\n\n"
        "今すぐアップデートしますか？\n"
        "（アプリが自動的に再起動します）",
        parent=parent_window,
    )
    if not proceed:
        return

    try:
        download_and_apply_update(manifest, log_callback=log_callback)
        # 正常系ではここに到達する前に os._exit(0) でプロセスが終了する。
    except Exception as e:
        _log(f"アップデートの適用に失敗しました: {e}", "ERROR")
        messagebox.showerror(
            "アップデート失敗",
            f"アップデートの適用中にエラーが発生しました。\n\n{e}",
            parent=parent_window,
        )