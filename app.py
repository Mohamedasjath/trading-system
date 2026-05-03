import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
from datetime import datetime
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Pro Trade Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS DESIGN
# ============================================================
st.markdown("""
<style>
    .stApp {
        background: #05070d;
        color: #e5e7eb;
    }

    header[data-testid="stHeader"] {
        background: rgba(5, 7, 13, 0.85);
    }

    section[data-testid="stSidebar"] {
        background: #080d18;
        border-right: 1px solid rgba(148,163,184,0.18);
    }

    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }

    .app-hero {
        background: linear-gradient(135deg, rgba(14,165,233,0.18), rgba(34,197,94,0.10));
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 22px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 0 42px rgba(14,165,233,0.10);
        animation: softGlow 3s ease-in-out infinite alternate;
    }

    @keyframes softGlow {
        from { box-shadow: 0 0 25px rgba(14,165,233,0.10); }
        to { box-shadow: 0 0 50px rgba(34,197,94,0.16); }
    }

    .app-title {
        font-size: 34px;
        font-weight: 950;
        color: #ffffff;
        letter-spacing: -0.8px;
        margin-bottom: 2px;
    }

    .app-subtitle {
        color: #94a3b8;
        font-size: 14px;
    }

    .warning-box {
        background: rgba(250,204,21,0.08);
        border: 1px solid rgba(250,204,21,0.22);
        border-radius: 14px;
        padding: 10px 14px;
        color: #fde68a;
        font-size: 13px;
        margin-bottom: 14px;
    }

    .top-summary-card {
        background: rgba(11,18,32,0.88);
        border: 1px solid rgba(148,163,184,0.16);
        border-radius: 18px;
        padding: 14px 16px;
        min-height: 92px;
        box-shadow: 0 16px 35px rgba(0,0,0,0.30);
        transition: 0.25s ease;
        backdrop-filter: blur(8px);
    }

    .top-summary-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 0 28px rgba(56,189,248,0.18);
    }

    .metric-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 24px;
        font-weight: 900;
        color: #ffffff;
        line-height: 1.1;
    }

    .metric-small {
        color: #64748b;
        font-size: 12px;
        margin-top: 6px;
    }

    .buy-signal {
        background: linear-gradient(135deg, #00ff88, #22c55e, #16a34a);
        color: #001b0c;
        border-radius: 26px;
        padding: 24px;
        text-align: center;
        font-size: 38px;
        font-weight: 1000;
        box-shadow: 0 0 40px rgba(34,197,94,0.48);
        animation: pulseSignal 1.6s infinite, greenGlow 2.4s infinite alternate;
        margin: 12px 0 14px 0;
    }

    .sell-signal {
        background: linear-gradient(135deg, #ff1744, #ef4444, #991b1b);
        color: #ffffff;
        border-radius: 26px;
        padding: 24px;
        text-align: center;
        font-size: 38px;
        font-weight: 1000;
        box-shadow: 0 0 40px rgba(239,68,68,0.48);
        animation: pulseSignal 1.6s infinite, redGlow 2.4s infinite alternate;
        margin: 12px 0 14px 0;
    }

    .wait-signal {
        background: linear-gradient(135deg, #facc15, #f59e0b, #b45309);
        color: #1f1300;
        border-radius: 26px;
        padding: 24px;
        text-align: center;
        font-size: 38px;
        font-weight: 1000;
        box-shadow: 0 0 40px rgba(250,204,21,0.38);
        animation: pulseSignal 1.8s infinite, yellowGlow 2.5s infinite alternate;
        margin: 12px 0 14px 0;
    }

    @keyframes pulseSignal {
        0% { transform: scale(1); }
        50% { transform: scale(1.008); }
        100% { transform: scale(1); }
    }

    @keyframes greenGlow {
        from { box-shadow: 0 0 25px rgba(34,197,94,0.28); }
        to { box-shadow: 0 0 65px rgba(34,197,94,0.65); }
    }

    @keyframes redGlow {
        from { box-shadow: 0 0 25px rgba(239,68,68,0.28); }
        to { box-shadow: 0 0 65px rgba(239,68,68,0.65); }
    }

    @keyframes yellowGlow {
        from { box-shadow: 0 0 25px rgba(250,204,21,0.22); }
        to { box-shadow: 0 0 65px rgba(250,204,21,0.55); }
    }

    .tv-wrapper {
        background: #05070d;
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 25px 60px rgba(0,0,0,0.45);
        margin-top: 8px;
    }

    .tv-topbar {
        height: 46px;
        background: #080808;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 12px;
        color: #e5e7eb;
        font-size: 13px;
    }

    .tv-symbol {
        background: #111827;
        border: 1px solid rgba(255,255,255,0.12);
        padding: 7px 12px;
        border-radius: 10px;
        font-weight: 900;
        color: #ffffff;
    }

    .tv-price {
        color: #e5e7eb;
        font-weight: 800;
        padding: 0 8px;
    }

    .tv-pill {
        background: transparent;
        color: #cbd5e1;
        padding: 5px 8px;
        border-radius: 8px;
        font-weight: 700;
    }

    .tv-pill-active {
        background: #1d4ed8;
        color: white;
        padding: 5px 9px;
        border-radius: 8px;
        font-weight: 900;
    }

    .tv-left-tools {
        background: #090909;
        border-right: 1px solid rgba(255,255,255,0.08);
        min-height: 720px;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 12px;
        gap: 10px;
        border-radius: 0 0 0 18px;
    }

    .tv-tool {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: transparent;
        border: 1px solid transparent;
        color: #cbd5e1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }

    .tv-tool:hover {
        background: #111827;
        border: 1px solid rgba(255,255,255,0.12);
    }

    .right-panel {
        background: rgba(9,9,9,0.95);
        border-left: 1px solid rgba(255,255,255,0.08);
        min-height: 720px;
        padding: 12px;
        border-radius: 0 0 18px 0;
    }

    .panel-title {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        margin-top: 6px;
    }

    .watch-card {
        background: #111827;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 13px;
        padding: 10px 11px;
        margin-bottom: 9px;
    }

    .watch-label {
        color: #94a3b8;
        font-size: 12px;
        margin-bottom: 4px;
    }

    .watch-value {
        color: #ffffff;
        font-size: 17px;
        font-weight: 900;
    }

    .green { color: #22c55e !important; }
    .red { color: #ef4444 !important; }
    .yellow { color: #facc15 !important; }

    .bottom-bar {
        height: 34px;
        background: #080808;
        border-top: 1px solid rgba(255,255,255,0.08);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 14px;
        color: #94a3b8;
        font-size: 12px;
    }

    .method-card {
        background: rgba(11,18,32,0.90);
        border: 1px solid rgba(148,163,184,0.16);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 10px;
        backdrop-filter: blur(8px);
    }

    .reason-card {
        background: rgba(15,23,42,0.95);
        border-left: 4px solid #38bdf8;
        padding: 12px 14px;
        border-radius: 12px;
        margin-bottom: 9px;
        color: #dbeafe;
        font-size: 14px;
    }

    .news-positive {
        border-left: 4px solid #22c55e;
        background: rgba(34,197,94,0.08);
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 10px;
    }

    .news-negative {
        border-left: 4px solid #ef4444;
        background: rgba(239,68,68,0.08);
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 10px;
    }

    .news-neutral {
        border-left: 4px solid #facc15;
        background: rgba(250,204,21,0.08);
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 10px;
    }

    div.stButton > button {
        width: 100%;
        height: 48px;
        border-radius: 14px;
        border: 0;
        font-weight: 900;
        color: #020617;
        background: linear-gradient(90deg, #22c55e, #38bdf8);
    }

    div.stButton > button:hover {
        transform: scale(1.01);
        box-shadow: 0 0 30px rgba(56,189,248,0.35);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #0b1220;
        border-radius: 14px;
        padding: 10px 18px;
        color: #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# ANIMATED BACKGROUND
# ============================================================
def inject_animated_background(signal="WAIT"):
    if signal == "BUY":
        main_color = "#22c55e"
        soft_color = "rgba(34,197,94,0.18)"
        glow_color = "rgba(34,197,94,0.45)"
    elif signal == "SELL":
        main_color = "#ef4444"
        soft_color = "rgba(239,68,68,0.18)"
        glow_color = "rgba(239,68,68,0.45)"
    else:
        main_color = "#facc15"
        soft_color = "rgba(250,204,21,0.15)"
        glow_color = "rgba(250,204,21,0.35)"

    st.markdown(f"""
    <style>
        .stApp {{
            background:
                linear-gradient(120deg, rgba(5,7,13,0.96), rgba(5,7,13,0.92)),
                repeating-linear-gradient(90deg, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px, transparent 1px, transparent 80px),
                repeating-linear-gradient(0deg, rgba(255,255,255,0.022) 0px, rgba(255,255,255,0.022) 1px, transparent 1px, transparent 55px);
            overflow-x: hidden;
        }}

        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: -40%;
            width: 180%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.28;
            background:
                linear-gradient(115deg, transparent 0%, transparent 42%, {soft_color} 43%, transparent 45%),
                linear-gradient(125deg, transparent 0%, transparent 52%, {soft_color} 53%, transparent 55%),
                linear-gradient(135deg, transparent 0%, transparent 63%, {soft_color} 64%, transparent 66%);
            animation: marketFlow 12s linear infinite;
        }}

        .stApp::after {{
            content: "";
            position: fixed;
            width: 420px;
            height: 420px;
            right: -120px;
            top: 80px;
            background: radial-gradient(circle, {glow_color}, transparent 68%);
            filter: blur(18px);
            pointer-events: none;
            z-index: 0;
            animation: glowMove 6s ease-in-out infinite alternate;
        }}

        @keyframes marketFlow {{
            0% {{ transform: translateX(-8%) translateY(0px); }}
            50% {{ transform: translateX(4%) translateY(-18px); }}
            100% {{ transform: translateX(12%) translateY(0px); }}
        }}

        @keyframes glowMove {{
            0% {{ transform: scale(1) translateY(0px); opacity: 0.45; }}
            100% {{ transform: scale(1.18) translateY(50px); opacity: 0.85; }}
        }}

        .block-container {{
            position: relative;
            z-index: 2;
        }}

        .animated-market-strip {{
            width: 100%;
            height: 46px;
            border-radius: 18px;
            overflow: hidden;
            margin-bottom: 14px;
            background: rgba(15,23,42,0.72);
            border: 1px solid rgba(148,163,184,0.18);
            position: relative;
        }}

        .animated-market-strip::before {{
            content: "";
            position: absolute;
            left: -20%;
            top: 50%;
            width: 140%;
            height: 2px;
            background: linear-gradient(90deg, transparent, {main_color}, transparent);
            animation: signalLine 3.2s linear infinite;
            box-shadow: 0 0 18px {main_color};
        }}

        .animated-market-strip::after {{
            content: "▁ ▂ ▃ ▅ ▆ ▇ ▆ ▅ ▃ ▂ ▁  ▂ ▄ ▆ ▇ ▅ ▃ ▂ ▁  ▃ ▅ ▇ ▆ ▄ ▂";
            position: absolute;
            top: 9px;
            left: -50%;
            font-size: 22px;
            letter-spacing: 10px;
            white-space: nowrap;
            color: {main_color};
            opacity: 0.55;
            animation: candleMove 13s linear infinite;
        }}

        @keyframes signalLine {{
            0% {{ transform: translateX(-30%); }}
            100% {{ transform: translateX(100%); }}
        }}

        @keyframes candleMove {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(55%); }}
        }}

        .top-summary-card:hover {{
            border-color: {main_color};
            box-shadow: 0 0 28px {soft_color};
        }}
    </style>

    <div class="animated-market-strip"></div>
    """, unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="app-hero">
    <div class="app-title">⚡ Pro Trade Analyzer</div>
    <div class="app-subtitle">
        Crypto, Forex and Gold technical + news sentiment trading dashboard.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="warning-box">
⚠️ This tool gives rule-based analysis only. It cannot guarantee profit or 100% accurate predictions.
Always use stop loss and proper risk management.
</div>
""", unsafe_allow_html=True)


