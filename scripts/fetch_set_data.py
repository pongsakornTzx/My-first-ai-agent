#!/usr/bin/env python3
"""
SET Thailand Stock Analysis System
Fetches data from Yahoo Finance, calculates technical signals,
and generates a self-contained HTML dashboard.
"""

import json
import math
import os
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import numpy as np

# ============================================================
# WATCHLIST — read from config/watchlist.json
# ============================================================
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "watchlist.json")

def load_watchlist() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stocks", {})
    except FileNotFoundError:
        print("[WARN] config/watchlist.json not found, using defaults")
        return _DEFAULT_WATCHLIST

_DEFAULT_WATCHLIST = {
    "PTT":    {"name": "ปตท",              "sector": "พลังงาน"},
    "KBANK":  {"name": "กสิกรไทย",         "sector": "การเงิน"},
    "AOT":    {"name": "ท่าอากาศยาน",      "sector": "คมนาคม"},
    "ADVANC": {"name": "AIS แอดวานซ์",     "sector": "โทรคมนาคม"},
    "SCB":    {"name": "ไทยพาณิชย์",       "sector": "การเงิน"},
    "CPALL":  {"name": "ซีพี ออลล์",       "sector": "พาณิชย์"},
    "GULF":   {"name": "กัลฟ์",            "sector": "พลังงาน"},
    "BDMS":   {"name": "กรุงเทพดุสิต",     "sector": "สุขภาพ"},
    "TRUE":   {"name": "ทรู คอร์ปอเรชั่น", "sector": "โทรคมนาคม"},
    "BBL":    {"name": "กรุงเทพ",          "sector": "การเงิน"},
}

WATCHLIST = load_watchlist()

SECTOR_COLORS = {
    "พลังงาน":       "#f59e0b",
    "การเงิน":       "#3b82f6",
    "คมนาคม":        "#8b5cf6",
    "โทรคมนาคม":    "#06b6d4",
    "พาณิชย์":       "#10b981",
    "สุขภาพ":        "#ec4899",
}

# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calc_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.dropna().iloc[-1] if not rsi.dropna().empty else 50.0
    return round(float(val), 2)


def calc_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    last = lambda s: float(s.dropna().iloc[-1]) if not s.dropna().empty else 0.0
    return round(last(macd_line), 4), round(last(signal_line), 4), round(last(histogram), 4)


def calc_bollinger(series: pd.Series, period: int = 20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    last = lambda s: float(s.dropna().iloc[-1]) if not s.dropna().empty else 0.0
    return round(last(upper), 2), round(last(sma), 2), round(last(lower), 2)


def calc_volume_ratio(vol: pd.Series, period: int = 20) -> float:
    avg = vol.rolling(period).mean()
    ratio = vol / avg
    val = ratio.dropna().iloc[-1] if not ratio.dropna().empty else 1.0
    return round(float(val), 2)


def calc_momentum(series: pd.Series, period: int = 10) -> float:
    if len(series) < period + 1:
        return 0.0
    current = series.iloc[-1]
    past = series.iloc[-period - 1]
    return round(float((current - past) / past * 100), 2) if past != 0 else 0.0


def calc_ma(series: pd.Series, period: int) -> float:
    ma = series.rolling(period).mean()
    val = ma.dropna().iloc[-1] if not ma.dropna().empty else float(series.iloc[-1])
    return round(float(val), 2)

# ============================================================
# SIGNAL ENGINE
# ============================================================

def generate_signals(data: dict) -> dict:
    signals = []
    score = 0  # positive = bullish, negative = bearish

    rsi = data["rsi"]
    macd_hist = data["macd_histogram"]
    price = data["price"]
    bb_upper = data["bb_upper"]
    bb_lower = data["bb_lower"]
    bb_mid = data["bb_mid"]
    vol_ratio = data["volume_ratio"]
    momentum = data["momentum_10d"]
    ma20 = data["ma20"]
    ma50 = data["ma50"]

    # RSI
    if rsi < 30:
        signals.append({"type": "bullish", "label": "RSI Oversold", "detail": f"RSI={rsi} < 30 สัญญาณซื้อ"})
        score += 2
    elif rsi > 70:
        signals.append({"type": "bearish", "label": "RSI Overbought", "detail": f"RSI={rsi} > 70 สัญญาณขาย"})
        score -= 2
    elif 40 <= rsi <= 60:
        signals.append({"type": "neutral", "label": "RSI Neutral", "detail": f"RSI={rsi} แนวโน้มกลาง"})

    # MACD
    if macd_hist > 0:
        signals.append({"type": "bullish", "label": "MACD Bullish", "detail": f"MACD histogram={macd_hist:.4f} บวก"})
        score += 1
    elif macd_hist < 0:
        signals.append({"type": "bearish", "label": "MACD Bearish", "detail": f"MACD histogram={macd_hist:.4f} ลบ"})
        score -= 1

    # Bollinger Bands
    if price <= bb_lower:
        signals.append({"type": "bullish", "label": "BB Lower Touch", "detail": f"ราคาแตะ Lower Band สัญญาณ Bounce"})
        score += 2
    elif price >= bb_upper:
        signals.append({"type": "bearish", "label": "BB Upper Touch", "detail": f"ราคาแตะ Upper Band อาจ Pullback"})
        score -= 2
    elif price > bb_mid:
        signals.append({"type": "bullish", "label": "BB Mid-Upper", "detail": "ราคาอยู่เหนือ Midline แนวโน้มบวก"})
        score += 1

    # Volume
    if vol_ratio > 2.0:
        signals.append({"type": "alert", "label": "Volume Spike", "detail": f"ปริมาณซื้อขาย {vol_ratio}x ค่าเฉลี่ย!"})
        score += 1 if momentum > 0 else -1
    elif vol_ratio > 1.5:
        signals.append({"type": "alert", "label": "High Volume", "detail": f"ปริมาณสูง {vol_ratio}x เฉลี่ย"})

    # Momentum
    if momentum > 5:
        signals.append({"type": "bullish", "label": "Strong Momentum", "detail": f"โมเมนตัม +{momentum}% (10 วัน)"})
        score += 2
    elif momentum > 2:
        signals.append({"type": "bullish", "label": "Positive Momentum", "detail": f"โมเมนตัม +{momentum}% (10 วัน)"})
        score += 1
    elif momentum < -5:
        signals.append({"type": "bearish", "label": "Weak Momentum", "detail": f"โมเมนตัม {momentum}% (10 วัน)"})
        score -= 2
    elif momentum < -2:
        signals.append({"type": "bearish", "label": "Negative Momentum", "detail": f"โมเมนตัม {momentum}% (10 วัน)"})
        score -= 1

    # MA Cross
    if ma20 > ma50 and price > ma20:
        signals.append({"type": "bullish", "label": "MA Alignment", "detail": "Price > MA20 > MA50 เทรนด์ขึ้น"})
        score += 2
    elif ma20 < ma50 and price < ma20:
        signals.append({"type": "bearish", "label": "MA Downtrend", "detail": "Price < MA20 < MA50 เทรนด์ลง"})
        score -= 2

    # Overall verdict
    if score >= 4:
        verdict = "ซื้อ (Strong Buy)"
        verdict_class = "strong-buy"
    elif score >= 2:
        verdict = "ซื้อ (Buy)"
        verdict_class = "buy"
    elif score <= -4:
        verdict = "ขาย (Strong Sell)"
        verdict_class = "strong-sell"
    elif score <= -2:
        verdict = "ขาย (Sell)"
        verdict_class = "sell"
    else:
        verdict = "ถือ (Hold)"
        verdict_class = "hold"

    return {"signals": signals, "score": score, "verdict": verdict, "verdict_class": verdict_class}


def ai_summary(ticker: str, name: str, data: dict, sig: dict) -> str:
    price = data["price"]
    change_pct = data["change_pct"]
    rsi = data["rsi"]
    vol_ratio = data["volume_ratio"]
    momentum = data["momentum_10d"]
    verdict = sig["verdict"]
    score = sig["score"]
    direction = "บวก" if change_pct >= 0 else "ลบ"
    trend = "ขาขึ้น" if score > 0 else ("ขาลง" if score < 0 else "ทรงตัว")

    vol_desc = "สูงกว่าปกติมาก" if vol_ratio > 2 else ("สูงกว่าปกติ" if vol_ratio > 1.5 else "ปกติ")
    rsi_desc = "ขาย Oversold" if rsi < 30 else ("เริ่ม Overbought" if rsi > 65 else "กลาง")
    mom_desc = f"เพิ่มขึ้น {abs(momentum):.1f}%" if momentum > 0 else f"ลดลง {abs(momentum):.1f}%"

    bullish_count = sum(1 for s in sig["signals"] if s["type"] == "bullish")
    bearish_count = sum(1 for s in sig["signals"] if s["type"] == "bearish")

    summary = (
        f"<strong>{ticker} ({name})</strong> ราคาปัจจุบัน {price:.2f} บาท "
        f"เปลี่ยนแปลง{direction} {abs(change_pct):.2f}% วันนี้ "
        f"ภาพรวมสัญญาณเทคนิคเป็น<strong>{trend}</strong> "
        f"โดยมี {bullish_count} สัญญาณบวก และ {bearish_count} สัญญาณลบ "
        f"RSI อยู่ที่ {rsi} ({rsi_desc}) "
        f"ปริมาณซื้อขาย{vol_desc} ({vol_ratio}x เฉลี่ย) "
        f"โมเมนตัม 10 วัน{mom_desc} "
        f"<strong>คำแนะนำ: {verdict}</strong>"
    )
    return summary

# ============================================================
# DATA FETCHER
# ============================================================

def fetch_stock(ticker: str) -> dict | None:
    symbol = f"{ticker}.BK"
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 30:
            print(f"  [WARN] {ticker}: insufficient data")
            return None

        close = hist["Close"]
        volume = hist["Volume"]
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        change = price - prev
        change_pct = (change / prev) * 100

        rsi = calc_rsi(close)
        macd_line, macd_signal, macd_hist = calc_macd(close)
        bb_upper, bb_mid, bb_lower = calc_bollinger(close)
        vol_ratio = calc_volume_ratio(volume)
        momentum = calc_momentum(close)
        ma20 = calc_ma(close, 20)
        ma50 = calc_ma(close, 50)

        # Last 30 days of closing prices for sparkline
        sparkline = [round(float(v), 2) for v in close.tail(30).tolist()]

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "rsi": rsi,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "bb_upper": bb_upper,
            "bb_mid": bb_mid,
            "bb_lower": bb_lower,
            "volume_ratio": vol_ratio,
            "momentum_10d": momentum,
            "ma20": ma20,
            "ma50": ma50,
            "sparkline": sparkline,
        }
    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return None

