from bot_core     import AirWorkBotBase, load_config, save_config
from page1        import Page1Mixin
from page2        import Page2Mixin
from page3        import Page3Mixin
from page4        import Page4Mixin
from config_loader import ConfigLoader


class AirWorkBot(Page1Mixin, Page2Mixin, Page3Mixin, Page4Mixin, AirWorkBotBase):
    """全ページ Mixin + Base を統合した完全なボットクラス。"""

    def __init__(self, username: str, password: str, sheet_id: str,
                 tab_name: str, image_folder: str,
                 config_loader: ConfigLoader,   # ← GUI から渡される
                 log_callback=None):
        super().__init__(
            username      = username,
            password      = password,
            sheet_id      = sheet_id,
            tab_name      = tab_name,
            image_folder  = image_folder,
            config_loader = config_loader,
            log_callback  = log_callback,
        )


# ── スタンドアロン実行 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cfg = load_config()

    username     = cfg.get("username", "")
    password     = cfg.get("password", "")
    sheet_id     = cfg.get("sheet_id", "")
    config_tab   = cfg.get("config_tab", "Config")

    if not all([username, password, sheet_id]):
        print("設定が不完全です。~/.airwork_bot_config.json を確認してください。")
        sys.exit(1)

    loader   = ConfigLoader(sheet_id, config_tab_name=config_tab)
    bot_cfg  = loader.get("bot_core.py")
    tab_name = bot_cfg.tab_name

    def console_log(msg, level="INFO"):
        print(f"[{level}] {msg}")

    bot = AirWorkBot(
        username      = username,
        password      = password,
        sheet_id      = sheet_id,
        tab_name      = tab_name,
        image_folder  = cfg.get("drive_folder", ""),
        config_loader = loader,
        log_callback  = console_log,
    )
    bot.run()