# ============================================================
# MARKETS
# ============================================================
TARGETS = {
    # Crypto
    "BTC-USD": {"symbols": ["BTC-USD"], "type": "crypto", "display": "BTC-USD"},
    "ETH-USD": {"symbols": ["ETH-USD"], "type": "crypto", "display": "ETH-USD"},
    "BNB-USD": {"symbols": ["BNB-USD"], "type": "crypto", "display": "BNB-USD"},
    "SOL-USD": {"symbols": ["SOL-USD"], "type": "crypto", "display": "SOL-USD"},
    "XRP-USD": {"symbols": ["XRP-USD"], "type": "crypto", "display": "XRP-USD"},
    "ADA-USD": {"symbols": ["ADA-USD"], "type": "crypto", "display": "ADA-USD"},
    "DOGE-USD": {"symbols": ["DOGE-USD"], "type": "crypto", "display": "DOGE-USD"},
    "AVAX-USD": {"symbols": ["AVAX-USD"], "type": "crypto", "display": "AVAX-USD"},
    "LINK-USD": {"symbols": ["LINK-USD"], "type": "crypto", "display": "LINK-USD"},
    "LTC-USD": {"symbols": ["LTC-USD"], "type": "crypto", "display": "LTC-USD"},

    # Gold
    "XAUUSD / GOLD": {"symbols": ["XAUUSD=X", "GC=F"], "type": "gold", "display": "XAUUSD"},

    # Forex majors and crosses
    "EURUSD": {"symbols": ["EURUSD=X"], "type": "forex", "display": "EURUSD"},
    "GBPUSD": {"symbols": ["GBPUSD=X"], "type": "forex", "display": "GBPUSD"},
    "USDJPY": {"symbols": ["USDJPY=X"], "type": "forex_jpy", "display": "USDJPY"},
    "USDCHF": {"symbols": ["USDCHF=X"], "type": "forex", "display": "USDCHF"},
    "USDCAD": {"symbols": ["USDCAD=X"], "type": "forex", "display": "USDCAD"},
    "AUDUSD": {"symbols": ["AUDUSD=X"], "type": "forex", "display": "AUDUSD"},
    "NZDUSD": {"symbols": ["NZDUSD=X"], "type": "forex", "display": "NZDUSD"},
    "EURJPY": {"symbols": ["EURJPY=X"], "type": "forex_jpy", "display": "EURJPY"},
    "GBPJPY": {"symbols": ["GBPJPY=X"], "type": "forex_jpy", "display": "GBPJPY"},
    "AUDJPY": {"symbols": ["AUDJPY=X"], "type": "forex_jpy", "display": "AUDJPY"},
    "CADJPY": {"symbols": ["CADJPY=X"], "type": "forex_jpy", "display": "CADJPY"},
    "CHFJPY": {"symbols": ["CHFJPY=X"], "type": "forex_jpy", "display": "CHFJPY"},
    "EURGBP": {"symbols": ["EURGBP=X"], "type": "forex", "display": "EURGBP"},
    "EURAUD": {"symbols": ["EURAUD=X"], "type": "forex", "display": "EURAUD"},
    "EURCAD": {"symbols": ["EURCAD=X"], "type": "forex", "display": "EURCAD"},
    "EURCHF": {"symbols": ["EURCHF=X"], "type": "forex", "display": "EURCHF"},
    "GBPAUD": {"symbols": ["GBPAUD=X"], "type": "forex", "display": "GBPAUD"},
    "GBPCAD": {"symbols": ["GBPCAD=X"], "type": "forex", "display": "GBPCAD"},
    "GBPCHF": {"symbols": ["GBPCHF=X"], "type": "forex", "display": "GBPCHF"},
    "AUDCAD": {"symbols": ["AUDCAD=X"], "type": "forex", "display": "AUDCAD"},
    "AUDCHF": {"symbols": ["AUDCHF=X"], "type": "forex", "display": "AUDCHF"},
    "NZDJPY": {"symbols": ["NZDJPY=X"], "type": "forex_jpy", "display": "NZDJPY"},
    "NZDCAD": {"symbols": ["NZDCAD=X"], "type": "forex", "display": "NZDCAD"},
}


