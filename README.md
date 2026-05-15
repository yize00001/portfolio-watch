# portfolio-watch

一個股票庫存監控工具。初版目標是讀取本機 CSV 庫存資料，抓取近即時股價，計算單檔股票的現價、成本、未實現損益與漲跌幅，並在達到設定門檻時發出通知。

## MVP 範圍

- 讀取 `data/portfolio.example.csv` 格式的持股清單
- 透過價格來源模組取得目前價格
- 計算市值、未實現損益與報酬率
- 預留交易時間內定期檢查的排程入口
- 預留 Telegram Bot 通知介面
- 使用 `.env` 管理 token 與個人設定

## 專案結構

```text
portfolio-watch/
  data/
    portfolio.example.csv
  src/
    portfolio_watch/
      __init__.py
      __main__.py
      cli.py
      config.py
      market_hours.py
      models.py
      notifier.py
      portfolio.py
      pricing.py
      watcher.py
  tests/
    test_portfolio.py
  .env.example
  .gitignore
  pyproject.toml
```

## 快速開始

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m portfolio_watch --portfolio data/portfolio.example.csv
```

如果環境使用 `python` 而不是 Windows 的 `py` launcher，可以把第一行改成：

```bash
python -m venv .venv
```

## 設定

複製 `.env.example` 為 `.env`，再填入自己的設定。

```bash
copy .env.example .env
```

真實庫存資料與 `.env` 不要提交到 GitHub。版控內只保留範例資料與程式碼。

## 下一步

- 接入實際價格來源，例如券商 API 或行情 API
- 完成 Telegram Bot 通知
- 加入交易時間排程
- 加入停利、停損、漲跌幅門檻設定

## Handoff

目前狀態：

- Python MVP 骨架已建立
- GitHub private repo 已建立並 push 到 `main`
- CLI 可使用 mock price provider 跑範例資料
- `.env` 與真實庫存資料已被 `.gitignore` 排除
- 下一個建議功能：接入 `yfinance` price provider

回家後建議流程：

```powershell
git clone https://github.com/yize00001/portfolio-watch.git
cd portfolio-watch
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m portfolio_watch --portfolio data\portfolio.example.csv
pytest
```

下一次對話可以直接這樣開場：

```text
請繼續 portfolio-watch 專案。
GitHub repo: https://github.com/yize00001/portfolio-watch
目前狀態：Python MVP 骨架已 push 到 private repo，mock provider 可跑。
目標：先確認 Python 環境與測試，接著實作 yfinance price provider。
```
