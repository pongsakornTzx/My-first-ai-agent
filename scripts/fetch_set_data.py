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
# WATCHLIST — SET Thailand tickers (Yahoo Finance format .BK)
# ============================================================
WATCHLIST = {
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
  @media(max-width:600px) {{
    .cards-grid {{ grid-template-columns: 1fr; padding: 1rem; }}
    .header {{ padding: 1rem; }}
    .overview-bar {{ padding: 0.75rem 1rem; }}
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
</div>

<main class="cards-grid" id="cardsGrid">
{cards_html}
</main>

<footer class="footer">
  อัปเดตล่าสุด: {updated} · ข้อมูลจาก Yahoo Finance (.BK) · อัปเดตอัตโนมัติทุก 30 นาที via GitHub Actions<br>
  <strong>คำเตือน:</strong> ข้อมูลนี้เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำการลงทุน กรุณาศึกษาข้อมูลเพิ่มเติมก่อนตัดสินใจ
</footer>

<script>
  // Filter cards by verdict
  const verdictMap = {{}};
  document.querySelectorAll('.stock-card').forEach(card => {{
    const vbox = card.querySelector('.verdict-box');
    if (vbox) {{
      const cls = [...vbox.classList].find(c => c !== 'verdict-box') || '';
      card.dataset.verdict = cls;
    }}
  }});

  // Read verdict from text content instead
  document.querySelectorAll('.stock-card').forEach(card => {{
    const id = card.id.replace('card-', '');
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
    document.querySelectorAll('.stock-card').forEach(card => {{
      if (filter === 'all' || card.dataset.verdict === filter) {{
        card.style.display = '';
      }} else {{
        card.style.display = 'none';
      }}
    }});
  }}
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
