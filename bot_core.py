import json, os, time, re, logging, sys
from collections import defaultdict
from config_loader import ConfigLoader, FileConfig

# ── Logger（変更なし）────────────────────────────────────────────────────────
def _setup_logger():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "airwork_bot.log")
    logger = logging.getLogger("airwork_bot")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger, log_path
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG); fh.setFormatter(fmt); logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG); ch.setFormatter(fmt); logger.addHandler(ch)
    return logger, log_path

_LOGGER, _LOG_PATH = _setup_logger()
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".airwork_bot_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(data: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Config save error: {e}")

# ── COL dict（後方互換・page1〜4 の _get_cell で使用）────────────────────────
COL = {
    "status": 0, "I": 8, "J": 9, "K": 10, "L": 11, "M": 12, "N": 13,
    "O": 14, "P": 15, "Q": 16, "R": 17, "S": 18, "T": 19, "U": 20,
    "V": 21, "W": 22, "X": 23, "Y": 24, "Z": 25, "AA": 26, "AB": 27,
    "AC": 28, "AD": 29, "AE": 30, "AF": 31, "AG": 32, "AH": 33,
    "AI": 34, "AJ": 35, "AK": 36,
    "AL": 37, "AM": 38, "AN": 39, "AO": 40, "AP": 41, "AQ": 42,
    "AR": 43, "AS": 44, "AT": 45, "AU": 46, "AV": 47, "AW": 48,
    "AX": 49, "AY": 50, "AZ": 51, "BA": 52, "BB": 53,
    "BC": 54, "BD": 55, "BE": 56, "BF": 57,
    "BG": 58, "BH": 59, "BI": 60, "BJ": 61,
    "BK": 62, "BL": 63, "BM": 64, "BN": 65, "BO": 66, "BP": 67,
    "BQ": 68, "BR": 69, "BS": 70, "BT": 71, "BU": 72, "BV": 73,
    "BW": 74, "BX": 75, "BY": 76, "BZ": 77, "CA": 78, "CB": 79,
    "CC": 80, "CD": 81, "CE": 82, "CF": 83, "CG": 84, "CH": 85,
    "CI": 86, "CJ": 87, "CK": 88, "CL": 89, "CM": 90, "CN": 91,
    "CO": 92, "CP": 93, "CQ": 94, "CR": 95,
    "CT": 97, "CU": 98, "CV": 99, "CW": 100, "CX": 101, "CY": 102,
    "CZ": 103, "DA": 104, "DB": 105, "DC": 106, "DD": 107, "DE": 108,
    "DF": 109, "DG": 110, "DH": 111, "DI": 112, "DJ": 113, "DK": 114,
    "DL": 115, "DM": 116, "DN": 117, "DO": 118, "DP": 119, "DQ": 120,
    "DR": 121, "DS": 122, "DT": 123, "DU": 124,
    "EP": 145,
    "EQ": 146, "ER": 147, "ES": 148, "ET": 149, "EU": 150,
    "EV": 151, "EW": 152, "EX": 153, "EY": 154,
    "EZ": 155, "FA": 156, "FB": 157, "FC": 158, "FD": 159,
    "FE": 160, "FF": 161, "FG": 162, "FH": 163, "FI": 164,
    "FJ": 165, "FK": 166, "FL": 167, "FM": 168, "FN": 169,
    "FO": 170, "FP": 171, "FQ": 172, "FR": 173, "FS": 174,
    "FT": 175, "FU": 176, "FV": 177, "FW": 178, "FX": 179,
    "FY": 180, "FZ": 181, "GA": 182, "GB": 183, "GC": 184,
    "GD": 185, "GE": 186, "GF": 187, "GG": 188, "GH": 189,
    "GI": 190, "GJ": 191, "GK": 192,
}