# ============================================================
# SIDEBAR SETTINGS
# ============================================================
st.sidebar.markdown("## ⚙️ Settings")

selected_market = st.sidebar.selectbox("Target Market", list(TARGETS.keys()))

timeframe = st.sidebar.selectbox(
    "Timeframe",
    ["5m", "15m", "30m", "1h", "4h", "1d"],
    index=3
)

period_map = {
    "5m": "5d",
    "15m": "1mo",
    "30m": "1mo",
    "1h": "3mo",
    "4h": "6mo",
    "1d": "1y"
}
period = period_map[timeframe]

account_balance = st.sidebar.number_input(
    "Account Balance $",
    min_value=10.0,
    max_value=1000000.0,
    value=1000.0,
    step=50.0
)

risk_percent = st.sidebar.slider(
    "Risk per trade %",
    min_value=0.5,
    max_value=50.0,
    value=1.0,
    step=0.5
)

max_leverage = st.sidebar.selectbox(
    "Broker Leverage",
    [10, 20, 30, 50, 100, 200, 500, 1000],
    index=3
)

methodology_text = st.sidebar.text_area(
    "Trading Methodology Feed",
    value=(
        "Follow trend with EMA 20/50/200. Confirm momentum with RSI and MACD. "
        "Avoid trades near strong resistance unless breakout confirms. "
        "Use ATR for stop loss and take profit. "
        "If news is strongly against the signal, wait."
    ),
    height=140
)

