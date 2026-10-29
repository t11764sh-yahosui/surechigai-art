"""通しテスト:参加 → 描画 → 投票 → 逆転(自由入力と判定)→ 結果発表

    .venv/bin/python tests/e2e.py            # 画面なしで実行
    .venv/bin/python tests/e2e.py --headed   # 4人分のウィンドウを開いて動きを見る

4人のプレイヤーを別々のブラウザコンテキストで動かし、本物の P2P 通信で1ラウンド遊ぶ。
各フェーズのスクリーンショットは test-results/ に保存される。
"""
import argparse
import os
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dev'))
from players import Player  # noqa: E402
from serve import make_server, ROOT  # noqa: E402

NAMES = ['ホスト', 'モネ', 'ピカソ', 'ダリ']
OUT = os.path.join(ROOT, 'test-results')


def step(msg):
    print(f'▶ {msg}', flush=True)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print(f'  ✓ {msg}', flush=True)


def shoot(players, label):
    for i, p in enumerate(players[:2]):   # ホストとゲスト1人分
        p.page.screenshot(path=os.path.join(OUT, f'{label}-{i}-{p.name}.png'), full_page=True)


def run(headed):
    os.makedirs(OUT, exist_ok=True)
    srv = make_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/'

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=not headed, slow_mo=150 if headed else 0)
        players = []
        for name in NAMES:
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            players.append(Player(ctx.new_page(), name))
        host, guests = players[0], players[1:]

        try:
            step('ホストが展覧会を開く')
            code = host.host(url)
            check(len(code) == 4, f'招待コードが発行された({code})')

            step('ゲスト3人が招待リンクから入場')
            for g in guests:
                g.join(url, code)
            host.page.wait_for_function('gameState.players.length === 4')
            check(True, '待機室に4人そろった')
            shoot(players, '1-lobby')

            step('開幕して、全員が描いて出展')
            host.start()
            for p in players:
                placed = p.draw(n_cards=3)
                check(placed == 3, f'{p.name} がカード3枚を置いて出展')
            for p in players:
                p.wait_panel('panel-gallery')
            check(True, '全員の画面が品評会に進んだ')
            shoot(players, '2-gallery')

            # 逆転チャンスまで確実に進めるため、ホストだけが知る正解(贋作師)に全員で投票する
            faker_i = host.page.evaluate('gameState.players.find(p => p.isFaker).index')
            master = host.page.evaluate('currentTheme.master')
            faker = players[faker_i]
            step(f'投票(贋作師は {faker.name}、みんなのお題は「{master}」)')
            for p in players:
                p.vote(None if p is faker else faker.name)
            for p in players:
                p.wait_panel('panel-guess')
            check(True, '見破られて逆転チャンスに進んだ')
            check(faker.is_faker_in_guess(), '贋作師にだけ回答欄が出ている')
            check(not any(p.is_faker_in_guess() for p in players if p is not faker), 'ほかの人には回答欄が出ていない')
            shoot(players, '3-guess')

            step('贋作師が自由入力で回答 → 残りの全員が判定')
            faker.guess('それっぽい何か')
            others = [p for p in players if p is not faker]
            for p in others:
                p.wait_panel('panel-judge')
            check(faker.page.locator('#judge-buttons').is_hidden(), '贋作師本人には判定ボタンが出ない')
            shoot(players, '4-judge')
            others[0].judge(True)
            others[1].judge(True)
            others[2].judge(False)

            step('結果発表')
            verdicts = [p.verdict() for p in players]
            check(all('大逆転' in v for v in verdicts), f'2対1で正解判定 → 全員の画面が「大逆転」({verdicts[0]})')
            scores = host.page.evaluate('gameState.players.map(p => p.score)')
            check(scores[faker_i] == 2 and sum(scores) == 2, f'贋作師だけに+2点(得点 {scores})')
            check(host.page.locator('.vote-row').count() == 4, '得票表に4人分の行がある')
            shoot(players, '5-result')

            errors = [e for p in players for e in p.errors]
            check(not errors, 'ブラウザのエラーなし' if not errors else '\n'.join(errors))
            print('\n全テスト成功', flush=True)
            return 0
        except Exception as e:  # noqa: BLE001
            print(f'\n✗ 失敗: {e}', flush=True)
            for p in players:
                p.page.screenshot(path=os.path.join(OUT, f'FAIL-{p.name}.png'), full_page=True)
                for err in p.errors:
                    print('  ', err)
            print(f'失敗時の画面: {OUT}/FAIL-*.png', flush=True)
            return 1
        finally:
            browser.close()
            srv.shutdown()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--headed', action='store_true', help='ブラウザ画面を表示して動きを見る')
    sys.exit(run(ap.parse_args().headed))
