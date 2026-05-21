# portfolio-watch

個人股票庫存監控工具。透過 Telegram Bot 即時查詢持股現況、未實現損益，並在漲跌幅或損益達到設定門檻時主動通知。

## 功能

- 透過 `yfinance` 取得近即時股價（支援台股、美股及所有 yfinance 支援的市場）
- 計算每檔持股的市值、未實現損益與報酬率
- Telegram Bot 指令查詢：
  - `/status` — 查詢目前持股現況
  - `/summary` — 查詢今日損益總結
- 開市時間（週一至週五）每 5 分鐘自動檢查門檻，觸發才推播
- 13:30 收盤後自動推送今日損益總結
- 持股資料與 token 皆不進版控，安全管理個人資訊

## 專案結構

```text
portfolio-watch/
  data/
    portfolio.example.csv   # 持股範例（格式參考）
  src/
    portfolio_watch/
      bot.py                # Telegram Bot 主迴圈
      cli.py                # CLI 入口
      config.py             # 設定載入（.env）
      market_hours.py       # 交易時間判斷
      models.py             # 資料模型
      notifier.py           # Telegram 通知
      portfolio.py          # 讀取持股 CSV
      pricing.py            # 價格來源（yfinance / mock）
      watcher.py            # 快照計算
  tests/                    # 單元測試
  .env.example              # 環境變數範例
  pyproject.toml
```

## 快速開始

### 1. 安裝套件

建議使用 [uv](https://github.com/astral-sh/uv)：

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
```

或使用傳統 pip：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. 設定環境變數

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

編輯 `.env`，填入你的設定：

```ini
PORTFOLIO_FILE=data/portfolio.csv
PRICE_PROVIDER=yfinance
NOTIFIER=telegram
TELEGRAM_BOT_TOKEN=你的 Bot Token
TELEGRAM_CHAT_ID=你的 Chat ID
CHECK_INTERVAL_SECONDS=300
MARKET_TIMEZONE=Asia/Taipei
```

取得 Telegram Bot Token 與 Chat ID 的方式：

1. Telegram 搜尋 `@BotFather` → `/newbot` → 取得 Token
2. 傳訊息給你的 Bot，再開啟 `https://api.telegram.org/bot<TOKEN>/getUpdates`，找 `chat.id`

### 3. 建立持股清單

```bash
cp data/portfolio.example.csv data/portfolio.csv
```

編輯 `data/portfolio.csv`，填入真實持股：

```csv
symbol,name,quantity,average_cost,currency,alert_change_percent,alert_gain_percent
0050.TW,元大台灣50,100,80.0,TWD,3,15
AAPL,Apple Inc.,10,150.0,USD,3,20
```

| 欄位 | 說明 |
|---|---|
| `symbol` | 股票代號（台股加 `.TW`，例如 `0050.TW`） |
| `quantity` | 持有股數 |
| `average_cost` | 平均成本（每股） |
| `currency` | 貨幣（TWD / USD） |
| `alert_change_percent` | 今日漲跌幅門檻（選填） |
| `alert_gain_percent` | 未實現損益門檻（選填） |

### 4. 執行

**一次性查詢（不啟動 Bot）：**

```bash
python -m portfolio_watch --portfolio data/portfolio.csv --provider yfinance
```

**啟動 Bot 模式（持續監控 + 回應指令）：**

```bash
python -m portfolio_watch --portfolio data/portfolio.csv --provider yfinance --watch
```

啟動後在 Telegram 傳 `/status` 或 `/summary` 即可查詢。

## 測試

```bash
pytest
```

## 安全說明

- `.env` 與 `data/portfolio.csv` 已列入 `.gitignore`，不會上傳 GitHub
- Telegram Bot Token 僅存在本機 `.env`，不會出現在程式碼或錯誤訊息中
- 版控內只保留範例資料（`portfolio.example.csv`）與程式碼

## 系統需求

- Python 3.11+
- 網路連線（yfinance 抓取行情）
- Telegram 帳號（通知功能）

## License

MIT