# ============================================================
# HTML GENERATOR
# ============================================================

def build_html(stocks: list) -> str:
    now_bkk = datetime.now(timezone.utc)
    # UTC+7
    from datetime import timedelta
    now_bkk = now_bkk + timedelta(hours=7)
    updated = now_bkk.strftime("%d/%m/%Y %H:%M") + " (ICT)"

    # Build market overview
    total = len(stocks)
    bullish_stocks = [s for s in stocks if s["sig"]["score"] > 0]
    bearish_stocks = [s for s in stocks if s["sig"]["score"] < 0]
    neutral_stocks = [s for s in stocks if s["sig"]["score"] == 0]
    avg_rsi = round(sum(s["data"]["rsi"] for s in stocks) / total, 1) if total else 0

    cards_html = ""
    for s in stocks:
        ticker = s["ticker"]
        info = s["info"]
        data = s["data"]
        sig = s["sig"]
        summary = s["summary"]

        sector_color = SECTOR_COLORS.get(info["sector"], "#6b7280")
        change_color = "#10b981" if data["change_pct"] >= 0 else "#ef4444"
        change_arrow = "▲" if data["change_pct"] >= 0 else "▼"
        vc = sig["verdict_class"]
        verdict_colors = {
            "strong-buy":  ("#052e16", "#16a34a", "#22c55e"),
            "buy":         ("#052e16", "#15803d", "#4ade80"),
            "hold":        ("#1c1917", "#92400e", "#fbbf24"),
            "sell":        ("#2d0000", "#b91c1c", "#f87171"),
            "strong-sell": ("#2d0000", "#991b1b", "#ef4444"),
        }
        vbg, vborder, vtext = verdict_colors.get(vc, ("#1c1917", "#6b7280", "#d1d5db"))

        # Signal badges
        signal_badges = ""
        for sig_item in sig["signals"]:
            t = sig_item["type"]
            badge_colors = {
                "bullish": "background:#052e16;color:#4ade80;border:1px solid #16a34a",
                "bearish": "background:#2d0000;color:#f87171;border:1px solid #b91c1c",
                "neutral": "background:#1c1917;color:#d1d5db;border:1px solid #374151",
                "alert":   "background:#1c1400;color:#fbbf24;border:1px solid #92400e",
            }
            bstyle = badge_colors.get(t, badge_colors["neutral"])
            signal_badges += f'<span class="signal-badge" style="{bstyle}" title="{sig_item["detail"]}">{sig_item["label"]}</span>'

        # RSI bar
        rsi_color = "#22c55e" if data["rsi"] < 30 else ("#ef4444" if data["rsi"] > 70 else "#3b82f6")
        rsi_pct = min(data["rsi"], 100)

        # Sparkline data
        sp = data["sparkline"]
        sp_min = min(sp)
        sp_max = max(sp)
        sp_range = sp_max - sp_min or 1
        w = 120
        h = 40
        pts = []
        for i, v in enumerate(sp):
            x = i * w / (len(sp) - 1)
            y = h - ((v - sp_min) / sp_range) * h
            pts.append(f"{x:.1f},{y:.1f}")
        spark_line = " ".join(pts)
        spark_color = "#10b981" if sp[-1] >= sp[0] else "#ef4444"

        cards_html += f"""
        <div class="stock-card" id="card-{ticker}">
          <div class="card-header">
            <div class="ticker-info">
              <span class="ticker-symbol">{ticker}</span>
              <span class="sector-tag" style="background:{sector_color}20;color:{sector_color};border:1px solid {sector_color}40">{info["sector"]}</span>
            </div>
            <span class="company-name">{info["name"]}</span>
          </div>

          <div class="price-row">
            <div class="price-main">
              <span class="price-value">{data["price"]:.2f}</span>
              <span class="price-unit">฿</span>
            </div>
            <div class="price-change" style="color:{change_color}">
              {change_arrow} {abs(data["change_pct"]):.2f}%
              <span style="font-size:0.75rem;opacity:0.8">({data["change"]:+.2f})</span>
            </div>
          </div>

          <div class="sparkline-container">
            <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
              <polyline points="{spark_line}" fill="none" stroke="{spark_color}" stroke-width="1.5" stroke-linejoin="round"/>
            </svg>
          </div>

          <div class="indicators-grid">
            <div class="indicator">
              <span class="ind-label">RSI(14)</span>
              <span class="ind-value" style="color:{rsi_color}">{data["rsi"]}</span>
              <div class="rsi-bar"><div style="width:{rsi_pct}%;background:{rsi_color}"></div></div>
            </div>
            <div class="indicator">
              <span class="ind-label">MACD Hist</span>
              <span class="ind-value" style="color:{'#22c55e' if data['macd_histogram']>0 else '#ef4444'}">{data["macd_histogram"]:+.4f}</span>
            </div>
            <div class="indicator">
              <span class="ind-label">BB Position</span>
              <span class="ind-value">{data["price"]:.2f} / {data["bb_upper"]:.2f}</span>
            </div>
            <div class="indicator">
              <span class="ind-label">Vol Ratio</span>
              <span class="ind-value" style="color:{'#fbbf24' if data['volume_ratio']>1.5 else '#9ca3af'}">{data["volume_ratio"]}x</span>
            </div>
            <div class="indicator">
              <span class="ind-label">MA20/MA50</span>
              <span class="ind-value">{data["ma20"]:.2f} / {data["ma50"]:.2f}</span>
            </div>
            <div class="indicator">
              <span class="ind-label">Mom 10d</span>
              <span class="ind-value" style="color:{'#22c55e' if data['momentum_10d']>=0 else '#ef4444'}">{data["momentum_10d"]:+.2f}%</span>
            </div>
          </div>

          <div class="signals-row">{signal_badges}</div>

          <div class="verdict-box" style="background:{vbg};border:1px solid {vborder};color:{vtext}">
            {sig["verdict"]}  (score: {sig["score"]:+d})
          </div>

          <div class="ai-summary">{summary}</div>
        </div>
        """

    # Market overview bar
    overview_html = f"""
    <div class="overview-bar">
      <div class="ov-item"><span class="ov-label">หุ้นทั้งหมด</span><span class="ov-val">{total}</span></div>
      <div class="ov-item"><span class="ov-label">สัญญาณบวก</span><span class="ov-val" style="color:#22c55e">{len(bullish_stocks)}</span></div>
      <div class="ov-item"><span class="ov-label">สัญญาณลบ</span><span class="ov-val" style="color:#ef4444">{len(bearish_stocks)}</span></div>
      <div class="ov-item"><span class="ov-label">ทรงตัว</span><span class="ov-val" style="color:#fbbf24">{len(neutral_stocks)}</span></div>
      <div class="ov-item"><span class="ov-label">RSI เฉลี่ย</span><span class="ov-val" style="color:#3b82f6">{avg_rsi}</span></div>
      <div class="ov-item"><span class="ov-label">อัปเดต</span><span class="ov-val" style="font-size:0.8rem">{updated}</span></div>
    </div>
    """

    # Top movers
    sorted_by_change = sorted(stocks, key=lambda s: s["data"]["change_pct"], reverse=True)
    top_gainers = sorted_by_change[:3]
    top_losers = sorted_by_change[-3:][::-1]

    def mover_item(s, color):
        return f'<div class="mover"><strong style="color:{color}">{s["ticker"]}</strong> {s["data"]["change_pct"]:+.2f}%</div>'

    movers_html = f"""
    <div class="movers-bar">
      <div class="movers-section">
        <span class="movers-title" style="color:#22c55e">TOP ขึ้น</span>
        {''.join(mover_item(s, '#22c55e') for s in top_gainers)}
      </div>
      <div class="movers-section">
        <span class="movers-title" style="color:#ef4444">TOP ลง</span>
        {''.join(mover_item(s, '#ef4444') for s in top_losers)}
      </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SET Thailand — AI Stock Analysis</title>
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --text: #e2e8f0;
    --muted: #6b7280;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, sans-serif; min-height: 100vh; }}
  .header {{
    background: linear-gradient(135deg, #0f0f1a 0%, #1a0a2e 50%, #0a1628 100%);
    border-bottom: 1px solid var(--border);
    padding: 1.5rem 2rem;
    display: flex; align-items: center; gap: 1rem;
  }}
  .header-icon {{ font-size: 2rem; }}
  .header-title {{ font-size: 1.5rem; font-weight: 700; color: #fff; }}
  .header-sub {{ font-size: 0.85rem; color: var(--muted); margin-top: 0.2rem; }}
  .header-badge {{
    margin-left: auto; background: #052e16; color: #22c55e;
    border: 1px solid #16a34a; border-radius: 999px;
    padding: 0.3rem 0.8rem; font-size: 0.75rem; font-weight: 600;
  }}
  .overview-bar {{
    display: flex; flex-wrap: wrap; gap: 1rem;
    padding: 1rem 2rem; background: var(--surface);
    border-bottom: 1px solid var(--border);
  }}
  .ov-item {{ display: flex; flex-direction: column; align-items: center; gap: 0.2rem; min-width: 80px; }}
  .ov-label {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }}
  .ov-val {{ font-size: 1.1rem; font-weight: 700; }}
  .movers-bar {{
    display: flex; gap: 2rem; padding: 0.8rem 2rem;
    background: var(--surface2); border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }}
  .movers-section {{ display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }}
  .movers-title {{ font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
  .mover {{ font-size: 0.85rem; background: var(--surface); padding: 0.2rem 0.6rem; border-radius: 6px; }}
  .filter-bar {{
    padding: 1rem 2rem; display: flex; gap: 0.5rem; flex-wrap: wrap;
    background: var(--bg); border-bottom: 1px solid var(--border);
  }}
  .filter-btn {{
    background: var(--surface); border: 1px solid var(--border);
    color: var(--muted); padding: 0.3rem 0.9rem; border-radius: 999px;
    cursor: pointer; font-size: 0.8rem; transition: all 0.2s;
  }}
  .filter-btn:hover, .filter-btn.active {{
    background: #1e3a5f; border-color: #3b82f6; color: #93c5fd;
  }}
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 1.25rem; padding: 1.5rem 2rem;
  }}
  .stock-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.25rem;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .stock-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
  .card-header {{ display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.75rem; }}
  .ticker-info {{ display: flex; align-items: center; gap: 0.5rem; }}
  .ticker-symbol {{ font-size: 1.2rem; font-weight: 800; color: #fff; }}
  .sector-tag {{ font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 999px; font-weight: 600; }}
  .company-name {{ font-size: 0.85rem; color: var(--muted); }}
  .price-row {{ display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 0.5rem; }}
  .price-main {{ display: flex; align-items: baseline; gap: 0.2rem; }}
  .price-value {{ font-size: 1.8rem; font-weight: 800; color: #fff; }}
  .price-unit {{ font-size: 0.9rem; color: var(--muted); }}
  .price-change {{ font-size: 0.95rem; font-weight: 700; }}
  .sparkline-container {{ margin: 0.5rem 0; }}
  .indicators-grid {{
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 0.5rem; margin: 0.75rem 0;
  }}
  .indicator {{
    background: var(--surface2); border-radius: 8px; padding: 0.5rem;
    display: flex; flex-direction: column; gap: 0.1rem;
  }}
  .ind-label {{ font-size: 0.65rem; color: var(--muted); text-transform: uppercase; }}
  .ind-value {{ font-size: 0.85rem; font-weight: 700; }}
  .rsi-bar {{ height: 3px; background: #2a2a3a; border-radius: 2px; margin-top: 0.2rem; overflow: hidden; }}
  .rsi-bar div {{ height: 100%; border-radius: 2px; }}
  .signals-row {{ display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.75rem 0; }}
  .signal-badge {{
    font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 999px;
    font-weight: 600; cursor: default; white-space: nowrap;
  }}
  .verdict-box {{
    border-radius: 8px; padding: 0.6rem 1rem; text-align: center;
    font-weight: 700; font-size: 0.9rem; margin: 0.5rem 0;
  }}
  .ai-summary {{
    font-size: 0.78rem; color: #94a3b8; line-height: 1.6;
    background: var(--surface2); border-radius: 8px; padding: 0.75rem;
    margin-top: 0.5rem; border-left: 3px solid #3b82f6;
  }}
  .footer {{
    text-align: center; padding: 2rem; color: var(--muted); font-size: 0.75rem;
    border-top: 1px solid var(--border);
  }}
  .pulse {{ animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100%{{ opacity:1 }} 50%{{ opacity:0.5 }} }}

  /* Add Stock Button */
  .add-stock-btn {{
    margin-left: auto; background: linear-gradient(135deg, #1e3a5f, #1e4080);
    border: 1px solid #3b82f6; color: #93c5fd;
    padding: 0.35rem 1rem; border-radius: 999px;
    cursor: pointer; font-size: 0.85rem; font-weight: 600;
    transition: all 0.2s;
  }}
  .add-stock-btn:hover {{ background: #2563eb; color: #fff; transform: translateY(-1px); }}

  /* Modal */
  .modal-overlay {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.75); backdrop-filter: blur(4px);
    z-index: 1000; align-items: center; justify-content: center;
  }}
  .modal-box {{
    background: #13131f; border: 1px solid #2a2a3a; border-radius: 16px;
    width: min(480px, 95vw); max-height: 90vh; overflow-y: auto;
    box-shadow: 0 24px 64px rgba(0,0,0,0.6);
  }}
  .modal-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.25rem 1.5rem; border-bottom: 1px solid #2a2a3a;
    font-size: 1rem; font-weight: 700; color: #fff;
  }}
  .modal-close {{
    background: none; border: none; color: #6b7280; cursor: pointer;
    font-size: 1.1rem; padding: 0.2rem 0.5rem; border-radius: 6px;
    transition: color 0.2s;
  }}
  .modal-close:hover {{ color: #fff; }}
  .modal-body {{ padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }}
  .input-row {{ display: flex; gap: 0.5rem; }}
  .ticker-input {{
    flex: 1; background: #1a1a24; border: 1px solid #2a2a3a; color: #fff;
    border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.95rem;
    outline: none; transition: border-color 0.2s; text-transform: uppercase;
  }}
  .ticker-input:focus {{ border-color: #3b82f6; }}
  .add-btn {{
    background: #2563eb; color: #fff; border: none; border-radius: 8px;
    padding: 0.6rem 1.2rem; font-size: 0.9rem; font-weight: 600; cursor: pointer;
    transition: background 0.2s;
  }}
  .add-btn:hover {{ background: #1d4ed8; }}
  .add-status {{ font-size: 0.85rem; min-height: 1.2em; }}
  .suggestions {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}
  .sug-item {{
    background: #1e3a5f; color: #93c5fd; border: 1px solid #3b82f640;
    border-radius: 999px; padding: 0.2rem 0.6rem; font-size: 0.78rem;
    cursor: pointer; transition: background 0.15s;
  }}
  .sug-item:hover {{ background: #2563eb; color: #fff; }}
  .custom-list-label {{ font-size: 0.8rem; color: #6b7280; font-weight: 600; }}
  .custom-list {{ display: flex; flex-direction: column; gap: 0.35rem; }}
  .clist-item {{
    display: flex; align-items: center; justify-content: space-between;
    background: #1a1a24; border-radius: 8px; padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
  }}
  .clist-remove {{
    background: none; border: none; color: #ef4444; cursor: pointer;
    font-size: 0.78rem; padding: 0.1rem 0.4rem;
  }}
  .suggest-popular {{ display: flex; flex-direction: column; gap: 0.5rem; }}
  .suggest-title {{ font-size: 0.75rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }}
  .suggest-chips {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
  .suggest-chip {{
    background: #1a1a24; color: #94a3b8; border: 1px solid #2a2a3a;
    border-radius: 999px; padding: 0.25rem 0.65rem; font-size: 0.78rem;
    cursor: pointer; transition: all 0.15s;
  }}
  .suggest-chip:hover {{ background: #1e3a5f; color: #93c5fd; border-color: #3b82f6; }}

  @media(max-width:600px) {{
    .cards-grid {{ grid-template-columns: 1fr; padding: 1rem; }}
    .header {{ padding: 1rem; }}
    .overview-bar {{ padding: 0.75rem 1rem; }}
    .filter-bar {{ padding: 0.75rem 1rem; }}
    .add-stock-btn {{ margin-left: 0; width: 100%; text-align: center; }}
  }}
</style>
</head>
<body>

<header class="header">
  <span class="header-icon">📈</span>
  <div>
    <div class="header-title">SET Thailand — AI Stock Analysis</div>
    <div class="header-sub">ระบบวิเคราะห์หุ้นไทย · Data + Signal + AI Summary · อัปเดตทุก 30 นาที</div>
  </div>
  <div class="header-badge">
    <span class="pulse">●</span> Live Data
  </div>
</header>

{overview_html}
{movers_html}

<div class="filter-bar">
  <button class="filter-btn active" onclick="filterCards('all', this)">ทั้งหมด</button>
  <button class="filter-btn" onclick="filterCards('strong-buy', this)">Strong Buy</button>
  <button class="filter-btn" onclick="filterCards('buy', this)">Buy</button>
  <button class="filter-btn" onclick="filterCards('hold', this)">Hold</button>
  <button class="filter-btn" onclick="filterCards('sell', this)">Sell</button>
  <button class="filter-btn" onclick="filterCards('strong-sell', this)">Strong Sell</button>
  <button class="add-stock-btn" onclick="openModal()">+ เพิ่มหุ้น</button>
</div>

<!-- Add Stock Modal -->
<div id="stockModal" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-header">
      <span>เพิ่มหุ้นที่สนใจ</span>
      <button onclick="closeModal()" class="modal-close">✕</button>
    </div>
    <div class="modal-body">
      <div class="input-row">
        <input id="tickerInput" type="text" placeholder="พิมพ์ ticker เช่น MINT, SCC, DELTA..." class="ticker-input" oninput="onTickerInput(this.value)" onkeydown="if(event.key==='Enter')addCustomStock()"/>
        <button onclick="addCustomStock()" class="add-btn">เพิ่ม</button>
      </div>
      <div id="suggestions" class="suggestions"></div>
      <div id="addStatus" class="add-status"></div>
      <div class="custom-list-label">หุ้นที่เพิ่มไว้ <span id="customCount"></span></div>
      <div id="customList" class="custom-list"></div>
      <div class="suggest-popular">
        <div class="suggest-title">หุ้นยอดนิยม SET</div>
        <div class="suggest-chips">
          <span class="suggest-chip" onclick="quickAdd('MINT')">MINT</span>
          <span class="suggest-chip" onclick="quickAdd('SCC')">SCC</span>
          <span class="suggest-chip" onclick="quickAdd('DELTA')">DELTA</span>
          <span class="suggest-chip" onclick="quickAdd('PTTGC')">PTTGC</span>
          <span class="suggest-chip" onclick="quickAdd('IVL')">IVL</span>
          <span class="suggest-chip" onclick="quickAdd('BH')">BH</span>
          <span class="suggest-chip" onclick="quickAdd('CENTEL')">CENTEL</span>
          <span class="suggest-chip" onclick="quickAdd('KTC')">KTC</span>
          <span class="suggest-chip" onclick="quickAdd('OSP')">OSP</span>
          <span class="suggest-chip" onclick="quickAdd('HMPRO')">HMPRO</span>
          <span class="suggest-chip" onclick="quickAdd('TU')">TU</span>
          <span class="suggest-chip" onclick="quickAdd('BEM')">BEM</span>
        </div>
      </div>
    </div>
  </div>
</div>

<main class="cards-grid" id="cardsGrid">
{cards_html}
</main>
<div id="customCardsSection"></div>

<footer class="footer">
  อัปเดตล่าสุด: {updated} · ข้อมูลจาก Yahoo Finance (.BK) · อัปเดตอัตโนมัติทุก 30 นาที via GitHub Actions<br>
  <strong>คำเตือน:</strong> ข้อมูลนี้เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำการลงทุน กรุณาศึกษาข้อมูลเพิ่มเติมก่อนตัดสินใจ
</footer>

<script>
// ── Filter ──────────────────────────────────────────────────
document.querySelectorAll('.stock-card').forEach(card => {{
  const vtext = card.querySelector('.verdict-box')?.textContent || '';
  if (vtext.includes('Strong Buy')) card.dataset.verdict = 'strong-buy';
  else if (vtext.includes('Strong Sell')) card.dataset.verdict = 'strong-sell';
  else if (vtext.includes('ซื้อ (Buy)')) card.dataset.verdict = 'buy';
  else if (vtext.includes('ขาย (Sell)')) card.dataset.verdict = 'sell';
  else card.dataset.verdict = 'hold';
}});

function filterCards(filter, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.stock-card, .custom-stock-card').forEach(card => {{
    card.style.display = (filter === 'all' || card.dataset.verdict === filter) ? '' : 'none';
  }});
}}

// ── Modal ────────────────────────────────────────────────────
function openModal() {{
  document.getElementById('stockModal').style.display = 'flex';
  document.getElementById('tickerInput').focus();
  renderCustomList();
}}
function closeModal() {{
  document.getElementById('stockModal').style.display = 'none';
  document.getElementById('addStatus').textContent = '';
  document.getElementById('tickerInput').value = '';
  document.getElementById('suggestions').innerHTML = '';
}}

// ── localStorage watchlist ───────────────────────────────────
const LS_KEY = 'set_custom_watchlist_v2';
function getCustomList() {{
  try {{ return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); }} catch {{ return []; }}
}}
function saveCustomList(list) {{
  localStorage.setItem(LS_KEY, JSON.stringify(list));
}}

// ── Popular tickers autocomplete ─────────────────────────────
const POPULAR = ['MINT','SCC','DELTA','PTTGC','IVL','BH','CENTEL','KTC','OSP','HMPRO',
  'TU','BEM','CPN','GLOBAL','BJC','ERW','MAJOR','MTC','SAWAD','TIDLOR',
  'GPSC','RATCH','EGCO','BANPU','IRPC','TOP','SPRC','ESSO',
  'KKP','TISCO','TCAP','TMB','LHFG','ASK',
  'BGRIM','BCPG','SPCG','EA','AMATA','WHA',
  'DTAC','JMT','AEONTS','NOBLE','SPALI','LH','AP','SIRI','ORI'];

function onTickerInput(val) {{
  const v = val.toUpperCase().trim();
  const box = document.getElementById('suggestions');
  if (!v) {{ box.innerHTML=''; return; }}
  const matches = POPULAR.filter(t => t.startsWith(v) && t !== v).slice(0, 6);
  box.innerHTML = matches.map(t =>
    `<span class="sug-item" onclick="document.getElementById('tickerInput').value='${{t}}';document.getElementById('suggestions').innerHTML='';addCustomStock()">${{t}}</span>`
  ).join('');
}}

// ── Add stock ────────────────────────────────────────────────
async function addCustomStock() {{
  const raw = document.getElementById('tickerInput').value.trim().toUpperCase();
  if (!raw) return;
  const ticker = raw.endsWith('.BK') ? raw.replace('.BK','') : raw;
  const list = getCustomList();
  const status = document.getElementById('addStatus');

  if (list.includes(ticker)) {{
    status.textContent = `${{ticker}} อยู่ในรายการแล้ว`;
    status.style.color = '#fbbf24';
    return;
  }}

  status.textContent = `กำลังดึงข้อมูล ${{ticker}}...`;
  status.style.color = '#94a3b8';

  const ok = await fetchAndRenderCustomCard(ticker);
  if (ok) {{
    list.push(ticker);
    saveCustomList(list);
    renderCustomList();
    document.getElementById('tickerInput').value = '';
    document.getElementById('suggestions').innerHTML = '';
    status.textContent = `✓ เพิ่ม ${{ticker}} สำเร็จ`;
    status.style.color = '#22c55e';
  }} else {{
    status.textContent = `ไม่พบข้อมูล ${{ticker}} — ตรวจสอบชื่อ ticker อีกครั้ง`;
    status.style.color = '#ef4444';
  }}
}}

function quickAdd(ticker) {{
  document.getElementById('tickerInput').value = ticker;
  addCustomStock();
}}

// ── Yahoo Finance fetch (browser-side) ───────────────────────
async function fetchYahoo(symbol) {{
  const urls = [
    `https://query1.finance.yahoo.com/v8/finance/chart/${{symbol}}?range=3mo&interval=1d&events=div`,
    `https://query2.finance.yahoo.com/v8/finance/chart/${{symbol}}?range=3mo&interval=1d`,
    `https://corsproxy.io/?${{encodeURIComponent(`https://query1.finance.yahoo.com/v8/finance/chart/${{symbol}}?range=3mo&interval=1d`)}}`,
  ];
  for (const url of urls) {{
    try {{
      const r = await fetch(url, {{headers:{{'Accept':'application/json'}}}});
      if (!r.ok) continue;
      const data = await r.json();
      const result = data?.chart?.result?.[0];
      if (result) return result;
    }} catch {{}}
  }}
  return null;
}}

// ── JS Technical Indicators ──────────────────────────────────
function calcRSI(closes, period=14) {{
  if (closes.length < period+1) return 50;
  let gains=0, losses=0;
  for (let i=closes.length-period; i<closes.length; i++) {{
    const d = closes[i] - closes[i-1];
    if (d>0) gains+=d; else losses-=d;
  }}
  const avgG=gains/period, avgL=losses/period;
  if (avgL===0) return 100;
  return +(100 - 100/(1+avgG/avgL)).toFixed(2);
}}

function calcEMA(arr, span) {{
  const k = 2/(span+1);
  let ema = arr[0];
  const out = [ema];
  for (let i=1; i<arr.length; i++) {{ ema = arr[i]*k + ema*(1-k); out.push(ema); }}
  return out;
}}

function calcMACD(closes) {{
  const ema12 = calcEMA(closes,12), ema26 = calcEMA(closes,26);
  const macd = ema12.map((v,i)=>v-ema26[i]);
  const signal = calcEMA(macd,9);
  const hist = macd[macd.length-1] - signal[signal.length-1];
  return {{macd:+macd[macd.length-1].toFixed(4), signal:+signal[signal.length-1].toFixed(4), hist:+hist.toFixed(4)}};
}}

function calcBB(closes, period=20) {{
  const slice = closes.slice(-period);
  const mean = slice.reduce((a,b)=>a+b,0)/period;
  const std = Math.sqrt(slice.reduce((a,b)=>a+(b-mean)**2,0)/period);
  return {{upper:+(mean+2*std).toFixed(2), mid:+mean.toFixed(2), lower:+(mean-2*std).toFixed(2)}};
}}

function scoreSignals(price, rsi, macdHist, bb, volRatio, mom10, ma20, ma50) {{
  let score=0, signals=[];
  if (rsi<30) {{ score+=2; signals.push({{t:'bullish',l:'RSI Oversold',d:`RSI=${{rsi}} สัญญาณซื้อ`}}); }}
  else if (rsi>70) {{ score-=2; signals.push({{t:'bearish',l:'RSI Overbought',d:`RSI=${{rsi}} สัญญาณขาย`}}); }}
  if (macdHist>0) {{ score+=1; signals.push({{t:'bullish',l:'MACD Bullish',d:`histogram=${{macdHist}}`}}); }}
  else {{ score-=1; signals.push({{t:'bearish',l:'MACD Bearish',d:`histogram=${{macdHist}}`}}); }}
  if (price<=bb.lower) {{ score+=2; signals.push({{t:'bullish',l:'BB Lower Touch',d:'ราคาแตะ Lower Band'}}); }}
  else if (price>=bb.upper) {{ score-=2; signals.push({{t:'bearish',l:'BB Upper Touch',d:'ราคาแตะ Upper Band'}}); }}
  if (volRatio>2) {{ score+=(mom10>0?1:-1); signals.push({{t:'alert',l:'Volume Spike',d:`${{volRatio}}x เฉลี่ย`}}); }}
  if (mom10>5) {{ score+=2; signals.push({{t:'bullish',l:'Strong Momentum',d:`+${{mom10}}%`}}); }}
  else if (mom10>2) {{ score+=1; signals.push({{t:'bullish',l:'Momentum',d:`+${{mom10}}%`}}); }}
  else if (mom10<-5) {{ score-=2; signals.push({{t:'bearish',l:'Weak Momentum',d:`${{mom10}}%`}}); }}
  else if (mom10<-2) {{ score-=1; signals.push({{t:'bearish',l:'Momentum',d:`${{mom10}}%`}}); }}
  if (ma20>ma50&&price>ma20) {{ score+=2; signals.push({{t:'bullish',l:'MA Alignment',d:'Price>MA20>MA50'}}); }}
  else if (ma20<ma50&&price<ma20) {{ score-=2; signals.push({{t:'bearish',l:'MA Downtrend',d:'Price<MA20<MA50'}}); }}
  let verdict, vc;
  if (score>=4) {{ verdict='ซื้อ (Strong Buy)'; vc='strong-buy'; }}
  else if (score>=2) {{ verdict='ซื้อ (Buy)'; vc='buy'; }}
  else if (score<=-4) {{ verdict='ขาย (Strong Sell)'; vc='strong-sell'; }}
  else if (score<=-2) {{ verdict='ขาย (Sell)'; vc='sell'; }}
  else {{ verdict='ถือ (Hold)'; vc='hold'; }}
  return {{score, verdict, vc, signals}};
}}

// ── Build & inject a custom card ─────────────────────────────
async function fetchAndRenderCustomCard(ticker) {{
  const symbol = ticker+'.BK';
  const result = await fetchYahoo(symbol);
  if (!result) return false;

  const closes = result.indicators?.quote?.[0]?.close?.filter(v=>v!=null) || [];
  const vols   = result.indicators?.quote?.[0]?.volume?.filter(v=>v!=null) || [];
  if (closes.length < 30) return false;

  const price   = +closes[closes.length-1].toFixed(2);
  const prev    = closes[closes.length-2];
  const change  = +(price-prev).toFixed(2);
  const changePct = +((change/prev)*100).toFixed(2);
  const rsi     = calcRSI(closes);
  const {{macd,signal,hist}} = calcMACD(closes);
  const bb      = calcBB(closes);
  const avgVol  = vols.slice(-20).reduce((a,b)=>a+b,0)/20;
  const lastVol = vols[vols.length-1];
  const volRatio= +(lastVol/avgVol).toFixed(2);
  const mom10   = closes.length>10 ? +((price-closes[closes.length-11])/closes[closes.length-11]*100).toFixed(2) : 0;
  const ma20    = +(closes.slice(-20).reduce((a,b)=>a+b,0)/20).toFixed(2);
  const ma50    = +(closes.slice(-50).reduce((a,b)=>a+b,0)/50).toFixed(2);
  const spark   = closes.slice(-30);

  const sig = scoreSignals(price, rsi, hist, bb, volRatio, mom10, ma20, ma50);
  renderCustomCardHTML(ticker, price, change, changePct, rsi, hist, bb, volRatio, mom10, ma20, ma50, spark, sig);
  return true;
}}

function renderCustomCardHTML(ticker, price, change, changePct, rsi, macdHist, bb, volRatio, mom10, ma20, ma50, spark, sig) {{
  const changeColor = changePct>=0 ? '#10b981' : '#ef4444';
  const arrow = changePct>=0 ? '▲' : '▼';
  const rsiColor = rsi<30?'#22c55e':rsi>70?'#ef4444':'#3b82f6';
  const vcColors = {{
    'strong-buy': ['#052e16','#16a34a','#22c55e'],
    'buy':        ['#052e16','#15803d','#4ade80'],
    'hold':       ['#1c1917','#92400e','#fbbf24'],
    'sell':       ['#2d0000','#b91c1c','#f87171'],
    'strong-sell':['#2d0000','#991b1b','#ef4444'],
  }};
  const [vbg,vborder,vtext] = vcColors[sig.vc] || ['#1c1917','#6b7280','#d1d5db'];
  const badgeStyle = {{bullish:'background:#052e16;color:#4ade80;border:1px solid #16a34a',bearish:'background:#2d0000;color:#f87171;border:1px solid #b91c1c',neutral:'background:#1c1917;color:#d1d5db;border:1px solid #374151',alert:'background:#1c1400;color:#fbbf24;border:1px solid #92400e'}};
  const badges = sig.signals.map(s=>`<span class="signal-badge" style="${{badgeStyle[s.t]}}" title="${{s.d}}">${{s.l}}</span>`).join('');
  const W=120,H=40;
  const mn=Math.min(...spark), mx=Math.max(...spark), rng=mx-mn||1;
  const pts = spark.map((v,i)=>`${{(i*W/(spark.length-1)).toFixed(1)}},${{(H-((v-mn)/rng)*H).toFixed(1)}}`).join(' ');
  const spColor = spark[spark.length-1]>=spark[0]?'#10b981':'#ef4444';
  const buls = sig.signals.filter(s=>s.t==='bullish').length;
  const bers = sig.signals.filter(s=>s.t==='bearish').length;
  const trend = sig.score>0?'ขาขึ้น':sig.score<0?'ขาลง':'ทรงตัว';
  const summary = `<strong>${{ticker}} (เพิ่มเอง)</strong> ราคา ${{price.toFixed(2)}} บาท เปลี่ยนแปลง ${{changePct>=0?'บวก':'ลบ'}} ${{Math.abs(changePct).toFixed(2)}}% ภาพรวมสัญญาณ<strong>${{trend}}</strong> ${{buls}} สัญญาณบวก / ${{bers}} สัญญาณลบ RSI=${{rsi}} <strong>คำแนะนำ: ${{sig.verdict}}</strong>`;

  const html = `
  <div class="stock-card custom-stock-card" id="custom-card-${{ticker}}" data-verdict="${{sig.vc}}">
    <div class="card-header">
      <div class="ticker-info">
        <span class="ticker-symbol">${{ticker}}</span>
        <span class="sector-tag" style="background:#7c3aed20;color:#a78bfa;border:1px solid #7c3aed40">เพิ่มเอง</span>
        <button onclick="removeCustomStock('${{ticker}}')" style="margin-left:auto;background:none;border:none;color:#6b7280;cursor:pointer;font-size:0.8rem" title="ลบออก">✕ ลบ</button>
      </div>
      <span class="company-name">${{ticker}}.BK · Yahoo Finance live</span>
    </div>
    <div class="price-row">
      <div class="price-main">
        <span class="price-value">${{price.toFixed(2)}}</span>
        <span class="price-unit">฿</span>
      </div>
      <div class="price-change" style="color:${{changeColor}}">${{arrow}} ${{Math.abs(changePct).toFixed(2)}}% <span style="font-size:.75rem;opacity:.8">(${{change>=0?'+':''}}${{change.toFixed(2)}})</span></div>
    </div>
    <div class="sparkline-container">
      <svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}">
        <polyline points="${{pts}}" fill="none" stroke="${{spColor}}" stroke-width="1.5" stroke-linejoin="round"/>
      </svg>
    </div>
    <div class="indicators-grid">
      <div class="indicator"><span class="ind-label">RSI(14)</span><span class="ind-value" style="color:${{rsiColor}}">${{rsi}}</span><div class="rsi-bar"><div style="width:${{Math.min(rsi,100)}}%;background:${{rsiColor}}"></div></div></div>
      <div class="indicator"><span class="ind-label">MACD Hist</span><span class="ind-value" style="color:${{macdHist>0?'#22c55e':'#ef4444'}}">${{macdHist>=0?'+':''}}${{macdHist.toFixed(4)}}</span></div>
      <div class="indicator"><span class="ind-label">BB Upper</span><span class="ind-value">${{price.toFixed(2)}} / ${{bb.upper}}</span></div>
      <div class="indicator"><span class="ind-label">Vol Ratio</span><span class="ind-value" style="color:${{volRatio>1.5?'#fbbf24':'#9ca3af'}}">${{volRatio}}x</span></div>
      <div class="indicator"><span class="ind-label">MA20/50</span><span class="ind-value">${{ma20}} / ${{ma50}}</span></div>
      <div class="indicator"><span class="ind-label">Mom 10d</span><span class="ind-value" style="color:${{mom10>=0?'#22c55e':'#ef4444'}}">${{mom10>=0?'+':''}}${{mom10.toFixed(2)}}%</span></div>
    </div>
    <div class="signals-row">${{badges}}</div>
    <div class="verdict-box" style="background:${{vbg}};border:1px solid ${{vborder}};color:${{vtext}}">${{sig.verdict}} (score: ${{sig.score>=0?'+':''}}${{sig.score}})</div>
    <div class="ai-summary">${{summary}}</div>
  </div>`;

  const section = document.getElementById('customCardsSection');
  let grid = document.getElementById('customCardsGrid');
  if (!grid) {{
    section.innerHTML = '<div style="padding:0.5rem 2rem;color:#6b7280;font-size:0.8rem;border-top:1px solid #2a2a3a">หุ้นที่เพิ่มเอง (ดึงข้อมูล live จากเบราว์เซอร์)</div><div class="cards-grid" id="customCardsGrid"></div>';
    grid = document.getElementById('customCardsGrid');
  }}
  const existing = document.getElementById(`custom-card-${{ticker}}`);
  if (existing) existing.outerHTML = html;
  else grid.insertAdjacentHTML('beforeend', html);
}}

function removeCustomStock(ticker) {{
  const list = getCustomList().filter(t=>t!==ticker);
  saveCustomList(list);
  document.getElementById(`custom-card-${{ticker}}`)?.remove();
  const grid = document.getElementById('customCardsGrid');
  if (grid && !grid.children.length) {{
    document.getElementById('customCardsSection').innerHTML = '';
  }}
  renderCustomList();
}}

function renderCustomList() {{
  const list = getCustomList();
  document.getElementById('customCount').textContent = list.length ? `(${{list.length}})` : '';
  document.getElementById('customList').innerHTML = list.length
    ? list.map(t=>`<div class="clist-item"><span>${{t}}.BK</span><button onclick="removeCustomStock('${{t}}');renderCustomList()" class="clist-remove">ลบ</button></div>`).join('')
    : '<div style="color:#4b5563;font-size:0.8rem">ยังไม่มีหุ้นที่เพิ่ม</div>';
}}

// ── Load saved custom stocks on page load ─────────────────────
(async function() {{
  const list = getCustomList();
  for (const ticker of list) {{
    await fetchAndRenderCustomCard(ticker);
  }}
}})();
</script>
</body>
</html>"""
    return html

