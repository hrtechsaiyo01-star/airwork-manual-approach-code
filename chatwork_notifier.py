import json
import os
import sys
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import requests

CHATWORK_API_BASE = "https://api.chatwork.com/v2"
CONFIG_FILENAME = "chatwork_config.json"


def _exe_dir() -> str:
    """exe実行時はexeと同じフォルダ、python実行時はこのファイルと同じフォルダ。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_path() -> str:
    return os.path.join(_exe_dir(), CONFIG_FILENAME)


def _load_config() -> Dict[str, str]:
    path = config_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {path}\n"
            f"chatwork_config.json.example をコピーして {CONFIG_FILENAME} を作成し、"
            "api_token 等を設定してください。"
        )
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    required = ["api_token", "room_id", "boss_account_id", "boss_name"]
    missing = [k for k in required if not str(cfg.get(k, "")).strip()]
    if missing:
        raise ValueError(
            f"{CONFIG_FILENAME} に次の項目が未設定です: {missing}"
        )
    cfg["test_mode"] = bool(cfg.get("test_mode", False))
    return cfg


class ChatworkNotifier:
    """
    Chatworkへの通知を担当するクラス。

    設定ファイルが無い/不正な場合でもインスタンス生成自体は失敗させず、
    通知機能だけを無効化する（＝手動アプローチBot本体の起動・実行を
    妨げないため）。
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        self._log_cb = log_callback or (lambda msg, level="INFO": print(f"[{level}] {msg}"))
        try:
            self._cfg = _load_config()
            self.enabled = True
            if self._cfg.get("test_mode"):
                self._log(
                    "Chatwork通知は test_mode で動作しています"
                    "（上司へのメンションなし、メッセージ先頭に🧪テスト表記）。",
                    "WARN",
                )
        except Exception as e:
            self._log(
                f"Chatwork通知は無効化されています（設定未完了）: {e}",
                "WARN",
            )
            self._cfg = {}
            self.enabled = False

    def _log(self, msg: str, level: str = "INFO"):
        try:
            self._log_cb(msg, level)
        except Exception:
            print(f"[{level}] {msg}")

    def _tag_boss(self) -> str:
        """
        test_mode の場合はメンションを一切付けない（誤って本番roomのまま
        テストしても上司に通知が飛ばないようにするため）。
        """
        if self._cfg.get("test_mode"):
            return f"（テストモード：本来ここに{self._cfg['boss_name']}さんへの" \
                   f"メンションが入ります）"
        return f"[To:{self._cfg['boss_account_id']}]{self._cfg['boss_name']}さん"

    def _finalize_body(self, body: str) -> str:
        """
        ★ v40で追加。
        test_mode が有効な場合に、実際に送信される本文へ必ず付与される
        目立つテスト表記を適用する。プレビュー表示（GUIの確認ダイアログ）
        と実際の送信の両方がこのメソッドを経由することで、「プレビューで
        見た文面」と「実際に送信される文面」が完全に一致することを
        保証する。
        """
        if self._cfg.get("test_mode"):
            return "🧪【テスト通知】このメッセージはテストモードで送信されました。\n\n" + body
        return body

    def _post(self, body: str, max_attempts: int = 3) -> bool:
        """
        ★ v40で追加（旧 `_send` の送信部分のみを切り出したもの）。
        既に最終形になっている本文（test_modeの表記も含め、これ以上
        書き換えない状態）を、そのままChatwork APIへリトライ付きで
        送信する。通知の送信失敗は bot 本体の処理を止めてはいけない
        ため、例外は投げず bool を返すだけにする。
        """
        if not self.enabled:
            return False

        url = f"{CHATWORK_API_BASE}/rooms/{self._cfg['room_id']}/messages"
        headers = {"X-ChatWorkToken": self._cfg["api_token"]}

        last_err = ""
        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    url, headers=headers, data={"body": body}, timeout=10
                )
                if resp.status_code == 200:
                    return True
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                last_err = str(e)

            if attempt < max_attempts:
                time.sleep(2.0 * attempt)

        self._log(f"Chatwork通知の送信に失敗しました: {last_err}", "WARN")
        return False

    def render_preview(self, body: str) -> str:
        """
        ★ v40で追加。
        まだ送信していない本文（`build_summary_body()` 等が返す生の
        テキスト）を受け取り、実際に送信されるのとまったく同じ最終形
        （test_mode表記込み）に変換して返す。GUIの確認ダイアログでの
        プレビュー表示専用（このメソッド自体は送信しない）。
        """
        return self._finalize_body(body)

    def send_prebuilt(self, body: str) -> bool:
        """
        ★ v40で追加。
        既に組み立て済みの生の本文（test_mode表記が付く前のもの）を
        受け取り、`_finalize_body()` で最終形にしてから実際に送信する。
        GUIの「報告を送信」ボタンが、直前に `render_preview()` で
        ユーザーに見せたのと完全に同じ内容を送信するために使う
        （生成し直すのではなく、プレビュー時に組み立てた本文を
        そのまま渡すことで、プレビューと送信内容の不一致を防ぐ）。
        """
        return self._post(self._finalize_body(body))

    def _send(self, body: str, max_attempts: int = 3) -> bool:
        """
        後方互換用ラッパー。生の本文を受け取り、test_mode処理と送信を
        まとめて行う（従来の `_send()` と同じ動作）。
        """
        return self._post(self._finalize_body(body), max_attempts=max_attempts)

    # ─────────────────────────────────────────────────────────────
    #  即時通知：重複送信リスク等、放置できない重大エラー
    # ─────────────────────────────────────────────────────────────
    def notify_critical_error(
        self,
        title: str,
        company: str,
        job_id: str,
        row_idx: int,
        detail: str,
        sheet_url: str = "",
    ) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            self._tag_boss(),
            "",
            f"🔴【要確認】{title}",
            "",
            f"会社　　: {company}",
            f"求人番号: {job_id}",
            f"シート行: {row_idx}",
            f"発生時刻: {now}",
            "",
            "内容:",
            detail,
        ]
        if sheet_url:
            lines += ["", f"シート: {sheet_url}"]
        return self._send("\n".join(lines))

    # ─────────────────────────────────────────────────────────────
    #  実行ごとのサマリー通知本文の組み立て（★ v40: 送信処理から分離）
    # ─────────────────────────────────────────────────────────────
    def build_summary_body(
        self,
        total_in_sheet: int,
        bot_processed_count: int,
        done_count: int,
        need_confirm_rows: List[Dict[str, str]],
        job_not_found_count: int,
        no_candidates_count: int,
        no_matching_candidates_count: int = 0,
        not_fulltime_count: int = 0,
        unpublished_count: int = 0,
        still_pending_count: int = 0,
        other_count: int = 0,
        no_candidates_detail_rows: Optional[List[Dict[str, str]]] = None,
        not_fulltime_detail_rows: Optional[List[Dict[str, str]]] = None,
        sheet_url: str = "",
        max_detail_rows: int = 10,
    ) -> str:
        """
        ★ v37で更新、v40で `notify_summary()` から分離。
        実行結果サマリーの本文（test_mode表記が付く前の生のテキスト）を
        組み立てて返す。送信はしない。

        GUIの「報告を送信」ボタンがこの生の本文を使って
        `render_preview()` でプレビュー表示し、ユーザー確認後に
        `send_prebuilt()` で送信することで、プレビューと実際の送信内容が
        完全に一致することを保証できるようにするために、送信処理
        （`_post`/`_finalize_body`）とは独立させた。

        `total_in_sheet` はシート全体（対応必要以外も含む全行）の件数、
        `bot_processed_count` は今回のrun()でbotが実際に処理を試みた
        （＝実行開始時点で「対応必要」だった）件数。この2つを分けて
        見せることで、上司は「シート全体で今どういう状況か」と
        「botが今回どれだけ動いたか」の両方を把握できる。
        以降の各カテゴリ件数（対応済み・確認必要 等）は、bot が今回
        処理した行だけでなく、シートに既存の（過去の実行やユーザーの
        手動対応による）値も含めた、シート全体での現状を表す。
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            self._tag_boss(),
            "",
            f"📋 手動アプローチBot 実行結果（{now}）",
            "",
            f"シート総数: {total_in_sheet}件",
            f"　└ 今回botが処理: {bot_processed_count}件",
        ]
        manual_or_existing = total_in_sheet - bot_processed_count
        if manual_or_existing > 0:
            lines.append(f"　└ 既存（前回までの結果・手動対応等）: {manual_or_existing}件")
        lines += [
            "",
            f"✅ 対応済み: {done_count}件",
            f"⚠️ 確認必要: {len(need_confirm_rows)}件",
            f"❌ 求人ID見つからない: {job_not_found_count}件",
            f"🚫 候補者を表示できません: {no_candidates_count}件",
            f"🔍 条件に合う候補者がいない: {no_matching_candidates_count}件",
            f"👤 正社員以外: {not_fulltime_count}件",
            f"📴 未掲載: {unpublished_count}件",
        ]
        # ★ v32: 上記いずれのカテゴリにも分類されなかった行（処理中に
        #   スキップされた、途中で停止された等）がある場合、件数の
        #   合計が処理件数と食い違って見えて混乱を招くため、差分を
        #   「その他/未処理」として明示する。0件のときは表示しない。
        if other_count > 0:
            lines.append(f"❔ その他/未処理: {other_count}件")
        # ★ v37: 「対応必要」のまま残っている行（bot が今回未着手・
        #   途中停止等）も上司に分かるように表示する。0件なら表示しない。
        if still_pending_count > 0:
            lines.append(f"🕐 対応必要のまま（未処理）: {still_pending_count}件")

        if need_confirm_rows:
            lines += ["", "── 確認必要の詳細 ──"]
            for item in need_confirm_rows[:max_detail_rows]:
                lines.append(f"行{item['row_idx']}: {item['company']}（{item['job_id']}）")
                lines.append(f"　→ {item['reason']}")
            remaining = len(need_confirm_rows) - max_detail_rows
            if remaining > 0:
                lines.append(f"（他{remaining}件はシート参照）")

        # ★ v33: 「候補者を表示できません」のうち、具体的な理由が付いて
        #   いる行（自動リトライ上限まで解消しなかった「掲載中なのに
        #   ボタン操作不可」等）は、件数だけでなく理由も報告する。
        #   これにより、ステータス上は「候補者を表示できません」に
        #   なっていても、実際の原因（掲載中なのにボタンが押せない状態が
        #   続いている等）が上司に伝わるようにする。
        if no_candidates_detail_rows:
            lines += ["", "── 候補者を表示できませんの詳細 ──"]
            for item in no_candidates_detail_rows[:max_detail_rows]:
                lines.append(f"行{item['row_idx']}: {item['company']}（{item['job_id']}）")
                lines.append(f"　→ {item['reason']}")
            remaining = len(no_candidates_detail_rows) - max_detail_rows
            if remaining > 0:
                lines.append(f"（他{remaining}件はシート参照）")

        # ★ v34: 「正社員以外」はシート上は詳細を持たないため、
        #   Chatworkの報告でのみ具体的な雇用形態を表示する。
        if not_fulltime_detail_rows:
            lines += ["", "── 正社員以外の詳細 ──"]
            for item in not_fulltime_detail_rows[:max_detail_rows]:
                lines.append(f"行{item['row_idx']}: {item['company']}（{item['job_id']}）")
                lines.append(f"　→ 正社員以外（{item['reason']}）")
            remaining = len(not_fulltime_detail_rows) - max_detail_rows
            if remaining > 0:
                lines.append(f"（他{remaining}件はシート参照）")

        if sheet_url:
            lines += ["", f"シート: {sheet_url}"]

        return "\n".join(lines)

    def notify_summary(
        self,
        total_in_sheet: int,
        bot_processed_count: int,
        done_count: int,
        need_confirm_rows: List[Dict[str, str]],
        job_not_found_count: int,
        no_candidates_count: int,
        no_matching_candidates_count: int = 0,
        not_fulltime_count: int = 0,
        unpublished_count: int = 0,
        still_pending_count: int = 0,
        other_count: int = 0,
        no_candidates_detail_rows: Optional[List[Dict[str, str]]] = None,
        not_fulltime_detail_rows: Optional[List[Dict[str, str]]] = None,
        sheet_url: str = "",
        max_detail_rows: int = 10,
    ) -> bool:
        """
        ★ v40で更新。
        `build_summary_body()` で本文を組み立て、そのまま送信する
        従来どおりの一括処理版（run() から即座に送りたい場合や、
        テストスクリプトからの直接送信に使う）。
        GUIの「プレビュー確認してから送信」フローでは、代わりに
        `build_summary_body()` → `render_preview()` →（ユーザー確認）→
        `send_prebuilt()` の順に個別に呼び出す。
        """
        body = self.build_summary_body(
            total_in_sheet=total_in_sheet,
            bot_processed_count=bot_processed_count,
            done_count=done_count,
            need_confirm_rows=need_confirm_rows,
            job_not_found_count=job_not_found_count,
            no_candidates_count=no_candidates_count,
            no_matching_candidates_count=no_matching_candidates_count,
            not_fulltime_count=not_fulltime_count,
            unpublished_count=unpublished_count,
            still_pending_count=still_pending_count,
            other_count=other_count,
            no_candidates_detail_rows=no_candidates_detail_rows,
            not_fulltime_detail_rows=not_fulltime_detail_rows,
            sheet_url=sheet_url,
            max_detail_rows=max_detail_rows,
        )
        return self._send(body)