risk_dollar = account_balance * (risk_percent / 100)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💵 Risk Summary")
st.sidebar.write(f"Account Balance: **${account_balance:,.2f}**")
st.sidebar.write(f"Risk Amount: **${risk_dollar:,.2f}**")
st.sidebar.write(f"Broker Leverage: **1:{max_leverage}**")

st.sidebar.markdown("---")
st.sidebar.markdown("### Strategy Rules")
st.sidebar.markdown("""
- EMA 20 / 50 / 200 trend
- RSI momentum
- MACD confirmation
- Bollinger band position
- ATR volatility
- Support & resistance
- Market news sentiment
- Risk $ + lot size + leverage check
""")

analyze = st.sidebar.button("🚀 Analyze Now")


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def safe_number(value, decimals=4):
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.{decimals}f}"
    except Exception:
        return "N/A"


def download_market_data(symbol_list, period_value, interval_value):
    last_error = None

    for symbol in symbol_list:
        try:
            data = yf.download(
                symbol,
                period=period_value,
                interval=interval_value,
                progress=False,
                auto_adjust=False
            )

            if data is not None and not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)

                data = data.dropna()

                if len(data) > 220:
                    return symbol, data

        except Exception as e:
            last_error = e

    raise Exception(f"Market data not available. Last error: {last_error}")


def add_indicators(data):
    data = data.copy()

    data["EMA_20"] = EMAIndicator(close=data["Close"], window=20).ema_indicator()
    data["EMA_50"] = EMAIndicator(close=data["Close"], window=50).ema_indicator()
    data["EMA_200"] = EMAIndicator(close=data["Close"], window=200).ema_indicator()

    data["RSI"] = RSIIndicator(close=data["Close"], window=14).rsi()

    macd = MACD(close=data["Close"])
    data["MACD"] = macd.macd()
    data["MACD_SIGNAL"] = macd.macd_signal()
    data["MACD_HIST"] = macd.macd_diff()

    bb = BollingerBands(close=data["Close"], window=20, window_dev=2)
    data["BB_HIGH"] = bb.bollinger_hband()
    data["BB_LOW"] = bb.bollinger_lband()
    data["BB_MID"] = bb.bollinger_mavg()

    atr = AverageTrueRange(
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        window=14
    )
    data["ATR"] = atr.average_true_range()

    data = data.dropna()
    return data


def fetch_news(market_name):
    if "USD" in market_name and "-" in market_name:
        base = market_name.replace("-USD", "")
        queries = [
            f"{base} crypto price market news today",
            f"{base} crypto technical analysis",
            "crypto market Federal Reserve interest rates",
            "Bitcoin Ethereum crypto market sentiment"
        ]
    elif market_name == "XAUUSD / GOLD":
        queries = [
            "gold price XAUUSD market today",
            "gold price US dollar yields Federal Reserve",
            "XAUUSD technical analysis market news",
            "gold inflation safe haven geopolitical news",
            "gold price interest rates market"
        ]
    else:
        queries = [
            f"{market_name} forex market news today",
            f"{market_name} technical analysis forex",
            "US dollar Federal Reserve forex market",
            "forex market interest rates inflation news"
        ]

    all_news = []

    for query in queries:
        url = (
            "https://news.google.com/rss/search?q="
            + query.replace(" ", "%20")
            + "&hl=en-US&gl=US&ceid=US:en"
        )

        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", "")

            if title:
                all_news.append({
                    "title": title,
                    "link": link,
                    "published": published
                })

    unique_news = []
    seen_titles = set()

    for item in all_news:
        key = item["title"].lower().strip()

        if key not in seen_titles:
            seen_titles.add(key)
            unique_news.append(item)

    return unique_news[:25]


def analyze_news_sentiment(news_items, market_name):
    common_bullish = [
        "rally", "surge", "bullish", "breakout", "record high",
        "rate cut", "risk-on", "rebound", "gains", "soars",
        "jumps", "strong demand", "optimism", "weaker dollar",
        "inflation", "safe haven", "demand"
    ]

    common_bearish = [
        "crash", "drop", "selloff", "bearish", "rate hike",
        "risk-off", "falls", "plunge", "decline", "weakness",
        "fear", "strong dollar", "hawkish", "pressure",
        "liquidation", "outflows", "lawsuit"
    ]

    if "USD" in market_name and "-" in market_name:
        bullish_words = common_bullish + ["etf inflows", "institutional", "adoption", "accumulation"]
        bearish_words = common_bearish + ["regulation", "hack", "fraud", "ban"]
    elif market_name == "XAUUSD / GOLD":
        bullish_words = common_bullish + [
            "geopolitical", "central bank buying", "gold rises",
            "recession", "uncertainty", "war", "crisis", "yields fall"
        ]
        bearish_words = common_bearish + [
            "dollar strong", "yields rise", "gold falls", "inflation cools",
            "strong jobs", "profit taking"
        ]
    else:
        bullish_words = common_bullish + ["currency gains", "forex gains", "economic strength", "positive data"]
        bearish_words = common_bearish + ["currency falls", "forex losses", "economic slowdown", "negative data"]

    total_score = 0
    analyzed_news = []

    for item in news_items:
        title_lower = item["title"].lower()
        item_score = 0

        for word in bullish_words:
            if word in title_lower:
                item_score += 1

        for word in bearish_words:
            if word in title_lower:
                item_score -= 1

        total_score += item_score

        if item_score > 0:
            sentiment = "positive"
        elif item_score < 0:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        analyzed_news.append({
            **item,
            "score": item_score,
            "sentiment": sentiment
        })

    return total_score, analyzed_news


