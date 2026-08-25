import os
import re
import webbrowser
import threading
from datetime import datetime
from typing import Optional, Callable

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog

from bot_core import load_config, save_config
from config_loader import ConfigLoader, resource_path
from airwork_manual_approach import (
    AirWorkManualApproach,
    MANUAL_APPROACH_SHEET_ID,
    MANUAL_APPROACH_SHEET_URL,
    extract_sheet_id,
)
import updater

# ★ アップデート機能: バージョン番号は updater.py の CURRENT_VERSION を
#   唯一の管理場所とする（ここと二重管理にならないようにするため）。
#   新しいバージョンをリリースする際は updater.py の CURRENT_VERSION
#   だけを書き換えればよい。
APP_VERSION = updater.CURRENT_VERSION

# ── Design Tokens（メインツールと統一） ──────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG           = "#F8FAFC"
ACCENT       = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
GRAY         = "#64748B"
GRAY_HOVER   = "#475569"
GREEN        = "#16A34A"
GREEN_HOVER  = "#15803D"
RED          = "#DC2626"
TEXT_DK      = "#1F2937"
TEXT_MD      = "#475569"
TEXT_LT      = "#94A3B8"
CARD         = "#FFFFFF"
BORDER       = "#E2E8F0"
INPUT_BG     = "#F1F5F9"
LOG_BG       = "#111827"
LOG_FG       = "#60A5FA"

FH1   = ("Helvetica Neue", 17, "bold")
FH2   = ("Helvetica Neue", 14, "bold")
FBOD  = ("Helvetica Neue", 13)
FBTN  = ("Helvetica Neue", 13, "bold")
FMONO = ("Menlo", 11)
FSM   = ("Helvetica Neue", 11)


def _shade(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


# ══════════════════════════════════════════════════════════════════════════
#  UI Helpers（メインツールと同じ見た目にするため一部を流用）
# ══════════════════════════════════════════════════════════════════════════
def page_frame(parent) -> ctk.CTkScrollableFrame:
    p = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
    p.pack(fill="both", expand=True)
    return p


def section(parent, text: str):
    frm = ctk.CTkFrame(parent, fg_color="transparent")
    frm.pack(fill="x", padx=24, pady=(20, 6))
    ctk.CTkLabel(frm, text=text, text_color=TEXT_DK, font=FH2).pack(side="left")
    ctk.CTkFrame(frm, fg_color=BORDER, height=1).pack(
        side="left", fill="x", expand=True, padx=(12, 0))


def card(parent, pad_bottom=12) -> ctk.CTkFrame:
    f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                     border_width=1, border_color=BORDER)
    f.pack(fill="x", padx=24, pady=(0, pad_bottom))
    return f


def entry_row(parent, label: str, var: tk.StringVar,
              show="", width=320) -> ctk.CTkEntry:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=7)
    ctk.CTkLabel(row, text=label, text_color=TEXT_MD, font=FBOD,
                 width=210, anchor="w").pack(side="left")
    e = ctk.CTkEntry(row, textvariable=var, show=show, width=width,
                     font=FBOD, fg_color=INPUT_BG, border_color=BORDER,
                     border_width=1, text_color=TEXT_DK, height=38,
                     corner_radius=8)
    e.pack(side="left", fill="x", expand=True)
    return e


def action_btn(parent, text: str, cmd: Callable,
               color=ACCENT, width=160, state="normal") -> ctk.CTkButton:
    b = ctk.CTkButton(parent, text=text, command=cmd,
                      fg_color=color, hover_color=_shade(color, 0.85),
                      text_color="white", font=FBTN,
                      height=42, width=width, corner_radius=9, state=state)
    b.pack(side="left", padx=(0, 10))
    return b


def hint_label(parent, text: str):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=18, pady=(0, 10))
    ctk.CTkLabel(f, text=text, text_color=TEXT_LT, font=FSM,
                 justify="left", anchor="w").pack(side="left")


