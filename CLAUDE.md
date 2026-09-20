# sagumo プロジェクト固有設定

## コミット運用

developブランチの直近コミット履歴を確認したところ、全コミットが自分（being24 / forprom.sn.16@gmail.com、同一人物）の直コミットで、PR/mergeの痕跡はdependabotの自動PRのみ（判定日: 2026-09-20）。develop への直コミットを許容する。

## 開発コマンド

- Pythonの実行・パッケージ管理は `uv` を使用（`.github/copilot-instructions.md` 準拠）
- フォーマット: `uv run ruff format`
- import整理: `uv run ruff check --fix --select I`
- 型チェック: `pyrightconfig.json` / `pyrefly.toml` あり。`pyrefly.toml` の `python-interpreter-path` はdevcontainer前提（`/workspaces/sagumo/...`）でハードコードされており、他環境では `uv run pyrefly check cogs/ --python-interpreter-path "$(pwd)/.venv/bin/python3"` のように明示指定が必要（既知の環境依存、今回未修正）
- テスト: `uv run pytest tests/`（pytest / pytest-asyncio を導入。テストは `cogs.utils.*` を `import` するため `pyproject.toml` の `[tool.pytest.ini_options] pythonpath = ["."]` が必要）