# ── Tag mappings（変更なし）──────────────────────────────────────────────────
SELECTION_FLOW_TAG_MAP = {
    "60代も応募可": "65U83", "70代も応募可": "PFK9P", "履歴書不要": "VRCQ4",
    "友達と応募OK": "XYD5T", "職場見学可": "ANKQD", "面接1回": "R4ZRK",
}
SALARY_TAG_MAP = {
    "日払いOK": "HSRBS", "週払いOK": "H3ZFF", "高収入": "UABTR",
    "給料前払いOK": "8A66P", "賞与あり": "NA9HP", "ストックオプションあり": "6XT6J",
    "歩合給あり": "3A8KY", "固定給25万円以上": "PWAV3", "固定給35万円以上": "XUEJQ",
}
SALARY_TAG_MAP_GYOMU = {
    "日払いOK": "HSRBS", "週払いOK": "H3ZFF", "高収入": "UABTR",
    "給料前払いOK": "8A66P", "歩合給あり": "3A8KY",
}
WORKING_HOURS_TAG_MAP = {
    "残業なし": "GN2KW", "フルタイム歓迎": "QP3PV", "長期歓迎": "Q5J84",
    "短期": "8EG5C", "短期（1ヵ月以内）": "T22G3", "短期（3ヵ月以内）": "3BA2Q",
    "単発": "QFE79", "春夏冬休み期間限定": "WGEC9", "平日のみOK": "B9ACM",
    "土日祝のみOK": "52HB2", "都合による週0日OK": "QMFBU", "週1日からOK": "4HUYA",
    "週2・3日からOK": "RNH2U", "週4日以上OK": "THMDR", "週1シフト提出": "5P9GS",
    "隔週シフト提出": "4ZJDK", "月1シフト提出": "JG87K",
    "前日までのシフト調整可": "RS4NC", "家庭都合のシフト調整可": "5Y8GP",
    "都合による当日早退可": "8SD3J", "学業都合のシフト調整可": "NCXZ4",
    "シフト自由": "8GGC3", "早朝": "8EWXV", "午前": "FDF8V",
    "夕方": "K8AKP", "深夜": "SXRB4", "夜間": "H3N5U",
    "月平均残業時間20時間以内": "AFMGC", "原則定時退社": "VMN92",
    "時短勤務あり": "F8UBA", "1日1時間以内OK": "76M3X", "1日2時間以内OK": "H7Q4Y",
    "1日3時間以内OK": "QRM2V", "1日4時間以内OK": "4U3VY",
}
WORKING_HOURS_TAG_MAP_GYOMU = {
    "長期歓迎": "Q5J84", "短期": "8EG5C", "短期（1ヵ月以内）": "T22G3",
    "短期（3ヵ月以内）": "3BA2Q", "単発": "QFE79", "シフト自由": "8GGC3",
}
HOLIDAY_TAG_MAP = {
    "長期休暇あり": "TABHV", "年間休日120日以上": "6E5P4", "完全週休2日制": "NUHCT",
    "介護休暇あり": "87RUM", "育休あり": "NPHPU", "土日祝休み": "TSEFZ",
}
WELFARE_TAG_MAP = {
    "入社祝い金あり": "ZA2SS", "託児所あり": "Z5ZDK", "交通費支給": "PM67F",
    "社割あり": "SXFZX", "社員登用あり": "4E8M2", "研修あり": "K5UDY",
    "副業・WワークOK": "4PX2W", "家賃無料": "MG35T", "住宅手当あり": "DNKPF",
    "寮・社宅あり": "YCH9D", "食事補助あり": "YJ8XR", "まかないあり": "PXKDN",
    "昼食補助あり": "VD9Z9", "食費補助あり": "JGSQQ", "資格取得支援あり": "77B4M",
    "退職金あり": "KBRYN", "インセンティブあり": "P42XV",
    "資格取得手当あり": "RNEAH", "通勤交通費全額支給": "F9VJA",
}
WELFARE_TAG_MAP_GYOMU = {
    "交通費支給": "PM67F", "社員登用あり": "4E8M2", "研修あり": "K5UDY",
    "食事補助あり": "YJ8XR", "まかないあり": "PXKDN", "昼食補助あり": "VD9Z9",
    "食費補助あり": "JGSQQ", "インセンティブあり": "P42XV", "通勤交通費全額支給": "F9VJA",
}
LOCATION_FEATURE_MAP = {
    "送迎あり": "ZPPKQ", "車通勤OK": "9KWAA", "バイク通勤OK": "89HG5",
    "駅ナカ": "H7DBB", "駅近5分以内": "RCH8H", "転勤なし": "BNE3V", "在宅OK": "N83EH",
}
WORK_ENV_MAP = {
    "学生歓迎": "BD3P7", "英語": "D866K", "リゾート": "Y5887",
    "オープニングスタッフ": "NYYS2", "服装自由": "UG7AK", "髪型・髪色自由": "ZUPFV",
    "制服あり": "2MRTC", "主婦・主夫歓迎": "5DCQH", "学歴不問": "9JRJG",
    "フリーター歓迎": "7PD2A", "ブランクOK": "NKKX4", "ひげOK": "YSEDZ",
    "ネイルOK": "G8VR2", "ピアスOK": "TD4UW", "経験者歓迎": "G3CST",
    "有資格者歓迎": "JCEKM", "留学生活躍中": "YTAGU",
    "管理職・マネジメント経験歓迎": "F6PAA", "第二新卒歓迎": "VFQ6J",
    "業界未経験歓迎": "368C7", "中途入社50％以上": "992GD", "女性が活躍中": "P4MNE",
    "女性管理職登用あり": "FQMBA", "管理職・マネジャー採用": "FAD3T",
    "中国語": "TG4D3", "経験不問": "D7S5D", "未経験者歓迎": "D9PP2",
    "ノルマなし": "WEWW4", "扶養内勤務OK": "49FJ7", "ランチタイム": "3VNPH",
    "知識不要": "W9MGH", "経験不要": "SWWAC", "要知識": "5PGHG", "要経験": "3FJYA",
    "10代が多い": "FQ634", "20代が多い": "ACFMM", "30代が多い": "VFJRG",
    "40代が多い": "4VADT", "50代が多い": "DKT7N", "60代が多い": "NWBZ9",
    "70代以上が多い": "NZ2MT",
}
EMPLOYMENT_TYPE_MAP = {
    "正社員": "4", "契約社員": "5", "派遣社員": "6",
    "アルバイト・パート": "3", "業務委託": "8", "有料職業紹介": "7",
    "インターンシップ＆キャリア": "9",
}
SALARY_FORM_MAP = {
    "時給": "01", "日給": "02", "週給": "03",
    "月給": "04", "年俸": "05", "業務単位": "06",
}
SALARY_FORM_MAP_GYOMU = {
    "時給": "01", "日給": "02", "週給": "03",
    "月給": "04", "年俸": "05", "業務単位": "06", "完全歩合": "07",
}
WORKING_STYLE_MAP      = {"固定時間制": "01", "シフト制": "02", "変形労働時間制": "03", "その他": "04"}
WORKING_STYLE_MAP_GYOMU = {"固定時間制": "01", "シフト制": "02"}
GYOMU_TYPES      = {"業務委託"}
FREE_SHIFT_TYPES = {"業務委託", "アルバイト・パート"}

