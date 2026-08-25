#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chatwork_lookup_members.py
===========================================================================
指定したChatworkルームのメンバー一覧（名前 + account_id）を表示する
確認用スクリプト。chatwork_config.json の boss_account_id が正しいかの
確認、または他のメンバーのaccount_idを調べたい場合に1回だけ実行する。

使い方:
    python chatwork_lookup_members.py

chatwork_config.json（api_token / room_id）を読み込んで使用する。
===========================================================================
"""

import requests
from chatwork_notifier import _load_config, CHATWORK_API_BASE


def main():
    cfg = _load_config()
    url = f"{CHATWORK_API_BASE}/rooms/{cfg['room_id']}/members"
    headers = {"X-ChatWorkToken": cfg["api_token"]}

    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"エラー: HTTP {resp.status_code}: {resp.text}")
        return

    members = resp.json()
    print(f"ルームID {cfg['room_id']} のメンバー一覧（{len(members)}名）:\n")
    print(f"{'account_id':<12} {'権限':<10} 名前")
    print("-" * 50)
    for m in members:
        role = m.get("role", "")
        print(f"{m.get('account_id'):<12} {role:<10} {m.get('name')}")

    print(
        f"\n現在 chatwork_config.json に設定されている boss_account_id: "
        f"{cfg.get('boss_account_id')}"
    )
    match = [m for m in members if str(m.get("account_id")) == str(cfg.get("boss_account_id"))]
    if match:
        print(f"→ 一致するメンバー: {match[0].get('name')}（正しく設定されています）")
    else:
        print("→ 一致するメンバーが見つかりませんでした。boss_account_id を見直してください。")


if __name__ == "__main__":
    main()
