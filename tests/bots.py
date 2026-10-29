"""テスト用ボット:あなたの部屋に入って、描画・投票・お題当て・判定まで自動で遊ぶ

    # 1. 開発サーバーを起動して、ブラウザで展覧会を開く(招待コードを控える)
    python3 dev/serve.py
    # 2. 別のターミナルでボットを3体入場させる(ウィンドウが開いて動きが見える)
    .venv/bin/python tests/bots.py ABCD

ホスト(あなた)が開幕すればボットも遊び始め、次のラウンドにもそのまま参加する。
Ctrl+C で終了。
"""
import argparse
import os
import random
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from players import Player  # noqa: E402

BOT_NAMES = ['ボット・モネ', 'ボット・ダリ', 'ボット・北斎', 'ボット・ミレー', 'ボット・ムンク', 'ボット・セザンヌ', 'ボット・若冲']
GUESSES = ['ネコ', 'トラ', 'りんご', '太陽', '電車', 'カメ', '時計', 'ペンギン']


def act(bot, done):
    """今の画面を見て、まだやっていないことを1つやる。done: このラウンドで済ませた操作"""
    phase = bot.phase()
    me = bot.me() or {}
    key = (phase, bot.page.evaluate('gameState.round'))
    if key in done:
        return
    if phase == 'game' and not me.get('isReady'):
        time.sleep(random.uniform(1, 4))          # 考えているふり
        bot.draw()
    elif phase == 'gallery' and not me.get('hasVoted'):
        time.sleep(random.uniform(1, 3))
        bot.vote()
    elif phase == 'guess' and bot.is_faker_in_guess():
        time.sleep(random.uniform(2, 5))
        bot.guess(random.choice(GUESSES))
    elif phase == 'judge' and bot.page.locator('#btn-judge-ok').is_visible():
        time.sleep(random.uniform(1, 3))
        bot.judge(random.random() < 0.5)
    else:
        return
    done.add(key)
    print(f'  {bot.name}: {phase} を完了', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('room', help='4文字の招待コード')
    ap.add_argument('-n', '--count', type=int, default=3, help='ボットの数(既定 3)')
    ap.add_argument('--url', default='http://localhost:8000/', help='ゲームのURL')
    ap.add_argument('--headless', action='store_true', help='ウィンドウを開かずに動かす')
    args = ap.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=args.headless, slow_mo=60)
        bots = []
        for name in BOT_NAMES[:args.count]:
            ctx = browser.new_context(viewport={'width': 390, 'height': 760})
            bot = Player(ctx.new_page(), name)
            bot.join(args.url, args.room.upper())
            print(f'{name} が入場しました', flush=True)
            bots.append((bot, set()))

        print('ホストが開幕するのを待っています(Ctrl+C で終了)', flush=True)
        try:
            while True:
                for bot, done in bots:
                    if bot.active_panel() == 'panel-lobby':   # 部屋が閉じられた
                        print('部屋が閉じられたので終了します')
                        return
                    try:
                        act(bot, done)
                    except Exception as e:  # noqa: BLE001  フェーズが途中で進んだ等。次の周回でやり直す
                        print(f'  {bot.name}: {e.__class__.__name__}(再試行します)', flush=True)
                for bot, _ in bots:
                    for err in bot.errors:
                        print('  ブラウザのエラー:', err)
                    bot.errors.clear()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()


if __name__ == '__main__':
    main()