# ============================================================
# MAIN
# ============================================================

DEMO_PRICES = {
    "PTT":    {"price": 31.50,  "change": -0.25, "change_pct": -0.79, "rsi": 44.2,  "macd_line": -0.12, "macd_signal": -0.08, "macd_histogram": -0.04, "bb_upper": 34.10, "bb_mid": 31.80, "bb_lower": 29.50, "volume_ratio": 0.95, "momentum_10d": -2.30, "ma20": 31.80, "ma50": 33.20, "sparkline": [34,33.8,33.2,33.5,32.8,32.1,31.9,32.3,31.7,31.5,31.2,31.8,32.1,31.6,31.0,31.3,31.7,31.4,31.8,31.5,31.2,31.6,31.9,31.4,31.1,31.5,31.7,31.3,31.6,31.5]},
    "KBANK":  {"price": 142.50, "change": 1.50,  "change_pct": 1.06,  "rsi": 58.3,  "macd_line": 0.85,  "macd_signal": 0.62,  "macd_histogram": 0.23,  "bb_upper": 148.0, "bb_mid": 140.5, "bb_lower": 133.0, "volume_ratio": 1.35, "momentum_10d": 3.20,  "ma20": 140.5, "ma50": 137.8, "sparkline": [137,137.5,138,138.5,139,138.8,139.5,140,139.8,140.5,141,140.8,141.5,142,141.8,142.5,143,142.8,143.2,142.9,142.5,143,143.5,143.2,142.8,143.1,142.9,142.6,143.0,142.5]},
    "AOT":    {"price": 58.25,  "change": -0.50, "change_pct": -0.85, "rsi": 38.5,  "macd_line": -0.32, "macd_signal": -0.18, "macd_histogram": -0.14, "bb_upper": 62.50, "bb_mid": 59.20, "bb_lower": 55.90, "volume_ratio": 1.82, "momentum_10d": -4.10, "ma20": 59.20, "ma50": 61.50, "sparkline": [63,62.5,62,61.5,61,60.5,60,59.8,59.5,59.2,59,58.8,58.5,58.3,58.1,58.5,59,58.8,58.6,58.3,58.1,58.4,58.6,58.3,58.1,58.4,58.2,58.5,58.3,58.25]},
    "ADVANC": {"price": 219.00, "change": 2.00,  "change_pct": 0.92,  "rsi": 62.1,  "macd_line": 1.20,  "macd_signal": 0.95,  "macd_histogram": 0.25,  "bb_upper": 225.0, "bb_mid": 215.0, "bb_lower": 205.0, "volume_ratio": 1.15, "momentum_10d": 4.50,  "ma20": 215.0, "ma50": 210.5, "sparkline": [210,210.5,211,212,213,212.5,213.5,214,215,214.5,215.5,216,217,216.5,217.5,218,217.8,218.2,218.5,218.2,217.8,218.5,219,218.8,219.2,219.5,219.2,218.8,219.3,219.0]},
    "SCB":    {"price": 101.50, "change": 0.50,  "change_pct": 0.49,  "rsi": 51.8,  "macd_line": 0.15,  "macd_signal": 0.10,  "macd_histogram": 0.05,  "bb_upper": 105.0, "bb_mid": 101.0, "bb_lower": 97.00, "volume_ratio": 0.88, "momentum_10d": 1.10,  "ma20": 101.0, "ma50": 100.2, "sparkline": [100,100.2,100.5,101,100.8,101.2,101.5,101.3,101.8,102,101.8,102.2,102,101.8,102.1,101.9,102.2,101.8,102,101.5,101.2,101.8,102,101.7,101.5,101.8,102,101.7,101.5,101.5]},
    "CPALL":  {"price": 54.75,  "change": -0.25, "change_pct": -0.45, "rsi": 47.3,  "macd_line": -0.08, "macd_signal": -0.04, "macd_histogram": -0.04, "bb_upper": 57.50, "bb_mid": 54.80, "bb_lower": 52.10, "volume_ratio": 1.05, "momentum_10d": -1.20, "ma20": 54.80, "ma50": 55.30, "sparkline": [56,55.8,55.5,55.8,55.5,55.2,55,55.3,55.1,54.8,55,54.8,54.5,54.8,55,54.8,54.5,54.8,55,54.8,54.5,54.8,55,54.75,54.5,54.8,55,54.8,54.5,54.75]},
    "GULF":   {"price": 42.50,  "change": 1.25,  "change_pct": 3.03,  "rsi": 68.5,  "macd_line": 0.65,  "macd_signal": 0.42,  "macd_histogram": 0.23,  "bb_upper": 43.50, "bb_mid": 40.50, "bb_lower": 37.50, "volume_ratio": 3.25, "momentum_10d": 8.30,  "ma20": 40.50, "ma50": 39.20, "sparkline": [38.5,38.8,39,39.2,39.5,39.8,40,40.5,40.8,41,41.2,41.5,41.8,42,41.8,42.2,42.5,42.8,42.5,42.8,43,42.8,43.2,42.9,42.6,42.8,43,42.8,42.5,42.5]},
    "BDMS":   {"price": 24.10,  "change": 0.10,  "change_pct": 0.42,  "rsi": 53.2,  "macd_line": 0.05,  "macd_signal": 0.02,  "macd_histogram": 0.03,  "bb_upper": 25.20, "bb_mid": 23.90, "bb_lower": 22.60, "volume_ratio": 0.92, "momentum_10d": 2.10,  "ma20": 23.90, "ma50": 23.50, "sparkline": [23.5,23.6,23.7,23.8,23.9,24,23.9,24.1,24,24.2,24.1,24.3,24.2,24.4,24.3,24.2,24.4,24.3,24.1,24.2,24.3,24.1,24.2,24.3,24.1,24.2,24.1,24.2,24.1,24.1]},
    "TRUE":   {"price": 8.35,   "change": -0.15, "change_pct": -1.76, "rsi": 32.1,  "macd_line": -0.05, "macd_signal": -0.03, "macd_histogram": -0.02, "bb_upper": 9.20,  "bb_mid": 8.60,  "bb_lower": 8.00,  "volume_ratio": 2.10, "momentum_10d": -5.90, "ma20": 8.60,  "ma50": 9.10,  "sparkline": [9.2,9.1,9,8.9,8.8,8.7,8.6,8.5,8.7,8.6,8.5,8.4,8.6,8.5,8.4,8.5,8.6,8.5,8.4,8.3,8.5,8.4,8.3,8.5,8.4,8.3,8.5,8.4,8.35,8.35]},
    "BBL":    {"price": 155.00, "change": 1.00,  "change_pct": 0.65,  "rsi": 55.4,  "macd_line": 0.45,  "macd_signal": 0.30,  "macd_histogram": 0.15,  "bb_upper": 160.0, "bb_mid": 153.0, "bb_lower": 146.0, "volume_ratio": 1.10, "momentum_10d": 2.80,  "ma20": 153.0, "ma50": 150.5, "sparkline": [150,150.5,151,152,152.5,153,152.8,153.5,154,153.8,154.5,155,154.8,155.2,155.5,155.2,155.8,155.5,155.2,155.5,155.8,155.5,155.2,155.5,155.8,155.5,155.2,155.5,155.2,155.0]},
}