def is_gyomu_type(emp_type: str) -> bool:
    return emp_type in GYOMU_TYPES

def is_free_shift_type(emp_type: str) -> bool:
    return emp_type in FREE_SHIFT_TYPES


# ══════════════════════════════════════════════════════════════════════════════
class AirWorkBotBase:
    def __init__(self, username: str, password: str, sheet_id: str,
                 tab_name: str, image_folder: str,
                 config_loader: ConfigLoader,          # ← v3.0
                 log_callback=None,
                 headless: bool = True):               # ← v3.1
        self.username      = username
        self.password      = password
        self.sheet_id      = sheet_id
        self.tab_name      = tab_name
        self.image_folder  = image_folder
        self._loader       = config_loader             # ← v3.0
        self._cfg          = None                      # ← v3.0: 遅延ロード（FileConfig | None）
        self._log_cb       = log_callback or (lambda msg, level="INFO": print(f"[{level}] {msg}"))
        self.running       = False
        self.headless      = headless                  # ← v3.1
        self.driver        = None
        # ★ v3.2: 同一driverで2回目以降のログイン（＝別会社への切り替え）
        #   かどうかを判定するためのフラグ。_login() 内で使用する。
        self._has_logged_in_before = False
        self.master_lookup = {}
        self._ws           = None

    # ── Config 取得（遅延ロード）──────────────────────────────────────────
    def _get_file_cfg(self) -> FileConfig:
        """このクラスに対応する FileConfig を返す（初回のみロード）。"""
        if self._cfg is None:
            self._cfg = self._loader.get("bot_core.py")
        return self._cfg

    def stop(self):
        self.running = False

    # ── Logging ──────────────────────────────────────────────────────────
    def _log(self, msg: str, level="INFO"):
        level_map = {"INFO": logging.INFO, "OK": logging.INFO,
                     "WARN": logging.WARNING, "ERROR": logging.ERROR}
        _LOGGER.log(level_map.get(level, logging.INFO), f"[{level}] {msg}")
        self._log_cb(msg, level)

    def _find_service_account_json(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        json_files = [f for f in os.listdir(base_dir)
                      if f.endswith(".json") and f != os.path.basename(CONFIG_FILE)]
        if not json_files:
            return ""
        found = os.path.join(base_dir, json_files[0])
        if len(json_files) > 1:
            self._log(f"JSONファイルが複数見つかりました。{json_files[0]} を使用します。", "WARN")
        return found

    # ── Sheets ───────────────────────────────────────────────────────────
    def _fetch_sheet_data(self):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            sa_file = self._find_service_account_json()
            if not sa_file:
                self._log("サービスアカウント JSONファイルが見つかりません。", "ERROR")
                return None
            scopes = ["https://spreadsheets.google.com/feeds",
                      "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(self.sheet_id)
            ws = sh.worksheet(self.tab_name)
            self._ws = ws
            return ws.get_all_values()
        except Exception as e:
            self._log(f"Sheets接続エラー: {e}", "ERROR")
            return None

    def _fetch_master_data(self) -> dict:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            sa_file = self._find_service_account_json()
            if not sa_file:
                return {}
            scopes = ["https://spreadsheets.google.com/feeds",
                      "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(self.sheet_id)
            ws = sh.worksheet("マスター")
            rows = ws.get_all_values()
            lookup = {}
            for row in rows[1:]:
                if not row:
                    continue
                code  = row[0].strip() if len(row) > 0 else ""
                col_c = row[2].strip() if len(row) > 2 else ""
                col_d = row[3].strip() if len(row) > 3 else ""
                if code:
                    lookup[code] = (col_c, col_d)
            self._log(f"マスターデータ読み込み完了: {len(lookup)} 件", "OK")
            return lookup
        except Exception as e:
            self._log(f"マスターデータ取得エラー: {e}", "WARN")
            return {}

    def _update_row_status(self, row_num: int, status: str):
        if self._ws is None:
            self._log(f"行{row_num} ステータス更新スキップ（ws未取得）", "WARN")
            return
        try:
            # Config から COL_STATUS を取得（フォールバック: 旧 COL dict）
            try:
                col_idx = self._get_file_cfg().col("COL_STATUS")
            except Exception:
                col_idx = COL["status"] + 1
            self._ws.update_cell(row_num, col_idx, status)
            self._log(f"行{row_num} ステータス更新: {status}", "OK")
        except Exception as e:
            self._log(f"ステータス更新エラー (行{row_num}): {e}", "WARN")

    def _update_cell_value(self, row_num: int, value: str, col_index: int = 4):
        if self._ws is None:
            self._log(f"行{row_num} セル更新スキップ（ws未取得）", "WARN")
            return
        try:
            # col_index が明示された場合はそのまま使用
            # （呼び出し元で Config から取得した値を渡すことを推奨）
            self._ws.update_cell(row_num, col_index, value)
            self._log(f"行{row_num} 列{col_index} 更新: {value}", "OK")
        except Exception as e:
            self._log(f"セル更新エラー (行{row_num}, 列{col_index}): {e}", "WARN")

    # ── Browser / Selenium helpers（変更なし）────────────────────────────
    def _launch_browser(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            if self.headless:
                opts.add_argument("--headless=new")
                opts.add_argument("--window-size=1280,900")
            else:
                opts.add_argument("--start-maximized")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            driver = webdriver.Chrome(options=opts)
            driver.implicitly_wait(10)
            # ★ v3.3で追加。
            # 従来はページ読み込みのタイムアウトを一切設定しておらず、
            # driver.get(url) がネットワーク不調やAirWork側の応答遅延時に
            # 無期限にブロックしうる状態だった（詳細はファイル冒頭の
            # v3.3 変更点コメントを参照）。ここで60秒の上限を設定し、
            # 超過した場合は selenium.common.exceptions.TimeoutException
            # を送出させることで、呼び出し元（通常は広めの
            # except Exception で受け止められる）に確実に制御を戻す。
            driver.set_page_load_timeout(60)
            self._log("ブラウザ起動成功。", "OK")
            # ★ v3.2: 新しいブラウザ（新しいSeleniumセッション）を起動した
            #   場合は、これまでのログイン履歴フラグをリセットする。
            self._has_logged_in_before = False
            return driver
        except Exception as e:
            self._log(f"ブラウザ起動エラー: {e}", "ERROR")
            return None

    def _wait_and_find(self, driver, by, selector, timeout=15):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector)))
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el)
        except Exception:
            pass
        return el

    def _click_js(self, driver, element):
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center',behavior:'instant'});"
            "arguments[0].click();", element)

    def _fast_type(self, driver, element, value: str):
        driver.execute_script("""
            var el=arguments[0], val=arguments[1];
            el.focus();
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')
                .set.call(el,val);
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));
            el.blur();
        """, element, str(value))

    def _fast_type_textarea(self, driver, element, value: str):
        driver.execute_script("""
            var el=arguments[0], val=arguments[1];
            el.focus();
            Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')
                .set.call(el,val);
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));
            el.blur();
        """, element, str(value))

    def _set_input(self, driver, element, value):
        self._fast_type(driver, element, str(value))

    def _get_cell(self, row, col_key) -> str:
        """旧 COL dict 経由（page1〜4 の後方互換用）。"""
        idx = COL[col_key]
        return row[idx].strip() if idx < len(row) else ""

    def _get_cfg_cell(self, row, var_name: str, file_name: str = "bot_core.py") -> str:
        """
        Config タブの Variable 名でセル値を取得する新方式。
        page1〜4 が Config 移行した後はこちらを使う。
        例: self._get_cfg_cell(row, "COL_JOB_TITLE", "page1.py")
        """
        try:
            cfg = self._loader.get(file_name)
            idx = cfg.col(var_name) - 1   # 0-based
            return row[idx].strip() if idx < len(row) else ""
        except Exception:
            return ""

    def _normalize_addr(self, text: str) -> str:
        t = re.sub(r"[\s\u3000]+", "", text)
        return t.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    def _addr_match(self, opt_addr: str, col_t: str, col_u: str, col_v: str) -> bool:
        expected = self._normalize_addr(col_t + col_u + col_v)
        actual   = self._normalize_addr(opt_addr.replace("住所：", ""))
        if not expected:
            return True
        return actual == expected or actual.startswith(expected) or expected.startswith(actual)

    def _tick_tags(self, driver, raw: str, tag_map: dict):
        from selenium.webdriver.common.by import By
        for kw in [k.strip() for k in raw.split(",") if k.strip()]:
            name_attr = tag_map.get(kw)
            if name_attr:
                try:
                    cb = driver.find_element(By.CSS_SELECTOR, f"input[name='{name_attr}']")
                    if not cb.is_selected():
                        self._click_js(driver, cb)
                except Exception:
                    self._log(f"タグ未発見: {kw}", "WARN")
            else:
                self._log(f"未知のタグ: {kw}", "WARN")

    def _enter_textarea(self, driver, css_selector: str, value: str):
        from selenium.webdriver.common.by import By
        try:
            field = self._wait_and_find(driver, By.CSS_SELECTOR, css_selector)
            self._fast_type_textarea(driver, field, str(value))
        except Exception as e:
            self._log(f"テキストエリア入力エラー ({css_selector}): {e}", "WARN")

    # ── Login ────────────────────────────────────────────────────────────
    # ★ v3.2: 同一driverで別会社のAirIDに切り替える際にログインできなくなる
    #   不具合を修正。詳細はファイル冒頭のコメントを参照。
    def _login(self, driver) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException

        LOGIN_URL = (
            "https://connect.airregi.jp/login?client_id=AWR"
            "&redirect_uri=https%3A%2F%2Fconnect.airregi.jp%2Foauth%2Fauthorize"
            "%3Fclient_id%3DAWR%26nonce%3DwAdWTOE2jZju1pUtmYrEK7idlq86dPQborZyWJIpe0w"
            "%26redirect_uri%3Dhttps%253A%252F%252Fats.rct.airwork.net%252Fairplf%252Flogin%252Fcb"
            "%26response_type%3Dcode%26scope%3Dopenid%2Bprofile%2Bemail"
            "%26state%3DCxUdDfTgzbwttBLzval52OWq6grPRYc3fUBD70cPyrE"
        )
        LOGOUT_URL = "https://ats.rct.airwork.net/logout"

        def _try_fill_and_submit() -> str:
            """
            現在の画面を判定し、可能なら AirID/パスワードを入力して送信する。
            戻り値:
              "submitted"         … #account + #password が見つかり送信した
              "identity_check"    … 本人確認画面（#password のみ、#account 無し）
              "already_dashboard" … 既にログイン済みダッシュボードに居る
              "unknown"           … どれにも該当しない（想定外の画面）
            """
            time.sleep(1.5)

            cur_url = driver.current_url
            if ("airwork.net" in cur_url or "job_offers" in cur_url) and \
               "connect.airregi.jp" not in cur_url:
                try:
                    driver.find_element(By.ID, "account")
                    # account フィールドが実は存在する（URLはダッシュボード
                    # だが実際はまだログイン画面が被さっているケース）
                    # → そのまま下の通常フローで処理する
                except NoSuchElementException:
                    return "already_dashboard"

            try:
                account_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "account"))
                )
            except TimeoutException:
                account_field = None

            if account_field is not None:
                pass_field = driver.find_element(By.ID, "password")
                self._set_input(driver, account_field, self.username)
                self._set_input(driver, pass_field, self.password)
                driver.find_element(
                    By.CSS_SELECTOR, "input[type='submit'][value='ログイン']"
                ).click()
                time.sleep(3)
                return "submitted"

            # #account は無いが #password だけある = 本人確認画面の可能性
            try:
                driver.find_element(By.ID, "password")
                return "identity_check"
            except NoSuchElementException:
                pass

            return "unknown"

        def _escape_identity_check() -> bool:
            """
            本人確認画面から「別のAirIDまたはメールアドレスでログインする」
            リンクをクリックして、通常の #account/#password フォームまで戻る。
            """
            try:
                link = driver.find_element(
                    By.XPATH,
                    "//a[contains(@href,'/logout')]"
                    "[contains(., '別のAirID') or contains(., '別の') or contains(., 'ログインする')]",
                )
            except NoSuchElementException:
                self._log(
                    "本人確認画面ですが「別のAirIDでログインする」リンクが"
                    "見つかりませんでした。",
                    "WARN",
                )
                return False

            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", link
                )
                link.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", link)
                except Exception as e:
                    self._log(f"本人確認画面からの離脱に失敗しました: {e}", "WARN")
                    return False

            time.sleep(1.5)

            # リンクをクリックした後、さらに中間の「ログイン」ボタンが
            # 挟まることがあるので、あれば押す。
            try:
                login_btn = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//*[self::a or self::button]"
                            "[@role='button']"
                            "[contains(@class,'loginButton') or normalize-space(text())='ログイン']",
                        )
                    )
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", login_btn
                )
                try:
                    login_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", login_btn)
                time.sleep(1.5)
            except TimeoutException:
                pass  # 中間ボタンが無いケースもある。想定内。

            return True

        try:
            # ── 事前ログアウト ──────────────────────────────────────
            # 2回目以降（＝直前に別のAirIDでログインしていた可能性がある）
            # の場合は、まず明示的にログアウトしてからログインページへ行く。
            # これにより「本人確認」画面や「既にログイン済みのダッシュ
            # ボードに直行してしまう」ケースを大きく減らせる。
            if self._has_logged_in_before:
                self._log("前回のログイン状態をクリアするためログアウトします...", "INFO")
                try:
                    driver.get(LOGOUT_URL)
                    time.sleep(1.5)
                except Exception as e:
                    self._log(f"事前ログアウトに失敗しました（続行します）: {e}", "WARN")

            self._log("ログインページに移動中...", "INFO")
            driver.get(LOGIN_URL)

            state = _try_fill_and_submit()

            if state == "identity_check":
                self._log(
                    "本人確認画面が表示されました。「別のAirIDでログインする」"
                    "から抜けて通常のログインフォームに進みます...",
                    "INFO",
                )
                if _escape_identity_check():
                    state = _try_fill_and_submit()

            if state == "already_dashboard":
                self._log(
                    "既にログイン済みの状態のようです。ログアウトしてやり直します...",
                    "WARN",
                )
                try:
                    driver.get(LOGOUT_URL)
                    time.sleep(1.5)
                except Exception as e:
                    self._log(f"ログアウトに失敗しました: {e}", "WARN")
                driver.get(LOGIN_URL)
                state = _try_fill_and_submit()
                if state == "identity_check":
                    if _escape_identity_check():
                        state = _try_fill_and_submit()

            if state not in ("submitted", "already_dashboard"):
                self._log(
                    f"ログインフォームを特定できませんでした（状態: {state}）。"
                    f"現在のURL: {driver.current_url}",
                    "ERROR",
                )
                return False

            # ── 結果判定 ─────────────────────────────────────────
            if "airwork.net" in driver.current_url or "job_offers" in driver.current_url:
                self._log("ログイン成功！", "OK")
                self._has_logged_in_before = True
                return True

            self._log(f"ログイン失敗。現在のURL: {driver.current_url}", "ERROR")
            return False

        except Exception as e:
            self._log(f"ログインエラー: {e}", "ERROR")
            return False

    # ── Run ──────────────────────────────────────────────────────────────
    def run(self):
        try:
            self.running = True
            self._log("Config タブから設定を読み込み中...", "INFO")
            file_cfg = self._get_file_cfg()
            self._log(f"設定取得完了: tab={file_cfg.tab_name}, vars={len(file_cfg.all_vars())}件", "OK")

            self._log("マスターデータを読み込み中...", "INFO")
            self.master_lookup = self._fetch_master_data()

            self._log("Google Sheetsに接続中...", "INFO")
            rows = self._fetch_sheet_data()
            if rows is None:
                return

            # Config からステータス列と開始行を取得
            status_col_idx = file_cfg.get("COL_STATUS", COL["status"] + 1) - 1  # 0-based
            job_id_col     = file_cfg.get("COL_JOB_ID",  4)                      # 1-based

            self._log(f"{len(rows)} 行を取得。処理対象行を確認中...", "INFO")
            target_rows = []
            for i, row in enumerate(rows[1:], start=2):
                status = row[status_col_idx].strip() if len(row) > status_col_idx else ""
                if status == "求人作成必要":
                    target_rows.append((i, row))

            if not target_rows:
                self._log("処理対象の行がありません。", "WARN")
                return

            self._log(f"処理対象: {len(target_rows)} 行", "OK")
            driver = self._launch_browser()
            if driver is None:
                return
            self.driver = driver

            # クライアント列（COL_CLIENT）を Config から取得
            client_col_idx = file_cfg.get("COL_CLIENT", COL["I"] + 1) - 1  # 0-based

            groups = defaultdict(list)
            for row_num, row in target_rows:
                client = row[client_col_idx].strip() if len(row) > client_col_idx else ""
                groups[client].append((row_num, row))

            for client_code, group_rows in groups.items():
                if not self.running:
                    break
                self._log(f"アカウント [{client_code or '共通'}] でログイン中...", "INFO")
                if not self._login(driver):
                    self._log(f"ログイン失敗。アカウント [{client_code}] をスキップ。", "ERROR")
                    continue

                for idx, (row_num, row) in enumerate(group_rows):
                    if not self.running:
                        break
                    self._log(f"── 行 {row_num} を処理中 ──", "INFO")
                    success = self._process_row(driver, row_num, row)

                    if success:
                        job_id = self._save_draft_and_get_id(driver)
                        if job_id:
                            self._update_cell_value(row_num, job_id, col_index=job_id_col)
                            self._log(f"行{row_num}: 求人ID [{job_id}] を記録しました。", "OK")
                        else:
                            self._log(f"行{row_num}: 求人ID取得失敗。", "WARN")
                        self._update_row_status(row_num, "完了")
                        self._log(f"行 {row_num}: 完了 ✓", "OK")
                        is_last = (idx == len(group_rows) - 1)
                        if not is_last and self.running:
                            self._click_create_new_job(driver)
                    else:
                        self._log(f"行 {row_num}: エラー。スキップ。", "ERROR")
                        self._update_row_status(row_num, "失敗")
                        is_last = (idx == len(group_rows) - 1)
                        if not is_last and self.running:
                            try:
                                self._click_create_new_job(driver)
                            except Exception:
                                pass

            self._log("全処理完了。", "OK")
        except Exception as e:
            self._log(f"予期せぬエラー: {e}", "ERROR")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.running = False