def methodology_score(methodology_text_value):
    text = methodology_text_value.lower()
    score = 0
    notes = []

    if "trend" in text or "ema" in text:
        notes.append("Methodology includes trend/EMA confirmation.")
    if "rsi" in text:
        notes.append("Methodology includes RSI momentum confirmation.")
    if "macd" in text:
        notes.append("Methodology includes MACD confirmation.")
    if "news" in text:
        notes.append("Methodology includes news confirmation.")
    if "risk" in text or "stop loss" in text or "sl" in text:
        notes.append("Methodology includes risk/stop-loss control.")
    if "wait" in text:
        notes.append("Methodology includes WAIT rule when confirmation is weak.")

    if "only buy" in text:
        score += 5
        notes.append("Custom bias: only buy wording detected.")
    if "only sell" in text:
        score -= 5
        notes.append("Custom bias: only sell wording detected.")

    return score, notes


def technical_engine(data):
    latest = data.iloc[-1]
    previous = data.iloc[-2]

    close = latest["Close"]
    score = 0
    reasons = []

    if latest["EMA_20"] > latest["EMA_50"] > latest["EMA_200"] and close > latest["EMA_20"]:
        score += 30
        reasons.append("Strong bullish trend: EMA20 > EMA50 > EMA200 and price is above EMA20.")
    elif latest["EMA_20"] < latest["EMA_50"] < latest["EMA_200"] and close < latest["EMA_20"]:
        score -= 30
        reasons.append("Strong bearish trend: EMA20 < EMA50 < EMA200 and price is below EMA20.")
    elif close > latest["EMA_200"]:
        score += 10
        reasons.append("Price is above EMA200, so long-term bias is bullish.")
    elif close < latest["EMA_200"]:
        score -= 10
        reasons.append("Price is below EMA200, so long-term bias is bearish.")

    if 50 < latest["RSI"] < 70:
        score += 15
        reasons.append("RSI is bullish but not overbought.")
    elif 30 < latest["RSI"] < 50:
        score -= 15
        reasons.append("RSI is bearish but not oversold.")
    elif latest["RSI"] >= 70:
        score -= 10
        reasons.append("RSI is overbought. Pullback risk is high.")
    elif latest["RSI"] <= 30:
        score += 10
        reasons.append("RSI is oversold. Bounce/reversal possibility is present.")

    if latest["MACD"] > latest["MACD_SIGNAL"] and latest["MACD_HIST"] > previous["MACD_HIST"]:
        score += 20
        reasons.append("MACD is bullish and histogram is increasing.")
    elif latest["MACD"] < latest["MACD_SIGNAL"] and latest["MACD_HIST"] < previous["MACD_HIST"]:
        score -= 20
        reasons.append("MACD is bearish and histogram is decreasing.")
    else:
        reasons.append("MACD is mixed. Momentum confirmation is not strong.")

    if close > latest["BB_MID"] and close < latest["BB_HIGH"]:
        score += 10
        reasons.append("Price is above Bollinger middle band. Buyers have control.")
    elif close < latest["BB_MID"] and close > latest["BB_LOW"]:
        score -= 10
        reasons.append("Price is below Bollinger middle band. Sellers have control.")
    elif close >= latest["BB_HIGH"]:
        score -= 5
        reasons.append("Price is near upper Bollinger band. Overextension risk.")
    elif close <= latest["BB_LOW"]:
        score += 5
        reasons.append("Price is near lower Bollinger band. Bounce zone possible.")

    resistance = data["High"].tail(60).max()
    support = data["Low"].tail(60).min()

    distance_to_resistance = abs(resistance - close) / close
    distance_to_support = abs(close - support) / close

    if distance_to_resistance < 0.005:
        score -= 8
        reasons.append("Price is close to resistance. Breakout confirmation is needed.")
    if distance_to_support < 0.005:
        score += 8
        reasons.append("Price is close to support. Reversal/bounce possibility is higher.")

    return score, reasons, resistance, support


def final_decision(technical_score, raw_news_score, custom_method_score):
    news_score = max(min(raw_news_score * 3, 20), -20)
    method_score = max(min(custom_method_score, 10), -10)
    total_score = technical_score + news_score + method_score

    if total_score >= 45:
        signal = "BUY"
        confidence = min(95, 55 + total_score)
    elif total_score <= -45:
        signal = "SELL"
        confidence = min(95, 55 + abs(total_score))
    else:
        signal = "WAIT"
        confidence = 50 + min(abs(total_score), 15)

    return signal, confidence, total_score, news_score, method_score


def calculate_trade_levels(data, signal):
    latest = data.iloc[-1]
    close = latest["Close"]
    atr = latest["ATR"]

    if signal == "BUY":
        entry = close
        stop_loss = close - (atr * 1.5)
        tp1 = close + (atr * 2.0)
        tp2 = close + (atr * 3.0)
    elif signal == "SELL":
        entry = close
        stop_loss = close + (atr * 1.5)
        tp1 = close - (atr * 2.0)
        tp2 = close - (atr * 3.0)
    else:
        entry = close
        stop_loss = None
        tp1 = None
        tp2 = None

    return entry, stop_loss, tp1, tp2


