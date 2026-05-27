from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from portfolio_watch.database import DB_PATH
from portfolio_watch.market_hours import is_weekday_market_time
from portfolio_watch.portfolio import load_positions_from_db
from portfolio_watch.pricing import PriceProvider
from portfolio_watch.watcher import build_snapshots

app = FastAPI()

_price_provider: PriceProvider | None = None
_db_path: Path = DB_PATH


def init_web(price_provider: PriceProvider, db_path: Path = DB_PATH) -> None:
    global _price_provider, _db_path
    _price_provider = price_provider
    _db_path = db_path


@app.get("/api/data")
def api_data():
    positions = load_positions_from_db(_db_path)
    snapshots = build_snapshots(positions, _price_provider)
    market_open = is_weekday_market_time()

    total_cost = sum(s.cost_basis for s in snapshots)
    total_value = sum(s.market_value for s in snapshots)
    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost else 0
    total_daily_gain = sum(s.market_value * (s.quote.change_percent / 100) for s in snapshots)

    rows = [
        {
            "symbol": s.position.symbol,
            "name": s.position.name,
            "price": s.quote.price,
            "change_percent": s.quote.change_percent,
            "currency": s.quote.currency,
            "quantity": s.position.quantity,
            "market_value": s.market_value,
            "unrealized_gain": s.unrealized_gain,
            "unrealized_gain_percent": s.unrealized_gain_percent,
            "daily_gain": s.market_value * (s.quote.change_percent / 100),
            "alert_change_percent": s.position.alert_change_percent,
            "alert_gain_percent": s.position.alert_gain_percent,
        }
        for s in snapshots
    ]

    return {
        "market_open": market_open,
        "rows": rows,
        "total_value": total_value,
        "total_gain": total_gain,
        "total_gain_pct": total_gain_pct,
        "total_daily_gain": total_daily_gain,
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Simple green circle SVG as favicon
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="16" fill="#0f172a"/><rect x="7" y="18" width="4" height="7" fill="#22d3ee" rx="1"/><rect x="14" y="12" width="4" height="13" fill="#6366f1" rx="1"/><rect x="21" y="8" width="4" height="17" fill="#4ade80" rx="1"/></svg>'
    return Response(content=svg.encode(), media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(_HTML)


_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio Watch</title>
  <link rel="icon" href="/favicon.ico">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    header { padding: 16px 20px; border-bottom: 1px solid #1e293b; display: flex; align-items: center; gap: 12px; }
    header h1 { font-size: 1.1rem; font-weight: 600; }
    #market-badge { font-size: 0.75rem; padding: 3px 10px; border-radius: 99px; font-weight: 500; }
    .open  { background: #166534; color: #86efac; }
    .closed { background: #1e293b; color: #94a3b8; }

    main { padding: 16px 20px; display: grid; gap: 16px; }

    /* Cards */
    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card { background: #1e293b; border-radius: 12px; padding: 16px; }
    .card-label { font-size: 0.7rem; color: #64748b; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .05em; }
    .card-value { font-size: 1.3rem; font-weight: 700; }
    .card-sub { font-size: 0.8rem; margin-top: 4px; }
    .pos { color: #4ade80; } .neg { color: #f87171; }

    /* Bottom layout: table + pie side by side on desktop, stacked on mobile */
    .bottom { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }

    /* Table */
    .table-wrap { overflow-x: auto; border-radius: 12px; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; min-width: 480px; }
    th { background: #0f172a; padding: 10px 14px; text-align: left; font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; white-space: nowrap; }
    td { padding: 12px 14px; border-top: 1px solid #0f172a; font-size: 0.85rem; vertical-align: top; }
    tr:hover td { background: #263348; }

    /* Alert badge */
    .alert-bar { margin-top: 4px; height: 3px; border-radius: 99px; background: #1e293b; overflow: hidden; }
    .alert-bar-fill { height: 100%; border-radius: 99px; transition: width 0.3s; }
    .alert-label { font-size: 0.7rem; margin-top: 2px; }
    .alert-triggered { color: #f87171; }
    .alert-near { color: #f59e0b; }
    .alert-ok { color: #475569; }

    /* Pie */
    .pie-wrap { background: #1e293b; border-radius: 12px; padding: 16px; }
    .pie-wrap h2 { font-size: 0.75rem; color: #64748b; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .05em; }

    #updated { font-size: 0.7rem; color: #475569; text-align: right; margin-top: 6px; }

    /* Mobile */
    @media (max-width: 640px) {
      .cards { grid-template-columns: 1fr 1fr; }
      .cards .card:last-child { grid-column: span 2; }
      .bottom { grid-template-columns: 1fr; }
      .pie-wrap { order: -1; }
    }
  </style>
</head>
<body>
  <header>
    <h1>📊 Portfolio Watch</h1>
    <span id="market-badge">—</span>
  </header>
  <main>
    <div class="cards">
      <div class="card">
        <div class="card-label">總市值</div>
        <div class="card-value" id="total-value">—</div>
      </div>
      <div class="card">
        <div class="card-label">未實現損益</div>
        <div class="card-value" id="total-gain">—</div>
        <div class="card-sub" id="total-gain-pct">—</div>
      </div>
      <div class="card">
        <div class="card-label">今日損益</div>
        <div class="card-value" id="daily-gain">—</div>
      </div>
    </div>
    <div class="bottom">
      <div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>股票</th>
                <th>現價</th>
                <th>今日</th>
                <th>市值</th>
                <th>未實現損益</th>
                <th>警示狀態</th>
              </tr>
            </thead>
            <tbody id="table-body"></tbody>
          </table>
        </div>
        <div id="updated"></div>
      </div>
      <div class="pie-wrap">
        <h2>持股比例</h2>
        <canvas id="pie"></canvas>
      </div>
    </div>
  </main>
  <script>
    let pieChart = null;

    function fmt(n, dec=2) {
      return n.toLocaleString('zh-TW', {minimumFractionDigits: dec, maximumFractionDigits: dec});
    }
    function sign(n) { return n >= 0 ? '+' : ''; }
    function cls(n) { return n >= 0 ? 'pos' : 'neg'; }

    function alertCell(r) {
      const absChange = Math.abs(r.change_percent);
      const absGain   = Math.abs(r.unrealized_gain_percent);

      // Check change_percent alert
      if (r.alert_change_percent) {
        const pct = Math.min(absChange / r.alert_change_percent, 1);
        const triggered = absChange >= r.alert_change_percent;
        const near = pct >= 0.8;
        const labelCls = triggered ? 'alert-triggered' : near ? 'alert-near' : 'alert-ok';
        const barColor = triggered ? '#f87171' : near ? '#f59e0b' : '#4ade80';
        const label = triggered ? '⚠️ 已觸發' : `${fmt(absChange)}% / ${r.alert_change_percent}%`;
        return `
          <div class="alert-label ${labelCls}">${label}</div>
          <div class="alert-bar"><div class="alert-bar-fill" style="width:${pct*100}%;background:${barColor}"></div></div>`;
      }

      // Check gain alert
      if (r.alert_gain_percent) {
        const pct = Math.min(absGain / r.alert_gain_percent, 1);
        const triggered = absGain >= r.alert_gain_percent;
        const near = pct >= 0.8;
        const labelCls = triggered ? 'alert-triggered' : near ? 'alert-near' : 'alert-ok';
        const barColor = triggered ? '#f87171' : near ? '#f59e0b' : '#4ade80';
        const label = triggered ? '⚠️ 已觸發' : `${fmt(absGain)}% / ${r.alert_gain_percent}%`;
        return `
          <div class="alert-label ${labelCls}">${label}</div>
          <div class="alert-bar"><div class="alert-bar-fill" style="width:${pct*100}%;background:${barColor}"></div></div>`;
      }

      return '<span style="color:#475569;font-size:0.75rem">未設定</span>';
    }

    async function refresh() {
      const res = await fetch('/api/data');
      const d = await res.json();

      const badge = document.getElementById('market-badge');
      badge.textContent = d.market_open ? '開市中' : '休市';
      badge.className = d.market_open ? 'open' : 'closed';

      document.getElementById('total-value').textContent = 'TWD ' + fmt(d.total_value);

      const tg = document.getElementById('total-gain');
      tg.textContent = sign(d.total_gain) + fmt(d.total_gain);
      tg.className = 'card-value ' + cls(d.total_gain);

      const tgp = document.getElementById('total-gain-pct');
      tgp.textContent = sign(d.total_gain_pct) + fmt(d.total_gain_pct) + '%';
      tgp.className = 'card-sub ' + cls(d.total_gain_pct);

      const dg = document.getElementById('daily-gain');
      dg.textContent = sign(d.total_daily_gain) + fmt(d.total_daily_gain);
      dg.className = 'card-value ' + cls(d.total_daily_gain);

      const tbody = document.getElementById('table-body');
      tbody.innerHTML = d.rows.map(r => `
        <tr>
          <td><strong>${r.symbol}</strong><br><span style="color:#64748b;font-size:0.78rem">${r.name}</span></td>
          <td>${r.currency} ${fmt(r.price)}</td>
          <td class="${cls(r.change_percent)}">${sign(r.change_percent)}${fmt(r.change_percent)}%<br>
            <span style="font-size:0.78rem">${sign(r.daily_gain)}${fmt(r.daily_gain)}</span></td>
          <td>${fmt(r.market_value)}</td>
          <td class="${cls(r.unrealized_gain)}">
            ${sign(r.unrealized_gain)}${fmt(r.unrealized_gain)}<br>
            <span style="font-size:0.78rem">${sign(r.unrealized_gain_percent)}${fmt(r.unrealized_gain_percent)}%</span>
          </td>
          <td>${alertCell(r)}</td>
        </tr>
      `).join('');

      const labels = d.rows.map(r => r.symbol);
      const values = d.rows.map(r => r.market_value);
      const colors = ['#6366f1','#22d3ee','#f59e0b','#4ade80','#f87171','#a78bfa'];

      if (pieChart) {
        pieChart.data.labels = labels;
        pieChart.data.datasets[0].data = values;
        pieChart.update();
      } else {
        pieChart = new Chart(document.getElementById('pie'), {
          type: 'doughnut',
          data: {
            labels,
            datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }]
          },
          options: {
            plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 11 } } } },
            cutout: '60%'
          }
        });
      }

      document.getElementById('updated').textContent =
        '更新於 ' + new Date().toLocaleTimeString('zh-TW');
    }

    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>"""