def make_demo_data(ticker: str) -> dict:
    p = DEMO_PRICES[ticker]
    return {
        "ticker": ticker,
        "price": p["price"],
        "change": p["change"],
        "change_pct": p["change_pct"],
        "rsi": p["rsi"],
        "macd_line": p["macd_line"],
        "macd_signal": p["macd_signal"],
        "macd_histogram": p["macd_histogram"],
        "bb_upper": p["bb_upper"],
        "bb_mid": p["bb_mid"],
        "bb_lower": p["bb_lower"],
        "volume_ratio": p["volume_ratio"],
        "momentum_10d": p["momentum_10d"],
        "ma20": p["ma20"],
        "ma50": p["ma50"],
        "sparkline": p["sparkline"],
    }


def main():
    print("SET Thailand Stock Analysis — Fetching data...")
    stocks = []
    use_demo = False

    for ticker, info in WATCHLIST.items():
        print(f"  Fetching {ticker}.BK ...")
        data = fetch_stock(ticker)
        if data is None:
            print(f"  [INFO] Using demo data for {ticker}")
            data = make_demo_data(ticker)
            use_demo = True
        sig = generate_signals(data)
        summary = ai_summary(ticker, info["name"], data, sig)
        stocks.append({
            "ticker": ticker,
            "info": info,
            "data": data,
            "sig": sig,
            "summary": summary,
            "is_demo": data == make_demo_data(ticker),
        })

    if use_demo:
        print("\n[INFO] Some data is demo/simulated — live data requires GitHub Actions with internet access.")

    # Sort by signal score descending
    stocks.sort(key=lambda s: s["sig"]["score"], reverse=True)

    print(f"\nBuilding HTML dashboard for {len(stocks)} stocks...")
    html = build_html(stocks)

    out_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done! → index.html updated")

    # Print summary table
    print("\n{'='*60}")
    print(f"{'Ticker':<10} {'Price':>8} {'Change':>8} {'RSI':>6} {'Score':>6} {'Verdict'}")
    print("-" * 60)
    for s in stocks:
        d = s["data"]
        g = s["sig"]
        print(f"{s['ticker']:<10} {d['price']:>8.2f} {d['change_pct']:>+7.2f}% {d['rsi']:>6.1f} {g['score']:>+6d}  {g['verdict']}")


if __name__ == "__main__":
    main()
