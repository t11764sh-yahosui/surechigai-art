# すれちがい美術展

ゲーム本体は `index.html` 1ファイル(ビルドなし)。通信は PeerJS(WebRTC P2P)で、ホストのブラウザが進行役。

## 変更したら必ず通しテストを実行する

```
.venv/bin/python tests/e2e.py
```

4人分のプレイヤーを本物の P2P 通信で動かし、参加 → 描画 → 投票 → 逆転(自由入力と判定)→ 結果発表まで確認する。
`全テスト成功` 以外で終わったら、`test-results/FAIL-*.png` とエラー出力を見て直してから完了とする。
UI を変えたときは `test-results/` のフェーズごとのスクリーンショットも目で確認する。
PeerJS の公開サーバーを使うのでネット接続が必要。

## 開発用コマンド

- `python3 dev/serve.py` — http://localhost:8000/ で配信。ファイル保存でブラウザが自動再読み込み(index.html 自体は変更しない)
- `.venv/bin/python tests/e2e.py --headed` — 通しテストの動きをウィンドウで見る
- `.venv/bin/python tests/bots.py <招待コード>` — ボット3体を部屋に入れて一緒に遊ばせる(`-n` で人数)
- `tests/players.py` — 画面を操作する部品。テストとボットで共用。UI のセレクタを変えたらここも直す

## 環境

- Playwright は `.venv` に入っている(Python 3.11, playwright 1.48)。ブラウザはインストール済みの Google Chrome(`channel='chrome'`)
- Node.js / Homebrew はこの Mac にない