def calculate_position_sizing(market_type, entry, stop_loss, tp1, tp2, account_balance, risk_percent, max_leverage):
    risk_dollar = account_balance * (risk_percent / 100)

    if stop_loss is None or tp1 is None:
        return {
            "risk_dollar": risk_dollar,
            "stop_distance": None,
            "position_units": None,
            "lot_size": None,
            "estimated_loss": None,
            "estimated_profit_tp1": None,
            "estimated_profit_tp2": None,
            "position_value": None,
            "required_margin": None,
            "leverage_needed": None,
            "leverage_status": "N/A"
        }

    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        stop_distance = 0.00001

    position_units = risk_dollar / stop_distance

    if market_type in ["forex", "forex_jpy"]:
        lot_size = position_units / 100000
    elif market_type == "gold":
        lot_size = position_units / 100
    else:
        lot_size = position_units

    estimated_loss = risk_dollar
    estimated_profit_tp1 = abs(tp1 - entry) * position_units
    estimated_profit_tp2 = abs(tp2 - entry) * position_units if tp2 is not None else None

    position_value = position_units * entry
    required_margin = position_value / max_leverage

    leverage_needed = position_value / account_balance if account_balance > 0 else None

    if leverage_needed is not None and leverage_needed <= max_leverage:
        leverage_status = "OK"
    else:
        leverage_status = "Too High"

    return {
        "risk_dollar": risk_dollar,
        "stop_distance": stop_distance,
        "position_units": position_units,
        "lot_size": lot_size,
        "estimated_loss": estimated_loss,
        "estimated_profit_tp1": estimated_profit_tp1,
        "estimated_profit_tp2": estimated_profit_tp2,
        "position_value": position_value,
        "required_margin": required_margin,
        "leverage_needed": leverage_needed,
        "leverage_status": leverage_status
    }


def signal_class(signal):
    if signal == "BUY":
        return "green"
    if signal == "SELL":
        return "red"
    return "yellow"


