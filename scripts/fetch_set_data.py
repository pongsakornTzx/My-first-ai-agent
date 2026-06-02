#!/usr/bin/env python3
"""
SET Thailand Stock Analysis System
Data sources (priority order):
  1. Yahoo Finance (.BK) — อัปเดตอัตโนมัติ ไม่ต้องตั้งค่าอะไร
  2. Demo data           — fallback สุดท้าย (local dev / network blocked)
"""

import json
import os
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

# ============================================================
# WATCHLIST — read from config/watchlist.json
# ============================================================
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "watchlist.json")

_DEFAULT_WATCHLIST = {
    "PTT":    {"name": "ปตท",              "sector": "พลังงาน"},
}

def load_watchlist() -> dict:
    return _DEFAULT_WATCHLIST

if __name__ == "__main__":
    pass
