"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         SMART MONEY CONCEPT (SMC) ENGINE — XAUUSD (Gold/USD)               ║
║         Institutional-Grade | Production-Ready | Confluence-Driven          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Author  : Quantitative SMC Engine
Version : 2.0.0
Asset   : XAUUSD (adaptable to any instrument)
Timeframe: M5 / M15 / H1 / H4

Modules:
  1. Swing High/Low Detection
  2. Market Structure (BOS / CHOCH)
  3. Liquidity Detection & Sweeps
  4. Fair Value Gap (FVG)
  5. Order Block Detection
  6. Premium / Discount Zones
  7. Multi-Timeframe Bias
  8. Confluence-Based Signal Generation

"""

import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  LOGGING CONFIGURATION
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SMC_Engine")


# ─────────────────────────────────────────────
#  DATA CLASSES  (structured zone containers)
# ─────────────────────────────────────────────

@dataclass
class FVGZone:
    index: int          # candle index where FVG was confirmed
    top: float          # upper boundary of the gap
    bottom: float       # lower boundary of the gap
    direction: str      # "bullish" | "bearish"
    filled: bool = False


@dataclass
class OrderBlock:
    index: int
    top: float
    bottom: float
    direction: str      # "bullish" | "bearish"
    mitigated: bool = False


@dataclass
class StructurePoint:
    index: int
    price: float
    kind: str           # "HH" | "LH" | "HL" | "LL"


@dataclass
class LiquiditySweep:
    index: int
    price: float
    kind: str           # "buy_side" | "sell_side"


@dataclass
class SMCResult:
    """Full SMC analysis result for one timeframe."""
    swing_highs: list = field(default_factory=list)
    swing_lows: list  = field(default_factory=list)
    structure: list   = field(default_factory=list)   # List[StructurePoint]
    bos_bullish: list = field(default_factory=list)   # indices
    bos_bearish: list = field(default_factory=list)
    choch_bullish: list = field(default_factory=list)
    choch_bearish: list = field(default_factory=list)
    liquidity_sweeps: list = field(default_factory=list)  # List[LiquiditySweep]
    fvg_zones: list   = field(default_factory=list)   # List[FVGZone]
    order_blocks: list= field(default_factory=list)   # List[OrderBlock]
    premium_zone: tuple = (0.0, 0.0)  # (eq, swing_high)
    discount_zone: tuple = (0.0, 0.0) # (swing_low, eq)
    equilibrium: float = 0.0
    current_bias: str  = "NEUTRAL"    # "BULLISH" | "BEARISH" | "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 1 — SWING HIGH / LOW DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_swing_points(df: pd.DataFrame, lookback: int = 5) -> tuple[list, list]:
    """
    Identify swing highs and lows using a rolling lookback window.

    A swing high at index i means df['high'][i] is the highest point
    in the window [i-lookback : i+lookback].
    Same logic inverted for swing lows.

    Returns:
        swing_highs: list of (index, price)
        swing_lows:  list of (index, price)
    """
    highs = df["high"].values
    lows  = df["low"].values
    n     = len(df)

    swing_highs, swing_lows = [], []

    for i in range(lookback, n - lookback):
        window_h = highs[i - lookback : i + lookback + 1]
        window_l = lows [i - lookback : i + lookback + 1]

        if highs[i] == np.max(window_h):
            swing_highs.append((i, highs[i]))

        if lows[i] == np.min(window_l):
            swing_lows.append((i, lows[i]))

    logger.info(f"Swings detected — Highs: {len(swing_highs)}, Lows: {len(swing_lows)}")
    return swing_highs, swing_lows


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 2 — MARKET STRUCTURE (BOS / CHOCH)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_market_structure(
    df: pd.DataFrame,
    swing_highs: list,
    swing_lows: list,
) -> tuple[list, list, list, list, list]:
    """
    Classify swings into HH/LH/HL/LL and detect BOS + CHOCH.

    BOS  (Break of Structure): continuation signal
        Bullish BOS → close breaks above previous swing high (HH in uptrend)
        Bearish BOS → close breaks below previous swing low  (LL in downtrend)

    CHOCH (Change of Character): reversal signal
        Bullish CHOCH → price breaks a previous swing HIGH in a downtrend
        Bearish CHOCH → price breaks a previous swing LOW  in an uptrend

    Returns:
        structure_points, bos_bullish_idx, bos_bearish_idx,
        choch_bullish_idx, choch_bearish_idx
    """
    closes = df["close"].values
    structure_points: list[StructurePoint] = []
    bos_bullish, bos_bearish = [], []
    choch_bullish, choch_bearish = [], []

    # ── Tag swing highs as HH or LH ──────────────────────────────────────────
    prev_sh_price = None
    for idx, price in swing_highs:
        if prev_sh_price is None:
            kind = "HH"
        else:
            kind = "HH" if price > prev_sh_price else "LH"
        structure_points.append(StructurePoint(idx, price, kind))
        prev_sh_price = price

    # ── Tag swing lows as HL or LL ────────────────────────────────────────────
    prev_sl_price = None
    for idx, price in swing_lows:
        if prev_sl_price is None:
            kind = "HL"
        else:
            kind = "HL" if price > prev_sl_price else "LL"
        structure_points.append(StructurePoint(idx, price, kind))
        prev_sl_price = price

    structure_points.sort(key=lambda x: x.index)

    # ── BOS / CHOCH detection ─────────────────────────────────────────────────
    # Scan each candle: did close break a prior swing?
    sh_prices = [(idx, p) for idx, p in swing_highs]
    sl_prices = [(idx, p) for idx, p in swing_lows]

    # Determine trend at each swing to classify BOS vs CHOCH
    # Simple rule: if sequence is HH → bullish trend, LH → transitioning, etc.
    def _get_trend_at(idx: int) -> str:
        """Rough trend label at index idx based on recent structure points."""
        recent = [s for s in structure_points if s.index <= idx][-6:]
        hh = sum(1 for s in recent if s.kind == "HH")
        ll = sum(1 for s in recent if s.kind == "LL")
        return "BULLISH" if hh > ll else "BEARISH" if ll > hh else "NEUTRAL"

    for i in range(1, len(closes)):
        close = closes[i]

        # Check breaks of prior swing highs
        for sh_idx, sh_price in sh_prices:
            if sh_idx < i and close > sh_price:
                trend = _get_trend_at(sh_idx)
                if trend == "BULLISH":
                    bos_bullish.append(i)
                else:
                    # Breaking high in downtrend = CHOCH (reversal)
                    choch_bullish.append(i)
                break  # only tag once per candle

        # Check breaks of prior swing lows
        for sl_idx, sl_price in sl_prices:
            if sl_idx < i and close < sl_price:
                trend = _get_trend_at(sl_idx)
                if trend == "BEARISH":
                    bos_bearish.append(i)
                else:
                    # Breaking low in uptrend = CHOCH (reversal)
                    choch_bearish.append(i)
                break

    # Deduplicate
    bos_bullish   = sorted(set(bos_bullish))
    bos_bearish   = sorted(set(bos_bearish))
    choch_bullish = sorted(set(choch_bullish))
    choch_bearish = sorted(set(choch_bearish))

    logger.info(
        f"Structure — BOS Bull: {len(bos_bullish)}, BOS Bear: {len(bos_bearish)}, "
        f"CHOCH Bull: {len(choch_bullish)}, CHOCH Bear: {len(choch_bearish)}"
    )
    return structure_points, bos_bullish, bos_bearish, choch_bullish, choch_bearish


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 3 — LIQUIDITY DETECTION & SWEEPS
# ═══════════════════════════════════════════════════════════════════════════════

def detect_liquidity(
    df: pd.DataFrame,
    swing_highs: list,
    swing_lows: list,
    equal_tolerance: float = 0.002,   # 0.2 % tolerance for "equal" levels
) -> list:
    """
    Identify liquidity sweeps (stop hunts).

    Equal Highs / Equal Lows → clusters of retail stop orders.
    A sweep occurs when price:
      - Wicks ABOVE a prior swing high  (buy-side liquidity grab)
        then CLOSES BELOW it (trap → bearish continuation)
      - Wicks BELOW a prior swing low   (sell-side liquidity grab)
        then CLOSES ABOVE it (trap → bullish continuation)

    Returns:
        list of LiquiditySweep
    """
    highs  = df["high"].values
    lows   = df["low"].values
    closes = df["close"].values
    sweeps: list[LiquiditySweep] = []

    # ── Buy-side sweep (price takes out prior swing high then reverses) ───────
    for sh_idx, sh_price in swing_highs:
        for i in range(sh_idx + 1, len(df)):
            if highs[i] > sh_price and closes[i] < sh_price:
                sweeps.append(LiquiditySweep(i, sh_price, "buy_side"))
                break   # one sweep per swing high

    # ── Sell-side sweep (price takes out prior swing low then reverses) ───────
    for sl_idx, sl_price in swing_lows:
        for i in range(sl_idx + 1, len(df)):
            if lows[i] < sl_price and closes[i] > sl_price:
                sweeps.append(LiquiditySweep(i, sl_price, "sell_side"))
                break

    logger.info(f"Liquidity sweeps detected: {len(sweeps)}")
    return sweeps


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 4 — FAIR VALUE GAP (FVG)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_fvg(df: pd.DataFrame, min_gap_pct: float = 0.001) -> list:
    """
    Detect Fair Value Gaps using 3-candle imbalance logic.

    Bullish FVG:
        candle[i].low  > candle[i-2].high   → gap between i-2 high and i low

    Bearish FVG:
        candle[i].high < candle[i-2].low    → gap between i-2 low and i high

    min_gap_pct: minimum gap size as fraction of close price (filters noise)

    Returns:
        list of FVGZone
    """
    opens  = df["open"].values
    highs  = df["high"].values
    lows   = df["low"].values
    closes = df["close"].values
    fvgs: list[FVGZone] = []

    for i in range(2, len(df)):
        ref_close = closes[i]

        # Bullish FVG
        gap_top    = lows[i]
        gap_bottom = highs[i - 2]
        if gap_top > gap_bottom:
            gap_size = (gap_top - gap_bottom) / ref_close
            if gap_size >= min_gap_pct:
                fvgs.append(FVGZone(i, top=gap_top, bottom=gap_bottom, direction="bullish"))

        # Bearish FVG
        gap_top    = lows[i - 2]
        gap_bottom = highs[i]
        if gap_top < lows[i - 2] and highs[i] < lows[i - 2]:
            gap_size = (lows[i - 2] - highs[i]) / ref_close
            if gap_size >= min_gap_pct:
                fvgs.append(FVGZone(i, top=lows[i - 2], bottom=highs[i], direction="bearish"))

    # Mark FVGs as filled when price trades through them
    for fvg in fvgs:
        for j in range(fvg.index + 1, len(df)):
            if fvg.direction == "bullish" and lows[j] <= fvg.bottom:
                fvg.filled = True
                break
            if fvg.direction == "bearish" and highs[j] >= fvg.top:
                fvg.filled = True
                break

    active = [f for f in fvgs if not f.filled]
    logger.info(f"FVGs detected: {len(fvgs)} total, {len(active)} unfilled")
    return fvgs


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 5 — ORDER BLOCK DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_order_blocks(
    df: pd.DataFrame,
    body_ratio_threshold: float = 0.60,
    lookforward: int = 3,
) -> list:
    """
    Identify institutional Order Blocks.

    Logic:
      1. Find large-body candles (body ≥ body_ratio_threshold × full range)
      2. These represent institutional accumulation / distribution
      3. Bullish OB: last bearish candle BEFORE a strong bullish impulse move
         (price leaves the zone rapidly upward)
      4. Bearish OB: last bullish candle BEFORE a strong bearish impulse move

    Returns:
        list of OrderBlock
    """
    opens  = df["open"].values
    highs  = df["high"].values
    lows   = df["low"].values
    closes = df["close"].values
    order_blocks: list[OrderBlock] = []

    for i in range(1, len(df) - lookforward):
        candle_range = highs[i] - lows[i]
        if candle_range == 0:
            continue

        body   = abs(closes[i] - opens[i])
        body_r = body / candle_range
        is_bullish_candle = closes[i] > opens[i]

        if body_r < body_ratio_threshold:
            continue   # not an institutional candle

        # Measure impulse after this candle
        future_high = np.max(highs[i + 1 : i + 1 + lookforward])
        future_low  = np.min(lows [i + 1 : i + 1 + lookforward])

        # Bullish OB → bearish candle followed by bullish impulse
        if not is_bullish_candle:
            impulse_up = (future_high - closes[i]) / closes[i]
            if impulse_up > 0.001:   # 0.1 % minimum impulse
                order_blocks.append(
                    OrderBlock(i, top=opens[i], bottom=closes[i], direction="bullish")
                )

        # Bearish OB → bullish candle followed by bearish impulse
        else:
            impulse_dn = (closes[i] - future_low) / closes[i]
            if impulse_dn > 0.001:
                order_blocks.append(
                    OrderBlock(i, top=closes[i], bottom=opens[i], direction="bearish")
                )

    # Mark OBs as mitigated when price re-enters the zone
    for ob in order_blocks:
        for j in range(ob.index + 1, len(df)):
            if ob.direction == "bullish" and lows[j] <= ob.top:
                ob.mitigated = True
                break
            if ob.direction == "bearish" and highs[j] >= ob.bottom:
                ob.mitigated = True
                break

    active = [o for o in order_blocks if not o.mitigated]
    logger.info(f"Order Blocks: {len(order_blocks)} total, {len(active)} unmitigated")
    return order_blocks


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 6 — PREMIUM / DISCOUNT ZONES
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_premium_discount(
    df: pd.DataFrame,
    swing_highs: list,
    swing_lows: list,
    lookback_bars: int = 50,
) -> tuple[float, float, float, tuple, tuple]:
    """
    Calculate the Premium / Discount framework based on the most recent
    significant swing high and swing low.

    Equilibrium = 50% of [swing_low → swing_high] range
    Premium     = above equilibrium (institutional sell zone)
    Discount    = below equilibrium (institutional buy zone)

    Returns:
        swing_high, swing_low, equilibrium,
        premium_zone=(eq, swing_high),
        discount_zone=(swing_low, eq)
    """
    end_idx = len(df) - 1
    start_idx = max(0, end_idx - lookback_bars)

    # Filter swings within lookback window
    recent_sh = [(i, p) for i, p in swing_highs if i >= start_idx]
    recent_sl = [(i, p) for i, p in swing_lows  if i >= start_idx]

    if not recent_sh or not recent_sl:
        # Fallback to raw OHLC extremes
        sw_h = df["high"].iloc[-lookback_bars:].max()
        sw_l = df["low"] .iloc[-lookback_bars:].min()
    else:
        sw_h = max(p for _, p in recent_sh)
        sw_l = min(p for _, p in recent_sl)

    equilibrium   = (sw_h + sw_l) / 2
    premium_zone  = (equilibrium, sw_h)
    discount_zone = (sw_l, equilibrium)

    logger.info(
        f"Zones — Swing High: {sw_h:.2f}, Swing Low: {sw_l:.2f}, "
        f"EQ: {equilibrium:.2f}"
    )
    return sw_h, sw_l, equilibrium, premium_zone, discount_zone


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 7 — HIGHER TIMEFRAME BIAS
# ═══════════════════════════════════════════════════════════════════════════════

def determine_htf_bias(htf_df: pd.DataFrame, lookback: int = 10) -> str:
    """
    Derive directional bias from a higher timeframe (H1 / H4).

    Logic:
        Compare recent close vs EMA + structure direction
        Simple but effective for bias alignment.

    Returns:
        "BULLISH" | "BEARISH" | "NEUTRAL"
    """
    if htf_df is None or len(htf_df) < lookback + 2:
        return "NEUTRAL"

    closes = htf_df["close"].values[-lookback:]
    ema    = pd.Series(htf_df["close"]).ewm(span=20).mean().values

    # Trend via last EMA slope
    ema_slope = ema[-1] - ema[-5] if len(ema) >= 5 else 0

    # Higher highs / higher lows count
    highs   = htf_df["high"].values[-lookback:]
    lows    = htf_df["low"].values[-lookback:]
    hh_count = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i - 1])
    ll_count = sum(1 for i in range(1, len(lows))  if lows[i]  < lows[i - 1])

    if ema_slope > 0 and hh_count > ll_count:
        bias = "BULLISH"
    elif ema_slope < 0 and ll_count > hh_count:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    logger.info(f"HTF Bias: {bias} (EMA slope: {ema_slope:.4f})")
    return bias


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL SMC ANALYSIS — Combines All Modules
# ═══════════════════════════════════════════════════════════════════════════════

def run_smc_analysis(
    df: pd.DataFrame,
    htf_df: Optional[pd.DataFrame] = None,
    swing_lookback: int = 5,
) -> SMCResult:
    """
    Execute the complete SMC analysis pipeline on a DataFrame.

    Args:
        df            : Primary timeframe OHLC DataFrame
        htf_df        : Optional higher-timeframe DataFrame for bias
        swing_lookback: Lookback window for swing detection

    Returns:
        SMCResult with all detected zones and structure
    """
    if len(df) < 20:
        logger.warning("Insufficient data for SMC analysis (need ≥ 20 bars)")
        return SMCResult()

    result = SMCResult()

    # Step 1 — Swings
    result.swing_highs, result.swing_lows = detect_swing_points(df, swing_lookback)

    # Step 2 — Market Structure
    (
        result.structure,
        result.bos_bullish,
        result.bos_bearish,
        result.choch_bullish,
        result.choch_bearish,
    ) = detect_market_structure(df, result.swing_highs, result.swing_lows)

    # Step 3 — Liquidity
    result.liquidity_sweeps = detect_liquidity(df, result.swing_highs, result.swing_lows)

    # Step 4 — FVG
    result.fvg_zones = detect_fvg(df)

    # Step 5 — Order Blocks
    result.order_blocks = detect_order_blocks(df)

    # Step 6 — Premium / Discount
    sw_h, sw_l, eq, prem, disc = calculate_premium_discount(
        df, result.swing_highs, result.swing_lows
    )
    result.premium_zone  = prem
    result.discount_zone = disc
    result.equilibrium   = eq

    # Step 7 — HTF Bias
    result.current_bias = determine_htf_bias(htf_df)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 8 — CONFLUENCE-BASED SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(
    df: pd.DataFrame,
    result: SMCResult,
    atr_multiplier_sl: float = 1.5,
    risk_reward_target: float = 3.0,
) -> dict:
    """
    Generate a high-probability trade signal from SMC confluence.

    BUY Confluence:
      ✓ HTF bias is BULLISH (or NEUTRAL)
      ✓ Bullish CHOCH present recently
      ✓ Sell-side liquidity sweep detected recently
      ✓ Price is in DISCOUNT zone
      ✓ Unfilled bullish FVG exists near current price
      ✓ Unmitigated bullish Order Block present (bonus)

    SELL Confluence:
      ✓ HTF bias is BEARISH (or NEUTRAL)
      ✓ Bearish CHOCH or Bearish BOS present recently
      ✓ Buy-side liquidity sweep detected recently
      ✓ Price is in PREMIUM zone
      ✓ Unfilled bearish FVG near current price
      ✓ Unmitigated bearish Order Block present (bonus)

    Confidence:
        Each confluence factor adds points (see weights below).
        Score → 0–100.

    Returns:
        dict with signal, entry, stop_loss, take_profit, risk_reward,
              confidence, reason
    """
    if df.empty or len(df) < 5:
        return _no_trade("Insufficient data")

    current_close = df["close"].iloc[-1]
    current_idx   = len(df) - 1

    # How recent is "recent"? Look back N candles for signals
    recency = min(10, len(df) // 3)

    # ── ATR for dynamic SL sizing ─────────────────────────────────────────────
    atr = _calc_atr(df, period=14)

    # ── Premium / Discount check ──────────────────────────────────────────────
    in_discount = current_close <= result.equilibrium
    in_premium  = current_close >= result.equilibrium

    # ── Recent structure events ───────────────────────────────────────────────
    recent_choch_bull = any(i >= current_idx - recency for i in result.choch_bullish)
    recent_choch_bear = any(i >= current_idx - recency for i in result.choch_bearish)
    recent_bos_bear   = any(i >= current_idx - recency for i in result.bos_bearish)
    recent_bos_bull   = any(i >= current_idx - recency for i in result.bos_bullish)

    # ── Recent liquidity sweeps ───────────────────────────────────────────────
    recent_sell_sweep = any(
        s.kind == "sell_side" and s.index >= current_idx - recency
        for s in result.liquidity_sweeps
    )
    recent_buy_sweep = any(
        s.kind == "buy_side" and s.index >= current_idx - recency
        for s in result.liquidity_sweeps
    )

    # ── Active FVGs near price ────────────────────────────────────────────────
    price_tolerance = atr * 2
    active_bull_fvg = [
        f for f in result.fvg_zones
        if f.direction == "bullish"
        and not f.filled
        and f.bottom <= current_close <= f.top + price_tolerance
    ]
    active_bear_fvg = [
        f for f in result.fvg_zones
        if f.direction == "bearish"
        and not f.filled
        and f.bottom - price_tolerance <= current_close <= f.top
    ]

    # ── Active OBs near price ─────────────────────────────────────────────────
    active_bull_ob = [
        o for o in result.order_blocks
        if o.direction == "bullish"
        and not o.mitigated
        and o.bottom <= current_close <= o.top + price_tolerance
    ]
    active_bear_ob = [
        o for o in result.order_blocks
        if o.direction == "bearish"
        and not o.mitigated
        and o.bottom - price_tolerance <= current_close <= o.top
    ]

    # ─────────────────────────────────────────────────────────────────────────
    #  BUY SIGNAL SCORING
    # ─────────────────────────────────────────────────────────────────────────
    buy_score   = 0
    buy_reasons = []

    if result.current_bias in ("BULLISH", "NEUTRAL"):
        buy_score += 15
        buy_reasons.append(f"HTF bias: {result.current_bias}")

    if recent_choch_bull:
        buy_score += 25
        buy_reasons.append("Bullish CHOCH detected")

    if recent_sell_sweep:
        buy_score += 20
        buy_reasons.append("Sell-side liquidity swept")

    if in_discount:
        buy_score += 15
        buy_reasons.append(f"Price in Discount zone (EQ: {result.equilibrium:.2f})")

    if active_bull_fvg:
        buy_score += 15
        buy_reasons.append(f"Bullish FVG at {active_bull_fvg[0].bottom:.2f}–{active_bull_fvg[0].top:.2f}")

    if active_bull_ob:
        buy_score += 10
        buy_reasons.append(f"Bullish OB at {active_bull_ob[0].bottom:.2f}–{active_bull_ob[0].top:.2f}")

    # ─────────────────────────────────────────────────────────────────────────
    #  SELL SIGNAL SCORING
    # ─────────────────────────────────────────────────────────────────────────
    sell_score   = 0
    sell_reasons = []

    if result.current_bias in ("BEARISH", "NEUTRAL"):
        sell_score += 15
        sell_reasons.append(f"HTF bias: {result.current_bias}")

    if recent_choch_bear or recent_bos_bear:
        sell_score += 25
        sell_reasons.append("Bearish CHOCH / BOS detected")

    if recent_buy_sweep:
        sell_score += 20
        sell_reasons.append("Buy-side liquidity swept")

    if in_premium:
        sell_score += 15
        sell_reasons.append(f"Price in Premium zone (EQ: {result.equilibrium:.2f})")

    if active_bear_fvg:
        sell_score += 15
        sell_reasons.append(f"Bearish FVG at {active_bear_fvg[0].bottom:.2f}–{active_bear_fvg[0].top:.2f}")

    if active_bear_ob:
        sell_score += 10
        sell_reasons.append(f"Bearish OB at {active_bear_ob[0].bottom:.2f}–{active_bear_ob[0].top:.2f}")

    # ─────────────────────────────────────────────────────────────────────────
    #  DECISION
    # ─────────────────────────────────────────────────────────────────────────
    MIN_CONFIDENCE = 55   # minimum score to issue a signal

    if buy_score >= sell_score and buy_score >= MIN_CONFIDENCE:
        entry       = current_close
        stop_loss   = entry - atr * atr_multiplier_sl
        take_profit = entry + (entry - stop_loss) * risk_reward_target
        rr          = round((take_profit - entry) / (entry - stop_loss), 2)
        return {
            "signal":      "BUY",
            "entry":       round(entry,       4),
            "stop_loss":   round(stop_loss,   4),
            "take_profit": round(take_profit, 4),
            "risk_reward": rr,
            "confidence":  min(buy_score, 100),
            "reason":      " | ".join(buy_reasons),
        }

    elif sell_score > buy_score and sell_score >= MIN_CONFIDENCE:
        entry       = current_close
        stop_loss   = entry + atr * atr_multiplier_sl
        take_profit = entry - (stop_loss - entry) * risk_reward_target
        rr          = round((entry - take_profit) / (stop_loss - entry), 2)
        return {
            "signal":      "SELL",
            "entry":       round(entry,       4),
            "stop_loss":   round(stop_loss,   4),
            "take_profit": round(take_profit, 4),
            "risk_reward": rr,
            "confidence":  min(sell_score, 100),
            "reason":      " | ".join(sell_reasons),
        }

    else:
        best = max(buy_score, sell_score)
        return _no_trade(
            f"Insufficient confluence (Buy: {buy_score}, Sell: {sell_score}). "
            f"Need ≥ {MIN_CONFIDENCE}. Best factors: "
            + (" | ".join(buy_reasons) if buy_score > sell_score else " | ".join(sell_reasons))
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _no_trade(reason: str) -> dict:
    return {
        "signal":      "NO TRADE",
        "entry":       0.0,
        "stop_loss":   0.0,
        "take_profit": 0.0,
        "risk_reward": 0.0,
        "confidence":  0,
        "reason":      reason,
    }


def _calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Average True Range — used for dynamic SL sizing."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"].shift(1)
    tr    = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr   = tr.rolling(period).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else float(high.iloc[-1] - low.iloc[-1])


def print_signal(signal: dict) -> None:
    """Pretty-print the signal dictionary."""
    bar = "═" * 55
    print(f"\n{bar}")
    print(f"  SMC SIGNAL  →  {signal['signal']}")
    print(bar)
    print(f"  Entry      : {signal['entry']}")
    print(f"  Stop Loss  : {signal['stop_loss']}")
    print(f"  Take Profit: {signal['take_profit']}")
    print(f"  R:R Ratio  : 1 : {signal['risk_reward']}")
    print(f"  Confidence : {signal['confidence']}%")
    print(f"  Reason     : {signal['reason']}")
    print(f"{bar}\n")


def log_zones(result: SMCResult) -> None:
    """Log all detected zones for audit / debugging."""
    logger.info("─── DETECTED ZONES ───────────────────────────────")
    logger.info(f"  Swing Highs   : {len(result.swing_highs)}")
    logger.info(f"  Swing Lows    : {len(result.swing_lows)}")
    logger.info(f"  BOS Bullish   : {result.bos_bullish}")
    logger.info(f"  BOS Bearish   : {result.bos_bearish}")
    logger.info(f"  CHOCH Bullish : {result.choch_bullish}")
    logger.info(f"  CHOCH Bearish : {result.choch_bearish}")
    logger.info(f"  Liq. Sweeps   : {[(s.index, s.kind) for s in result.liquidity_sweeps]}")

    active_fvgs = [f for f in result.fvg_zones if not f.filled]
    logger.info(f"  Active FVGs   : {len(active_fvgs)}")
    for f in active_fvgs:
        logger.info(f"    [{f.direction.upper():7}] idx={f.index} {f.bottom:.2f} – {f.top:.2f}")

    active_obs = [o for o in result.order_blocks if not o.mitigated]
    logger.info(f"  Active OBs    : {len(active_obs)}")
    for o in active_obs:
        logger.info(f"    [{o.direction.upper():7}] idx={o.index} {o.bottom:.2f} – {o.top:.2f}")

    logger.info(f"  Equilibrium   : {result.equilibrium:.2f}")
    logger.info(f"  Premium Zone  : {result.premium_zone[0]:.2f} – {result.premium_zone[1]:.2f}")
    logger.info(f"  Discount Zone : {result.discount_zone[0]:.2f} – {result.discount_zone[1]:.2f}")
    logger.info(f"  HTF Bias      : {result.current_bias}")
    logger.info("──────────────────────────────────────────────────")


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API  (main entry point)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(
    df: pd.DataFrame,
    htf_df: Optional[pd.DataFrame] = None,
    swing_lookback: int = 5,
    atr_multiplier_sl: float = 1.5,
    risk_reward_target: float = 3.0,
    verbose: bool = True,
) -> dict:
    """
    One-call entry point: run full SMC analysis and return signal.

    Args:
        df                 : Primary (lower-TF) OHLC DataFrame
        htf_df             : Higher-TF DataFrame for bias (optional)
        swing_lookback     : Lookback for swing detection (5–10 recommended)
        atr_multiplier_sl  : SL distance in ATR multiples
        risk_reward_target : Minimum R:R ratio for TP
        verbose            : Log detected zones

    Returns:
        Signal dictionary
    """
    _validate_df(df)
    result = run_smc_analysis(df, htf_df, swing_lookback)

    if verbose:
        log_zones(result)

    signal = generate_signal(
        df, result,
        atr_multiplier_sl=atr_multiplier_sl,
        risk_reward_target=risk_reward_target,
    )
    return signal


def _validate_df(df: pd.DataFrame) -> None:
    required = {"open", "high", "low", "close"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing columns: {missing}")
    if df.isnull().any().any():
        logger.warning("DataFrame contains NaN values — forward-filling")
        df.ffill(inplace=True)
        df.bfill(inplace=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SAMPLE TEST USAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_sample_xauusd(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic XAUUSD-like OHLC data for testing.
    Starts near 2300, includes a downtrend → reversal → uptrend pattern.
    """
    np.random.seed(seed)
    close = [2300.0]

    # Phase 1: downtrend (first 60 bars)
    for _ in range(60):
        close.append(close[-1] + np.random.normal(-1.5, 3.0))

    # Phase 2: liquidity sweep low + reversal (bars 60–80)
    for _ in range(20):
        close.append(close[-1] + np.random.normal(-0.5, 4.0))
    # Sweep
    close.append(close[-1] - 15)
    close.append(close[-1] + 20)   # rejection / reversal candle

    # Phase 3: uptrend (remaining bars)
    for _ in range(n - len(close)):
        close.append(close[-1] + np.random.normal(1.2, 2.5))

    close = np.array(close[:n])

    rows = []
    for c in close:
        o = c + np.random.uniform(-2, 2)
        h = max(o, c) + np.random.uniform(0.5, 4)
        l = min(o, c) - np.random.uniform(0.5, 4)
        rows.append({"open": o, "high": h, "low": l, "close": c})

    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  SMC ENGINE — XAUUSD  |  Production Test Run")
    print("█" * 60)

    # ── Primary TF (e.g., M15) ───────────────────────────────────────────────
    ltf_df = _generate_sample_xauusd(n=200)

    # ── Higher TF (e.g., H1) ─────────────────────────────────────────────────
    # In production: pass real H1 data; here we downsample
    htf_df = _generate_sample_xauusd(n=60, seed=99)

    # ── Run Analysis ──────────────────────────────────────────────────────────
    signal = analyze(
        df=ltf_df,
        htf_df=htf_df,
        swing_lookback=5,
        atr_multiplier_sl=1.5,
        risk_reward_target=3.0,
        verbose=True,
    )

    print_signal(signal)

    # ── Minimal example (no HTF bias) ─────────────────────────────────────────
    print("─── Quick Run (no HTF) ───────────────────────────────")
    quick_signal = analyze(ltf_df, verbose=False)
    print(f"  Signal: {quick_signal['signal']}  |  Confidence: {quick_signal['confidence']}%")
    print(f"  Reason: {quick_signal['reason']}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  DEMO: FORCE-INJECT CONFLUENCE TO SHOW ALL SIGNAL PATHS
#  (For testing / documentation only — not for live use)
# ═══════════════════════════════════════════════════════════════════════════════

def _demo_all_signal_paths():
    """
    Directly injects SMCResult state to demonstrate all three signal outputs.
    In live usage, confluence emerges naturally from real market data.
    """
    from dataclasses import replace
    df = _generate_sample_xauusd(n=120, seed=11)
    result = run_smc_analysis(df, htf_df=None, swing_lookback=5)
    last  = len(df) - 1
    close = df["close"].iloc[-1]
    eq    = result.equilibrium

    # ── DEMO 1: BUY signal (inject bullish confluence) ────────────────────────
    result.current_bias  = "BULLISH"
    result.choch_bullish = [last - 3]
    result.liquidity_sweeps = [LiquiditySweep(last - 4, close - 10, "sell_side")]
    result.discount_zone = (close - 50, close + 5)   # price inside discount
    result.equilibrium   = close + 10                  # eq above price → discount
    result.fvg_zones     = [FVGZone(last - 2, close + 2, close - 2, "bullish")]
    result.order_blocks  = [OrderBlock(last - 5, close + 1, close - 3, "bullish")]

    sig_buy = generate_signal(df, result)
    print("\n─── DEMO: BUY Signal Path ───")
    print_signal(sig_buy)

    # ── DEMO 2: SELL signal ────────────────────────────────────────────────────
    result2 = run_smc_analysis(df)
    result2.current_bias  = "BEARISH"
    result2.choch_bearish = [last - 3]
    result2.bos_bearish   = [last - 5]
    result2.liquidity_sweeps = [LiquiditySweep(last - 4, close + 10, "buy_side")]
    result2.premium_zone  = (close - 5, close + 50)
    result2.equilibrium   = close - 10                # eq below price → premium
    result2.fvg_zones     = [FVGZone(last - 2, close + 3, close - 1, "bearish")]
    result2.order_blocks  = [OrderBlock(last - 5, close + 4, close - 1, "bearish")]

    sig_sell = generate_signal(df, result2)
    print("─── DEMO: SELL Signal Path ───")
    print_signal(sig_sell)

    # ── DEMO 3: NO TRADE (weak confluence) ────────────────────────────────────
    result3 = run_smc_analysis(df)
    sig_nt = generate_signal(df, result3)
    print("─── DEMO: NO TRADE (natural sparse data) ───")
    print_signal(sig_nt)


if __name__ == "__main__":
    pass  # Main block already ran above; call demo separately if needed
    # _demo_all_signal_paths()  # Uncomment to see all three signal paths