def log_widget(parent, height=260) -> ctk.CTkTextbox:
    box = ctk.CTkTextbox(parent, height=height, font=FMONO,
                         fg_color=LOG_BG, text_color=LOG_FG,
                         corner_radius=10, wrap="word",
                         border_width=0)
    box.pack(fill="both", expand=True)
    box.configure(state="disabled")

    ctrl = ctk.CTkFrame(parent, fg_color="transparent")
    ctrl.pack(fill="x", pady=(6, 0))

    def clear():
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.configure(state="disabled")

    def download():
        content = box.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("ログ保存", "保存するログがありません。")
            return
        default_name = f"manual_approach_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(
            title="ログを保存",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("ログ保存", f"ログを保存しました:\n{path}")
        except Exception as e:
            messagebox.showerror("ログ保存エラー", f"保存に失敗しました:\n{e}")

    ctk.CTkButton(ctrl, text="ログをクリア", command=clear,
                  fg_color="#334155", hover_color="#475569",
                  text_color=TEXT_LT, font=FSM, height=28, width=110,
                  corner_radius=6).pack(side="right")

    ctk.CTkButton(ctrl, text="⬇  ログを保存", command=download,
                  fg_color="#334155", hover_color="#475569",
                  text_color=TEXT_LT, font=FSM, height=28, width=120,
                  corner_radius=6).pack(side="right", padx=(0, 8))
    return box


def log_write(box: ctk.CTkTextbox, msg: str, level="INFO"):
    colors = {"INFO": LOG_FG, "WARN": "#FCD34D",
              "ERROR": "#F87171", "OK": "#4ADE80"}
    box.configure(state="normal")
    box.insert("end", f"[{level}] {msg}\n", level)
    box.tag_config(level, foreground=colors.get(level, LOG_FG))
    box.configure(state="disabled")
    box.see("end")


# ══════════════════════════════════════════════════════════════════════════
#  設定の読み込み
#
#  ★ v1.0.6: 手動アプローチタブは Config タブの列定義（sheet_id /
#  config_tab）を一切使わない。config.json が存在すれば参考表示だけに
#  使うが、無くても・空でも実行をブロックしない。
#
#  ★ v1.2.0: 処理対象シートのリンク/タブ名をユーザーがGUIから編集・
#  保存できるようにするための状態をここで管理する。
# ══════════════════════════════════════════════════════════════════════════
class RuntimeSettings:
    def __init__(self):
        # config.json の読み込みに失敗しても起動をブロックしない
        # （このアプリはそもそも sheet_id / config_tab を必要としない）。
        try:
            cfg = load_config()
        except Exception:
            cfg = {}
        self.sheet_id: str   = (cfg.get("sheet_id") or "").strip()
        self.config_tab: str = (cfg.get("config_tab") or "").strip()
        self.headless        = tk.BooleanVar(value=cfg.get("headless", True))

        # ★ v1.2.0で追加。
        # 処理対象シートのリンク/タブ名。未設定の場合は
        # コード内の既定値（MANUAL_APPROACH_SHEET_URL / 空欄=先頭タブ）
        # をそのまま初期値として使う。
        self.manual_target_link = tk.StringVar(
            value=(cfg.get("manual_target_sheet_link") or MANUAL_APPROACH_SHEET_URL)
        )
        self.manual_target_tab = tk.StringVar(
            value=(cfg.get("manual_target_tab_name") or "")
        )

        # ★ v1.3.0で追加。
        # 「実行」ボタンを押した際に、run() 完了後自動で「報告を送信」の
        # プレビュー確認ダイアログまで進めるかどうか。
        # 意図的に load_config() / save_config() のどちらにも関与させて
        # いない（cfg から読み込まない・cfg に書き込まない）。誤って
        # チェックしたまま保存され、次回起動時も自動的に有効になって
        # しまう事故を防ぐための設計（「危険」チェックボックスと同様の方針）。
        self.auto_report = tk.BooleanVar(value=False)

        # ★ 「危険」チェックボックス用の状態。
        # 意図的に load_config() / save_config() のどちらにも一切
        # 関与させていない（cfg から読み込まない・cfg に書き込まない）。
        # そのためアプリを再起動する（exeを開き直す）たびに、必ず
        # False（未チェック）から始まる。チェックしたまま保存されて
        # 次回起動時も有効になってしまう、という事故を防ぐための設計。
        self.skip_report_confirm = tk.BooleanVar(value=False)

    def make_loader(self) -> Optional[ConfigLoader]:
        """
        sheet_id / config_tab が両方揃っている場合のみ、参考として
        メインツールの ConfigLoader を作って渡す。無い場合は None を
        返し、AirWorkManualApproach 側のデフォルト実装
        （_make_default_config_loader() → ConfigLoader()）に任せる。
        このタブでは Config タブの列定義を一切参照しないため、
        どちらの経路でも動作に違いは無い。
        """
        if self.sheet_id and self.config_tab:
            try:
                return ConfigLoader(
                    sheet_id        = self.sheet_id,
                    config_tab_name = self.config_tab,
                )
            except Exception:
                return None
        return None

    def resolved_sheet_id(self) -> str:
        """
        ★ v1.2.0で追加。
        `manual_target_link` に入力された値（URL全体でもID単体でも）から
        実際に使うスプレッドシートIDを解決する。空欄の場合は
        `MANUAL_APPROACH_SHEET_ID`（コード内の既定値）にフォールバック
        する。
        """
        raw = self.manual_target_link.get().strip()
        if not raw:
            return MANUAL_APPROACH_SHEET_ID
        return extract_sheet_id(raw) or MANUAL_APPROACH_SHEET_ID

    def resolved_tab_name(self) -> str:
        """空欄なら空文字のまま返す（AirWorkManualApproach側で
        「先頭タブを使う」という意味に解釈される）。"""
        return self.manual_target_tab.get().strip()

    def save_manual_target(self):
        """
        ★ v1.2.0で追加。
        処理対象シートのリンク/タブ名の変更を ~/.airwork_bot_config.json
        へ永続化する。次回起動時に自動で復元される。
        メインツール側が使う既存のキー（sheet_id / config_tab / headless
        等）を上書きしないよう、既存の設定を読み込んでから該当キーだけを
        更新して書き戻す。
        """
        try:
            cfg = load_config()
        except Exception:
            cfg = {}
        cfg["manual_target_sheet_link"] = self.manual_target_link.get().strip()
        cfg["manual_target_tab_name"] = self.manual_target_tab.get().strip()
        save_config(cfg)