def render_top_card(label, value, small_text=""):
    st.markdown(f"""
    <div class="top-summary-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-small">{small_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_chart(data, actual_symbol, selected_market, timeframe, latest, signal, entry, stop_loss, tp1, resistance, support, confidence, total_score):
    st.markdown(f"""
    <div class="tv-wrapper">
        <div class="tv-topbar">
            <div class="tv-symbol">{actual_symbol}</div>
            <div class="tv-price">O {safe_number(latest["Open"])} &nbsp; H {safe_number(latest["High"])} &nbsp; L {safe_number(latest["Low"])} &nbsp; C {safe_number(latest["Close"])}</div>
            <div class="{signal_class(signal)}">{signal}</div>
            <div class="tv-pill">5m</div>
            <div class="tv-pill">15m</div>
            <div class="tv-pill">30m</div>
            <div class="tv-pill-active">{timeframe}</div>
            <div class="tv-pill">Indicators</div>
            <div class="tv-pill">Alert</div>
            <div style="margin-left:auto;" class="tv-pill">Pro Trade Analyzer</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left_tools, chart_col, right_panel = st.columns([0.45, 8.7, 1.55], gap="small")

    with left_tools:
        st.markdown("""
        <div class="tv-left-tools">
            <div class="tv-tool">＋</div>
            <div class="tv-tool">⌖</div>
            <div class="tv-tool">╱</div>
            <div class="tv-tool">━</div>
            <div class="tv-tool">▭</div>
            <div class="tv-tool">✎</div>
            <div class="tv-tool">T</div>
            <div class="tv-tool">⌁</div>
            <div class="tv-tool">📏</div>
            <div class="tv-tool">🔍</div>
            <div class="tv-tool">⚙</div>
        </div>
        """, unsafe_allow_html=True)

    with chart_col:
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Candles",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
            increasing_fillcolor="#22c55e",
            decreasing_fillcolor="#ef4444"
        ))

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["EMA_20"],
            mode="lines",
            name="EMA 20",
            line=dict(color="#38bdf8", width=1.2)
        ))

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["EMA_50"],
            mode="lines",
            name="EMA 50",
            line=dict(color="#facc15", width=1.2)
        ))

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["EMA_200"],
            mode="lines",
            name="EMA 200",
            line=dict(color="#a855f7", width=1.8)
        ))

        fig.add_hline(
            y=resistance,
            line_dash="dot",
            line_color="#ef4444",
            annotation_text="Resistance",
            annotation_position="top right"
        )

        fig.add_hline(
            y=support,
            line_dash="dot",
            line_color="#22c55e",
            annotation_text="Support",
            annotation_position="bottom right"
        )

        if signal == "BUY" and stop_loss is not None and tp1 is not None:
            fig.add_hrect(
                y0=entry,
                y1=tp1,
                fillcolor="rgba(34,197,94,0.12)",
                line_width=0,
                annotation_text="Profit Zone",
                annotation_position="top left"
            )
            fig.add_hrect(
                y0=stop_loss,
                y1=entry,
                fillcolor="rgba(239,68,68,0.12)",
                line_width=0,
                annotation_text="Risk Zone",
                annotation_position="bottom left"
            )
        elif signal == "SELL" and stop_loss is not None and tp1 is not None:
            fig.add_hrect(
                y0=tp1,
                y1=entry,
                fillcolor="rgba(34,197,94,0.12)",
                line_width=0,
                annotation_text="Profit Zone",
                annotation_position="bottom left"
            )
            fig.add_hrect(
                y0=entry,
                y1=stop_loss,
                fillcolor="rgba(239,68,68,0.12)",
                line_width=0,
                annotation_text="Risk Zone",
                annotation_position="top left"
            )

        fig.update_layout(
            template="plotly_dark",
            height=720,
            paper_bgcolor="#05070d",
            plot_bgcolor="#05070d",
            margin=dict(l=0, r=5, t=10, b=0),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            dragmode="pan",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)"
            ),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False, side="right")
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "scrollZoom": True,
                "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "eraseshape"]
            }
        )

    with right_panel:
        st.markdown(f"""
        <div class="right-panel">
            <div class="panel-title">Watchlist</div>

            <div class="watch-card">
                <div class="watch-label">{selected_market}</div>
                <div class="watch-value">{safe_number(latest["Close"])}</div>
                <div class="{signal_class(signal)}">{signal}</div>
            </div>

            <div class="panel-title">Trade Levels</div>

            <div class="watch-card">
                <div class="watch-label">Entry</div>
                <div class="watch-value">{safe_number(entry)}</div>
            </div>

            <div class="watch-card">
                <div class="watch-label">Stop Loss</div>
                <div class="watch-value red">{safe_number(stop_loss)}</div>
            </div>

            <div class="watch-card">
                <div class="watch-label">Take Profit 1</div>
                <div class="watch-value green">{safe_number(tp1)}</div>
            </div>

            <div class="watch-card">
                <div class="watch-label">Resistance</div>
                <div class="watch-value red">{safe_number(resistance)}</div>
            </div>

            <div class="watch-card">
                <div class="watch-label">Support</div>
                <div class="watch-value green">{safe_number(support)}</div>
            </div>

            <div class="panel-title">Score</div>

            <div class="watch-card">
                <div class="watch-label">Confidence</div>
                <div class="watch-value">{safe_number(confidence, 0)}%</div>
            </div>

            <div class="watch-card">
                <div class="watch-label">Total Score</div>
                <div class="watch-value">{safe_number(total_score, 0)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="bottom-bar">
        <div>{selected_market} • {timeframe} • EMA + RSI + MACD + ATR + News + Risk Engine</div>
        <div>Last analyzed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN APP
# ============================================================
if analyze:
    try:
        with st.spinner("Loading market data, calculating methodology, scanning news, and calculating risk..."):
            actual_symbol, data = download_market_data(
                TARGETS[selected_market]["symbols"],
                period,
                timeframe
            )

            data = add_indicators(data)

            news_items = fetch_news(selected_market)
            raw_news_score, analyzed_news = analyze_news_sentiment(news_items, selected_market)

            tech_score, tech_reasons, resistance, support = technical_engine(data)

            custom_method_score, method_notes = methodology_score(methodology_text)

            signal, confidence, total_score, news_score, method_score = final_decision(
                tech_score,
                raw_news_score,
                custom_method_score
            )

            entry, stop_loss, tp1, tp2 = calculate_trade_levels(data, signal)

            market_type = TARGETS[selected_market]["type"]

            position_info = calculate_position_sizing(
                market_type=market_type,
                entry=entry,
                stop_loss=stop_loss,
                tp1=tp1,
                tp2=tp2,
                account_balance=account_balance,
                risk_percent=risk_percent,
                max_leverage=max_leverage
            )

            latest = data.iloc[-1]

        inject_animated_background(signal)

        top1, top2, top3, top4, top5 = st.columns(5)

        with top1:
            render_top_card("Market", TARGETS[selected_market]["display"], f"Yahoo: {actual_symbol}")

        with top2:
            render_top_card("Price", safe_number(latest["Close"]), f"Timeframe: {timeframe}")

        with top3:
            render_top_card("Signal", signal, "BUY / SELL / WAIT")

        with top4:
            render_top_card("Confidence", f"{safe_number(confidence, 0)}%", "Rule-based score")

        with top5:
            render_top_card("Risk $", f"${position_info['risk_dollar']:,.2f}", f"{risk_percent}% of balance")

        if signal == "BUY":
            st.markdown('<div class="buy-signal">BUY SETUP DETECTED</div>', unsafe_allow_html=True)
        elif signal == "SELL":
            st.markdown('<div class="sell-signal">SELL SETUP DETECTED</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="wait-signal">WAIT — NO CLEAN SETUP</div>', unsafe_allow_html=True)

        tab_chart, tab_plan, tab_rules, tab_news = st.tabs([
            "📈 Trading Chart",
            "🎯 Trade Plan",
            "🧠 Methodology",
            "📰 News Scan"
        ])

        with tab_chart:
            render_chart(
                data=data,
                actual_symbol=actual_symbol,
                selected_market=selected_market,
                timeframe=timeframe,
                latest=latest,
                signal=signal,
                entry=entry,
                stop_loss=stop_loss,
                tp1=tp1,
                resistance=resistance,
                support=support,
                confidence=confidence,
                total_score=total_score
            )

        with tab_plan:
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                render_top_card("Entry", safe_number(entry), "Current market reference")

            with c2:
                render_top_card("Stop Loss", safe_number(stop_loss), "ATR based risk")

            with c3:
                render_top_card("Take Profit 1", safe_number(tp1), "ATR x 2 target")

            with c4:
                render_top_card("Take Profit 2", safe_number(tp2), "ATR x 3 target")

            st.markdown("### 💵 Money, Lot & Leverage Calculation")

            m1, m2, m3, m4 = st.columns(4)

            with m1:
                render_top_card(
                    "Risk Amount",
                    f"${position_info['risk_dollar']:,.2f}",
                    f"{risk_percent}% of ${account_balance:,.2f}"
                )

            with m2:
                render_top_card(
                    "Suggested Lot",
                    safe_number(position_info["lot_size"], 3),
                    "Based on SL distance"
                )

            with m3:
                render_top_card(
                    "Profit at TP1",
                    "N/A" if position_info["estimated_profit_tp1"] is None else f"${position_info['estimated_profit_tp1']:,.2f}",
                    "If TP1 hit"
                )

            with m4:
                render_top_card(
                    "Loss at SL",
                    "N/A" if position_info["estimated_loss"] is None else f"${position_info['estimated_loss']:,.2f}",
                    "If SL hit"
                )

            l1, l2, l3, l4 = st.columns(4)

            with l1:
                render_top_card(
                    "Profit at TP2",
                    "N/A" if position_info["estimated_profit_tp2"] is None else f"${position_info['estimated_profit_tp2']:,.2f}",
                    "If TP2 hit"
                )

            with l2:
                render_top_card(
                    "Required Margin",
                    "N/A" if position_info["required_margin"] is None else f"${position_info['required_margin']:,.2f}",
                    f"Using 1:{max_leverage}"
                )

            with l3:
                render_top_card(
                    "Leverage Needed",
                    "N/A" if position_info["leverage_needed"] is None else f"1:{position_info['leverage_needed']:.1f}",
                    "Based on balance"
                )

            with l4:
                render_top_card(
                    "Leverage Status",
                    position_info["leverage_status"],
                    "OK / Too High"
                )

            st.markdown(f"""
            <div class="method-card">
                <h3>Risk Management Rule</h3>
                <p>Account Balance: <b>${account_balance:,.2f}</b></p>
                <p>Risk Per Trade: <b>{risk_percent}%</b> = <b>${position_info['risk_dollar']:,.2f}</b></p>
                <p>Broker Leverage Selected: <b>1:{max_leverage}</b></p>
                <p>Suggested lot size is calculated using stop loss distance and dollar risk.</p>
                <p>Profit and loss are estimates only. They are not guaranteed.</p>
                <p>If leverage status shows <b>Too High</b>, reduce risk %, reduce lot size, or increase account balance.</p>
            </div>
            """, unsafe_allow_html=True)

        with tab_rules:
            r1, r2, r3, r4, r5 = st.columns(5)

            with r1:
                render_top_card("Technical Score", safe_number(tech_score, 0), "EMA + RSI + MACD + BB")

            with r2:
                render_top_card("News Score", safe_number(news_score, 0), "Capped news effect")

            with r3:
                render_top_card("Method Score", safe_number(method_score, 0), "From methodology feed")

            with r4:
                render_top_card("RSI", safe_number(latest["RSI"], 2), "Momentum")

            with r5:
                render_top_card("ATR", safe_number(latest["ATR"]), "Volatility")

            st.markdown("### Technical Rule Results")
            for reason in tech_reasons:
                st.markdown(f'<div class="reason-card">⚡ {reason}</div>', unsafe_allow_html=True)

            st.markdown("### Methodology Feed Notes")
            if method_notes:
                for note in method_notes:
                    st.markdown(f'<div class="reason-card">📌 {note}</div>', unsafe_allow_html=True)
            else:
                st.info("No methodology keywords detected.")

            st.markdown("### Indicator Values")

            indicator_df = pd.DataFrame({
                "Indicator": [
                    "EMA 20", "EMA 50", "EMA 200", "RSI", "MACD",
                    "MACD Signal", "MACD Histogram", "Bollinger High",
                    "Bollinger Mid", "Bollinger Low", "ATR"
                ],
                "Value": [
                    latest["EMA_20"], latest["EMA_50"], latest["EMA_200"],
                    latest["RSI"], latest["MACD"], latest["MACD_SIGNAL"],
                    latest["MACD_HIST"], latest["BB_HIGH"], latest["BB_MID"],
                    latest["BB_LOW"], latest["ATR"]
                ]
            })

            st.dataframe(indicator_df, use_container_width=True)

        with tab_news:
            st.markdown("### Live News Sentiment Scan")
            st.write(f"Raw news score: **{raw_news_score}**")
            st.write(f"Capped news score used in final decision: **{news_score}**")

            if not analyzed_news:
                st.info("News feed unavailable or empty.")
            else:
                positive_count = sum(1 for n in analyzed_news if n["sentiment"] == "positive")
                negative_count = sum(1 for n in analyzed_news if n["sentiment"] == "negative")
                neutral_count = sum(1 for n in analyzed_news if n["sentiment"] == "neutral")

                n1, n2, n3 = st.columns(3)

                with n1:
                    render_top_card("Positive News", positive_count, "Bullish headlines")

                with n2:
                    render_top_card("Negative News", negative_count, "Bearish headlines")

                with n3:
                    render_top_card("Neutral News", neutral_count, "No strong keyword")

                with st.expander("View all scanned news"):
                    for news in analyzed_news:
                        css_class = "news-neutral"
                        icon = "⚪"

                        if news["sentiment"] == "positive":
                            css_class = "news-positive"
                            icon = "🟢"
                        elif news["sentiment"] == "negative":
                            css_class = "news-negative"
                            icon = "🔴"

                        st.markdown(f"""
                        <div class="{css_class}">
                            <b>{icon} {news["title"]}</b><br>
                            <small>{news["published"]}</small><br>
                            <small>Sentiment score: {news["score"]}</small>
                        </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        inject_animated_background("WAIT")
        st.error("Error occurred.")
        st.write(e)

else:
    inject_animated_background("WAIT")

    st.markdown("""
    <div class="method-card">
        <h2>🚀 Ready to Analyze</h2>
        <p>Left side settings la market select pannunga.</p>
        <p>Markets: <b>Crypto</b>, <b>Forex</b>, and <b>XAUUSD / GOLD</b>.</p>
        <p>Account balance, risk %, leverage, methodology feed set pannitu <b>Analyze Now</b> click pannunga.</p>
    </div>
    """, unsafe_allow_html=True)