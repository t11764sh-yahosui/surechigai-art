"""ブラウザ上の1人のプレイヤーを操作する部品(ボットと自動テストで共用)

実際の画面をクリック・ドラッグして操作するので、UI の崩れや反応しないボタンもそのまま検出できる。
"""
import random

TIMEOUT = 20_000   # PeerJS の接続待ちがあるので長め


class Player:
    def __init__(self, page, name):
        self.page = page
        self.name = name
        self.errors = []
        page.on('pageerror', lambda e: self.errors.append(f'[{name}] {e}'))
        page.on('console', lambda m: m.type == 'error' and self.errors.append(f'[{name}] console: {m.text}'))
        page.on('dialog', lambda d: d.accept())   # 「空白のまま出展?」の確認など

    # ---------- 状態の読み取り ----------
    def phase(self):
        return self.page.evaluate('gameState.phase')

    def me(self):
        return self.page.evaluate('gameState.players.find(p => p.id === myId) || null')

    def active_panel(self):
        return self.page.evaluate("document.querySelector('.panel.active')?.id")

    def wait_panel(self, panel_id, timeout=TIMEOUT):
        self.page.wait_for_selector(f'#{panel_id}.active', timeout=timeout)

    # ---------- 入室 ----------
    def host(self, base_url):
        self.page.goto(base_url)
        self.page.fill('#input-name', self.name)
        self.page.click('#btn-create')
        self.wait_panel('panel-room')
        return self.page.evaluate('roomCode')

    def join(self, base_url, code):
        self.page.goto(f'{base_url}?room={code}')
        self.page.fill('#input-name', self.name)
        self.page.click('#btn-join')
        self.page.wait_for_function(
            'name => gameState.players.some(p => p.id === myId)', arg=self.name, timeout=TIMEOUT)

    def start(self):
        self.page.wait_for_selector('#btn-start:not([disabled])', timeout=TIMEOUT)
        self.page.click('#btn-start')

    # ---------- 制作 ----------
    def draw(self, n_cards=None):
        """手札をカンヴァスの好きな位置へドラッグして置き、出展する"""
        page = self.page
        self.wait_panel('panel-game')
        page.wait_for_selector('#hand-area .card.front-card', timeout=TIMEOUT)
        n = n_cards or random.randint(2, 4)
        for _ in range(n):
            pairs = page.locator('#hand-area .card-pair')
            if pairs.count() == 0:
                break
            pair = pairs.first
            if random.random() < 0.4:
                pair.locator('.flip-btn').click()
            card = pair.locator('.card.front-card').bounding_box()
            cv = page.locator('#canvas-area').bounding_box()
            tx = cv['x'] + cv['width'] * random.uniform(0.2, 0.8)
            ty = cv['y'] + cv['height'] * random.uniform(0.2, 0.8)
            page.mouse.move(card['x'] + card['width'] / 2, card['y'] + card['height'] / 2)
            page.mouse.down()
            page.mouse.move(tx, ty, steps=10)
            page.mouse.up()
        placed = page.locator('#canvas-area .canvas-card').count()
        page.click('#btn-submit')
        return placed

    # ---------- 投票 ----------
    def vote(self, target_name=None):
        """target_name の作品に投票(省略時は自分以外からランダム)"""
        page = self.page
        self.wait_panel('panel-gallery')
        items = page.locator('.gallery-item.can-pick')
        items.first.wait_for(timeout=TIMEOUT)
        if target_name:
            item = items.filter(has=page.locator('.artist', has_text=target_name)).first
        else:
            item = items.nth(random.randrange(items.count()))
        item.locator('.frame').click()
        page.click('#btn-vote-confirm')

    # ---------- 逆転チャンス ----------
    def is_faker_in_guess(self):
        return self.page.locator('#guess-form').is_visible()

    def guess(self, answer):
        self.page.fill('#input-guess', answer)
        self.page.click('#btn-guess-confirm')

    def judge(self, ok):
        self.wait_panel('panel-judge')
        self.page.click('#btn-judge-ok' if ok else '#btn-judge-ng')

    # ---------- 結果 ----------
    def verdict(self):
        self.wait_panel('panel-result')
        # 演出(ドラムロール)が終わって判定が出るまで待つ
        self.page.wait_for_selector('#result-banner:not(.drumroll) .verdict', timeout=TIMEOUT)
        return self.page.inner_text('#result-banner .verdict')