# ══════════════════════════════════════════════════════════════════════════
#  メイン画面
# ══════════════════════════════════════════════════════════════════════════
class ManualApproachApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title(f"AirWork 手動アプローチ  v{APP_VERSION}")
        self.root.geometry("760x760")
        self.root.minsize(640, 560)
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.settings = RuntimeSettings()
        self.worker: Optional[AirWorkManualApproach] = None
        self.btn_start: Optional[ctk.CTkButton] = None
        self.btn_stop:  Optional[ctk.CTkButton] = None
        self.btn_report: Optional[ctk.CTkButton] = None
        self.btn_update: Optional[ctk.CTkButton] = None
        self.log: Optional[ctk.CTkTextbox] = None

        self._build()

        # ★ アップデート機能: 起動時に自動でバックグラウンドチェックする
        #   （既に最新バージョンならメッセージボックスは出さない＝
        #   silent_if_up_to_date=True）。ネットワークが無い環境でも
        #   起動をブロックしないよう、別スレッドで実行する。
        self.root.after(1500, self._auto_check_update)

    # ── ログ / 実行状態 ─────────────────────────────────────────────
    def _log(self, msg, level="INFO"):
        if self.log is not None:
            self.root.after(0, log_write, self.log, msg, level)

    def _set_running(self, running: bool):
        if self.btn_start is not None:
            self.root.after(0, lambda: self.btn_start.configure(
                state="disabled" if running else "normal"))
        if self.btn_stop is not None:
            self.root.after(0, lambda: self.btn_stop.configure(
                state="normal" if running else "disabled"))
        # ★ v1.1.0: 実行中は「報告を送信」ボタンも押せないようにする
        #   （実行結果が確定していない状態で送信されるのを防ぐため）。
        if running and self.btn_report is not None:
            self.root.after(0, lambda: self.btn_report.configure(state="disabled"))

    def _refresh_report_button_state(self):
        """
        ★ v1.1.0で追加。
        run() が終了した直後に呼び出し、「報告を送信」ボタンを
        有効化してよいかどうかを判定する。直近の run() が1件以上の
        対象行を処理していた場合のみ有効化する。
        """
        if self.btn_report is None:
            return
        enabled = bool(self.worker is not None and self.worker.has_report_available())
        self.btn_report.configure(state="normal" if enabled else "disabled")

    # ── 画面構築 ─────────────────────────────────────────────────────
    def _build(self):
        p = page_frame(self.root)

        # タイトル
        title_frm = ctk.CTkFrame(p, fg_color="transparent")
        title_frm.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(title_frm, text="🖐️  AirWork 手動アプローチ",
                     text_color=TEXT_DK, font=FH1).pack(anchor="w")

        version_row = ctk.CTkFrame(title_frm, fg_color="transparent")
        version_row.pack(anchor="w")
        ctk.CTkLabel(version_row, text=f"v{APP_VERSION}（単独アプリ）",
                     text_color=TEXT_LT, font=FSM).pack(side="left")
        self.btn_update = ctk.CTkButton(
            version_row, text="🔄  アップデートを確認",
            command=self._manual_check_update,
            fg_color="transparent", hover_color=BORDER,
            text_color=ACCENT, font=FSM, height=22, width=140,
            corner_radius=6, border_width=0,
        )
        self.btn_update.pack(side="left", padx=(10, 0))

        # ── 参考情報バッジ（★ v1.0.6: 未設定でも表示するだけ。実行には
        #    影響しない）──────────────────────────────────────────
        badge_frm = ctk.CTkFrame(p, fg_color="transparent")
        badge_frm.pack(fill="x", padx=24, pady=(4, 0))
        if self.settings.sheet_id and self.settings.config_tab:
            badge_text = (
                f"ℹ️  参考: メインツールの config.json を検出 "
                f"（シートID {self.settings.sheet_id} / タブ「{self.settings.config_tab}」）"
                "※このアプリの動作には使用しません"
            )
        else:
            badge_text = (
                "ℹ️  このアプリはメインツールの ⚙️設定（スプレッドシートID / "
                "Config タブ）を必要としません。そのまま「実行」できます。"
            )
        ctk.CTkLabel(
            badge_frm, text=badge_text,
            text_color=TEXT_LT, font=FSM,
        ).pack(anchor="w")

        # ── 手動アプローチ本体 ─────────────────────────────────────
        section(p, "🖐️  手動アプローチ")
        c = card(p)
        ctk.CTkLabel(
            c,
            text=(
                "専用のスプレッドシート（会社ごとの AirID / パスワード /\n"
                "求人番号 / アプローチ上限数 / 検索条件）を読み込み、\n"
                "「対応必要」の行を自動処理します。"
            ),
            text_color=TEXT_LT, font=FSM, justify="left",
        ).pack(anchor="w", padx=18, pady=(14, 6))

        # ★ v1.2.0で追加: 処理対象シートのリンク/タブ名を編集できる
        #   入力欄。空欄のままなら、コード内の既定値
        #  （MANUAL_APPROACH_SHEET_ID / 先頭タブ）が使われる。
        entry_row(
            c, "📄  シートのリンク / ID",
            self.settings.manual_target_link, width=380,
        )
        entry_row(
            c, "📑  タブ名（空欄で先頭タブ）",
            self.settings.manual_target_tab, width=380,
        )

        link_btn_row = ctk.CTkFrame(c, fg_color="transparent")
        link_btn_row.pack(fill="x", padx=18, pady=(0, 4))

        # ★ v1.3.0: 「ID をコピー」ボタンは削除した（IDが必要な場合は
        #   「シートを開く」で開いたブラウザのアドレスバーから確認できる
        #   ため、ボタンを2つ並べるほどの必要性が薄いと判断）。
        ctk.CTkButton(
            link_btn_row, text="🔗  シートを開く", command=self._open_target_sheet,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_LT, font=FSM, height=26, width=120,
            corner_radius=6,
        ).pack(side="left")

        ctk.CTkButton(
            link_btn_row, text="💾  設定を保存", command=self._save_target_settings,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_LT, font=FSM, height=26, width=110,
            corner_radius=6,
        ).pack(side="left", padx=(8, 0))

        hint_label(
            c,
            "※ URLをそのまま貼り付けても、IDだけを貼り付けても動作します。\n"
            "   タブ名を空欄にすると、シートの一番左のタブを使用します。\n"
            "   入力内容は「実行」を押した時点でも自動的に保存されます。\n"
            "   （AirID・パスワードは対象シートの D列/E列を使用します）",
        )

        section(p, "⚙️  実行")
        c2 = card(p)
        row = ctk.CTkFrame(c2, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)
        self.btn_start = action_btn(row, "実行", self._start, ACCENT, width=180)
        self.btn_stop  = action_btn(row, "■  停止", self._stop, RED, width=120, state="disabled")
        # ★ v1.1.0: 実行結果のChatwork報告は、run() 終了時に自動送信する
        #   のではなく、ユーザーがシート内容を確認（kakunin）した後、
        #   任意のタイミングでこのボタンを押して送信する方式に変更した。
        #   run() 実行前・実行対象0件の場合は無効化しておく。
        self.btn_report = action_btn(
            row, "📮  報告を送信", self._send_report, GREEN, width=160, state="disabled"
        )

        # ★ v1.3.0で追加。
        # 従来の「🚀 実行して報告まで自動で行う」ボタンをこのチェック
        # ボックスに統合した。チェックを入れた状態で「実行」を押すと、
        # run() 完了後に自動で報告プレビュー確認ダイアログまで進む
        # （Chatworkへの実際の送信直前の最終確認ダイアログは従来どおり
        # 残るため、誤送信のリスクは変わらない）。
        auto_report_row = ctk.CTkFrame(c2, fg_color="transparent")
        auto_report_row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkCheckBox(
            auto_report_row, text="実行後に自動で報告する（完了後、報告内容の確認ダイアログを表示）",
            variable=self.settings.auto_report,
            font=FBOD, text_color=TEXT_MD,
            checkbox_width=18, checkbox_height=18,
            corner_radius=4,
            fg_color=GREEN, hover_color=GREEN_HOVER,
        ).pack(anchor="w")

        # ── ⚠️ 危険設定: 送信前の最終確認ダイアログをスキップ ─────────
        danger_frm = ctk.CTkFrame(
            c2, fg_color="#FEF2F2", corner_radius=8,
            border_width=1, border_color="#FCA5A5",
        )
        danger_frm.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkCheckBox(
            danger_frm,
            text="⚠️ 危険: 報告送信前の確認ダイアログを省略し、そのままChatworkへ自動送信する",
            variable=self.settings.skip_report_confirm,
            font=FBOD, text_color=RED,
            checkbox_width=18, checkbox_height=18,
            corner_radius=4,
            fg_color=RED, hover_color=_shade(RED, 0.85),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            danger_frm,
            text=(
                "シートの「確認必要」行を見直す前に報告が送信される可能性があります。\n"
                "この設定はアプリを終了・再起動すると必ずOFFに戻ります（保存されません）。"
            ),
            text_color="#B91C1C", font=FSM, justify="left", anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 10))
        ctk.CTkCheckBox(
            c2, text="画面表示",
            variable=self.settings.headless,
            font=FBOD, text_color=TEXT_MD,
            checkbox_width=18, checkbox_height=18,
            corner_radius=4,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=18, pady=(0, 14))
        hint_label(
            c2,
            "※「報告を送信」は、実行後にシートの「確認必要」等の行を\n"
            "   確認・修正してから押してください。押した時点のシートの\n"
            "   最新状態を読み直してから上司へ報告します。",
        )

        section(p, "📋  ログ")
        log_frm = ctk.CTkFrame(p, fg_color="transparent")
        log_frm.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.log = log_widget(log_frm)

    # ── 処理対象シート設定 ───────────────────────────────────────────
    def _open_target_sheet(self):
        """
        ★ v1.2.0で追加。
        入力欄の現在の値からスプレッドシートIDを解決し、ブラウザで開く。
        """
        sheet_id = self.settings.resolved_sheet_id()
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        webbrowser.open(url)

    def _save_target_settings(self):
        """
        ★ v1.2.0で追加。
        「💾 設定を保存」ボタンから呼ばれる。入力欄の現在の値を
        ~/.airwork_bot_config.json に永続化し、完了を知らせる。
        """
        self.settings.save_manual_target()
        messagebox.showinfo(
            "保存完了",
            "処理対象シートのリンク/タブ名を保存しました。\n"
            "次回起動時にも自動的に復元されます。",
        )

    # ── アップデート ───────────────────────────────────────────────
    def _manual_check_update(self):
        """
        「🔄 アップデートを確認」ボタンから呼ばれる。
        ユーザーが明示的に押した操作なので、既に最新バージョンの場合も
        その旨をメッセージボックスで知らせる（silent_if_up_to_date=False）。
        通信を含むため別スレッドで実行し、UIをブロックしないようにする。
        """
        if self.btn_update is not None:
            self.btn_update.configure(state="disabled", text="🔄  確認中...")

        def run():
            try:
                updater.check_and_prompt_update(
                    self.root,
                    log_callback=self._log,
                    silent_if_up_to_date=False,
                )
            finally:
                if self.btn_update is not None:
                    self.root.after(
                        0,
                        lambda: self.btn_update.configure(
                            state="normal", text="🔄  アップデートを確認"
                        ),
                    )

        threading.Thread(target=run, daemon=True).start()

    def _auto_check_update(self):
        """
        起動時に自動で行うバックグラウンドチェック。
        既に最新バージョンの場合はユーザーに何も表示しない
        （silent_if_up_to_date=True）。エラーが起きても起動自体には
        影響させないよう、例外はログに残すのみとする。
        """
        def run():
            try:
                updater.check_and_prompt_update(
                    self.root,
                    log_callback=self._log,
                    silent_if_up_to_date=True,
                )
            except Exception as e:
                self._log(f"アップデートの自動確認に失敗しました: {e}", "WARN")

        threading.Thread(target=run, daemon=True).start()

    # ── アクション ───────────────────────────────────────────────────
    def _start(self):
        """
        「実行」ボタンから呼ばれる。

        ★ v1.3.0: 従来の「🚀 実行して報告まで自動で行う」専用ボタンを
        廃止し、「実行後に自動で報告する」チェックボックスの状態を見て
        after_run コールバックを組み立てるように変更した（挙動自体は
        従来のボタンと同一）。run() 完了後、チェックが入っていれば
        自動的に _send_report()（報告内容のプレビュー確認ダイアログ表示
        → 「はい」を選んだ場合のみChatworkへ送信）を呼び出す。
        """
        after_run = self._send_report if self.settings.auto_report.get() else None

        # ★ v1.2.0: 固定のMANUAL_APPROACH_SHEET_IDではなく、入力欄から
        #   解決した値を使う（入力欄が空欄なら既定値にフォールバックする
        #   ため、従来どおり何も入力しなくても動作する）。
        sheet_id = self.settings.resolved_sheet_id()
        tab_name = self.settings.resolved_tab_name()

        if not sheet_id or sheet_id == "PUT_YOUR_SHEET_ID_HERE":
            messagebox.showerror(
                "設定エラー",
                "処理対象スプレッドシートのリンク/IDが未設定です。\n"
                "「シートのリンク / ID」欄に入力するか、"
                "airwork_manual_approach.py の MANUAL_APPROACH_SHEET_ID を"
                "設定してください。",
            )
            return

        # ★ v1.2.0: 実行のたびに入力内容を自動保存する
        #  （「設定を保存」ボタンを押し忘れても次回起動時に復元されるように）。
        self.settings.save_manual_target()

        self._set_running(True)

        def run():
            try:
                sheet_url_for_log = (
                    f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
                )
                self._log(f"対象スプレッドシート: {sheet_url_for_log}", "INFO")
                if tab_name:
                    self._log(f"対象タブ: {tab_name}", "INFO")
                else:
                    self._log("対象タブ: 先頭タブ（未指定）", "INFO")
                loader = self.settings.make_loader()  # 無ければ None（デフォルトに委譲）
                self.worker = AirWorkManualApproach(
                    target_sheet_id = sheet_id,
                    target_tab_name = tab_name or None,
                    log_callback    = self._log,
                    headless        = self.settings.headless.get(),
                    config_loader   = loader,
                )
                self.worker.run()
            except Exception as e:
                self._log(f"エラー: {e}", "ERROR")
            finally:
                self._set_running(False)
                # ★ v1.1.0: 実行が終わったタイミングで「報告を送信」
                #   ボタンの有効/無効を更新する（対象行が1件以上あれば
                #   有効化）。
                self.root.after(0, self._refresh_report_button_state)
                # ★ 「実行後に自動で報告する」がONの場合、実行完了後に
                #   続けて報告フローを起動する。
                if after_run is not None:
                    self.root.after(0, after_run)

        threading.Thread(target=run, daemon=True).start()

    def _stop(self):
        if self.worker and hasattr(self.worker, "stop"):
            self.worker.stop()
        self._log("⏹ 停止リクエスト送信済み。", "WARN")
        if self.btn_stop is not None:
            self.btn_stop.configure(state="disabled")

    def _send_report(self):
        """
        ★ v1.1.0で追加。
        「📮 報告を送信」ボタンから呼ばれる。
        直近の run() が処理した行について、シートの最新状態を読み直して
        から報告文面を組み立て、実際にChatworkへ送信する内容をそのまま
        確認ダイアログにプレビュー表示する。ユーザーが「はい」を選んだ
        場合のみ実際に送信する。

        シート読み込み・Chatwork送信はいずれもネットワークI/Oを伴うため、
        UIをブロックしないよう別スレッドで行う。
        """
        if self.worker is None or not self.worker.has_report_available():
            messagebox.showinfo(
                "報告",
                "報告できる実行結果がありません。先に「実行」を行ってください。",
            )
            return

        if self.btn_report is not None:
            self.btn_report.configure(state="disabled", text="📮  内容を確認中...")

        def build_and_confirm():
            try:
                preview = self.worker.preview_report_text()
            except Exception as e:
                preview = None
                self._log(f"報告内容の作成に失敗しました: {e}", "ERROR")

            def ask_and_send():
                if self.btn_report is not None:
                    self.btn_report.configure(text="📮  報告を送信")

                if preview is None:
                    messagebox.showwarning(
                        "報告",
                        "報告内容の作成に失敗しました。ログを確認してください。",
                    )
                    self._refresh_report_button_state()
                    return

                # ★ 「危険」チェックボックスがONの場合、確認ダイアログを
                #   省略してそのまま送信する。誤操作防止のため、必ず
                #   ログにWARNで明示的に記録しておく。
                if self.settings.skip_report_confirm.get():
                    self._log(
                        "⚠️ 危険設定が有効なため、確認ダイアログを省略して"
                        "報告を自動送信します。",
                        "WARN",
                    )
                    confirmed = True
                else:
                    confirmed = messagebox.askyesno(
                        "報告を送信",
                        "以下の内容でChatworkに報告を送信します。よろしいですか？\n\n"
                        + preview,
                    )
                if not confirmed:
                    self._refresh_report_button_state()
                    return

                if self.btn_report is not None:
                    self.btn_report.configure(state="disabled", text="📮  送信中...")

                def send():
                    ok = False
                    try:
                        ok = self.worker.send_report()
                    finally:
                        def after_send():
                            if self.btn_report is not None:
                                self.btn_report.configure(text="📮  報告を送信")
                            self._refresh_report_button_state()
                            if ok:
                                messagebox.showinfo("報告", "Chatworkへの報告を送信しました。")
                            else:
                                messagebox.showwarning(
                                    "報告",
                                    "送信に失敗しました。ログを確認してください。",
                                )
                        self.root.after(0, after_send)

                threading.Thread(target=send, daemon=True).start()

            self.root.after(0, ask_and_send)

        threading.Thread(target=build_and_confirm, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        root = ctk.CTk()
        ManualApproachApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        try:
            import tkinter.messagebox as mb
            mb.showerror("起動エラー", f"{e}\n\n{traceback.format_exc()}")
        except Exception:
            print("起動エラー:", e)
            traceback.print_exc()