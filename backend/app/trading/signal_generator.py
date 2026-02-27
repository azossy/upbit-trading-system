"""
============================================================
매매 신호 생성 모듈 (Signal Generator)
기술적 지표(RSI, MACD, 볼린저 밴드 등)를 분석하여
매수/매도 신호를 생성합니다.

신호 체계:
  - BUY  : 매수 진입 (다중 지표 확인 후)
  - SELL : 매도 청산 (손절/익절/트레일링 스탑)
  - HOLD : 관망 (명확한 신호 없음)

진입 조건 (AND 조건, 3개 이상 충족 시 매수):
  1. RSI(14) 30~45 범위 (과매도 구간 반등)
  2. MACD 골든크로스 (MACD선이 시그널선 상향 돌파)
  3. 볼린저 밴드 하단 접근 후 반등
  4. 거래량 급증 (20일 평균 대비 1.5배 이상)
  5. 5일 이동평균선 위에 종가
============================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from loguru import logger


@dataclass
class Signal:
    """
    매매 신호 데이터 클래스.

    Attributes:
        action: 매매 동작 ("BUY", "SELL", "HOLD")
        coin: 코인 마켓 코드 (예: "KRW-BTC")
        strength: 신호 강도 (0.0 ~ 1.0, 높을수록 강한 신호)
        reasons: 신호 발생 근거 목록
        indicators: 현재 지표값 딕셔너리
        timestamp: 신호 생성 시간
    """
    action: str          # "BUY" | "SELL" | "HOLD"
    coin: str            # 마켓 코드
    strength: float      # 신호 강도 (0.0 ~ 1.0)
    reasons: List[str]   # 신호 근거 목록
    indicators: Dict     # 현재 지표값
    timestamp: datetime  # 생성 시간


class SignalGenerator:
    """
    기술적 지표 기반 매매 신호 생성기.

    캔들 데이터를 입력받아 다중 지표를 계산하고,
    매수/매도/관망 신호를 생성합니다.

    사용법:
        generator = SignalGenerator()
        signal = generator.generate("KRW-BTC", candle_df, market_mode="BULL")
    """

    def __init__(self):
        """기본 지표 파라미터 초기화"""
        # RSI 파라미터
        self.rsi_period = 14           # RSI 계산 기간
        self.rsi_oversold = 30         # 과매도 기준
        self.rsi_overbought = 70       # 과매수 기준

        # MACD 파라미터
        self.macd_fast = 12            # 단기 EMA 기간
        self.macd_slow = 26            # 장기 EMA 기간
        self.macd_signal = 9           # 시그널 EMA 기간

        # 볼린저 밴드 파라미터
        self.bb_period = 20            # 이동평균 기간
        self.bb_std_multiplier = 2.0   # 표준편차 배수

        # 거래량 파라미터
        self.volume_ma_period = 20     # 거래량 이동평균 기간
        self.volume_surge_ratio = 1.5  # 거래량 급증 배율

    # ══════════════════════════════════════════════════
    # 메인 — 신호 생성
    # ══════════════════════════════════════════════════

    def generate(
        self,
        coin: str,
        df: pd.DataFrame,
        market_mode: str = "SIDEWAYS",
    ) -> Signal:
        """
        매매 신호를 생성합니다.

        Args:
            coin: 마켓 코드 (예: "KRW-BTC")
            df: 캔들 OHLCV DataFrame (최소 200행)
            market_mode: 현재 시장 모드 ("BULL", "SIDEWAYS", "BEAR")

        Returns:
            Signal 객체 (action, strength, reasons 등)
        """
        if len(df) < 50:
            # 데이터 부족 시 관망
            return Signal(
                action="HOLD",
                coin=coin,
                strength=0.0,
                reasons=["데이터 부족 (50개 미만)"],
                indicators={},
                timestamp=datetime.utcnow(),
            )

        # ── 1) 기술적 지표 계산 ──
        indicators = self._calculate_indicators(df)

        # ── 2) 매수 조건 확인 ──
        buy_reasons = []
        buy_score = 0

        # 조건 1: RSI 과매도 구간 반등 (30~45)
        if self.rsi_oversold <= indicators["rsi"] <= 45:
            buy_reasons.append(f"RSI 과매도 반등 구간 ({indicators['rsi']:.1f})")
            buy_score += 1

        # 조건 2: MACD 골든크로스 (MACD > Signal, 이전에는 아래였음)
        if indicators["macd_cross"] == "golden":
            buy_reasons.append("MACD 골든크로스 발생")
            buy_score += 1

        # 조건 3: 볼린저 밴드 하단 접근 후 반등
        if indicators["bb_position"] <= 0.2 and indicators["price_above_ma5"]:
            buy_reasons.append("볼린저 밴드 하단 반등")
            buy_score += 1

        # 조건 4: 거래량 급증
        if indicators["volume_surge"]:
            buy_reasons.append(
                f"거래량 급증 (평균 대비 {indicators['volume_ratio']:.1f}배)"
            )
            buy_score += 1

        # 조건 5: 5일 이동평균 위에 종가
        if indicators["price_above_ma5"]:
            buy_reasons.append("종가 > 5일 이동평균")
            buy_score += 1

        # ── 3) 매도 조건 확인 ──
        sell_reasons = []
        sell_score = 0

        # 조건 1: RSI 과매수 (70 이상)
        if indicators["rsi"] >= self.rsi_overbought:
            sell_reasons.append(f"RSI 과매수 ({indicators['rsi']:.1f})")
            sell_score += 1

        # 조건 2: MACD 데드크로스
        if indicators["macd_cross"] == "dead":
            sell_reasons.append("MACD 데드크로스 발생")
            sell_score += 1

        # 조건 3: 볼린저 밴드 상단 이탈
        if indicators["bb_position"] >= 1.0:
            sell_reasons.append("볼린저 밴드 상단 이탈")
            sell_score += 1

        # ── 4) 시장 모드에 따른 진입 기준 조절 ──
        # 상승장: 3개 이상 조건 충족 시 매수
        # 횡보장: 4개 이상 조건 충족 시 매수
        # 하락장: 5개 모두 충족 시에만 매수
        required_conditions = {
            "BULL": 3,
            "SIDEWAYS": 4,
            "BEAR": 5,
        }
        min_conditions = required_conditions.get(market_mode, 4)

        # ── 5) 신호 결정 ──
        if buy_score >= min_conditions:
            # 매수 신호
            strength = min(1.0, buy_score / 5.0)
            return Signal(
                action="BUY",
                coin=coin,
                strength=strength,
                reasons=buy_reasons,
                indicators=indicators,
                timestamp=datetime.utcnow(),
            )
        elif sell_score >= 2:
            # 매도 신호 (2개 이상 조건 충족)
            strength = min(1.0, sell_score / 3.0)
            return Signal(
                action="SELL",
                coin=coin,
                strength=strength,
                reasons=sell_reasons,
                indicators=indicators,
                timestamp=datetime.utcnow(),
            )
        else:
            # 관망
            return Signal(
                action="HOLD",
                coin=coin,
                strength=0.0,
                reasons=["명확한 매매 신호 없음"],
                indicators=indicators,
                timestamp=datetime.utcnow(),
            )

    # ══════════════════════════════════════════════════
    # 지표 계산
    # ══════════════════════════════════════════════════

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        모든 기술적 지표를 한 번에 계산합니다.

        Args:
            df: OHLCV DataFrame

        Returns:
            지표값 딕셔너리
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # ── RSI(14) 계산 ──
        rsi = self._calc_rsi(close, self.rsi_period)

        # ── MACD 계산 ──
        macd_line, signal_line, macd_hist = self._calc_macd(close)
        # MACD 크로스 판단 (현재와 이전 MACD 히스토그램 비교)
        if len(macd_hist) >= 2:
            if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0:
                macd_cross = "golden"  # 골든크로스 (상향 돌파)
            elif macd_hist.iloc[-1] < 0 and macd_hist.iloc[-2] >= 0:
                macd_cross = "dead"    # 데드크로스 (하향 돌파)
            else:
                macd_cross = "none"
        else:
            macd_cross = "none"

        # ── 볼린저 밴드 계산 ──
        bb_upper, bb_middle, bb_lower = self._calc_bollinger_bands(close)
        # 볼린저 밴드 내 현재가 위치 (0=하단, 0.5=중간, 1=상단)
        bb_range = bb_upper - bb_lower
        if bb_range != 0:
            bb_position = (close.iloc[-1] - bb_lower) / bb_range
        else:
            bb_position = 0.5

        # ── 거래량 분석 ──
        vol_ma = volume.rolling(self.volume_ma_period).mean().iloc[-1]
        current_vol = volume.iloc[-1]
        volume_ratio = current_vol / vol_ma if vol_ma > 0 else 1.0
        volume_surge = volume_ratio >= self.volume_surge_ratio

        # ── 5일 이동평균 ──
        ma5 = close.rolling(5).mean().iloc[-1]
        price_above_ma5 = close.iloc[-1] > ma5

        # ── ATR(14) — 손절 계산용 ──
        atr = self._calc_atr(high, low, close, period=14)

        return {
            "rsi": rsi,
            "macd_line": macd_line.iloc[-1] if len(macd_line) > 0 else 0,
            "macd_signal": signal_line.iloc[-1] if len(signal_line) > 0 else 0,
            "macd_hist": macd_hist.iloc[-1] if len(macd_hist) > 0 else 0,
            "macd_cross": macd_cross,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "bb_position": bb_position,
            "volume_ratio": volume_ratio,
            "volume_surge": volume_surge,
            "price_above_ma5": price_above_ma5,
            "ma5": ma5,
            "atr": atr,
            "current_price": close.iloc[-1],
        }

    # ══════════════════════════════════════════════════
    # RSI (Relative Strength Index)
    # ══════════════════════════════════════════════════

    def _calc_rsi(self, close: pd.Series, period: int = 14) -> float:
        """
        RSI를 계산합니다.

        RSI = 100 - (100 / (1 + RS))
        RS = 평균 상승폭 / 평균 하락폭

        Args:
            close: 종가 시리즈
            period: RSI 계산 기간 (기본 14)

        Returns:
            RSI 값 (0~100)
        """
        delta = close.diff()  # 전일 대비 변동분

        # 상승분과 하락분 분리
        gain = delta.where(delta > 0, 0.0)   # 상승일만 (나머지 0)
        loss = (-delta).where(delta < 0, 0.0)  # 하락일만 (절대값, 나머지 0)

        # 지수이동평균(EMA)으로 평균 계산 (Wilder's Smoothing)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean().iloc[-1]
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean().iloc[-1]

        if avg_loss == 0:
            return 100.0  # 하락이 없으면 RSI = 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    # ══════════════════════════════════════════════════
    # MACD (Moving Average Convergence Divergence)
    # ══════════════════════════════════════════════════

    def _calc_macd(
        self,
        close: pd.Series,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD를 계산합니다.

        MACD = 단기EMA(12) - 장기EMA(26)
        Signal = MACD의 EMA(9)
        Histogram = MACD - Signal

        Args:
            close: 종가 시리즈

        Returns:
            (MACD선, 시그널선, 히스토그램) 튜플
        """
        ema_fast = close.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.macd_slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow                                # MACD 선
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()  # 시그널 선
        histogram = macd_line - signal_line                             # 히스토그램

        return macd_line, signal_line, histogram

    # ══════════════════════════════════════════════════
    # 볼린저 밴드 (Bollinger Bands)
    # ══════════════════════════════════════════════════

    def _calc_bollinger_bands(
        self,
        close: pd.Series,
    ) -> Tuple[float, float, float]:
        """
        볼린저 밴드를 계산합니다.

        상단: 중심선 + (표준편차 × 배수)
        중심: 20일 이동평균
        하단: 중심선 - (표준편차 × 배수)

        Args:
            close: 종가 시리즈

        Returns:
            (상단, 중심, 하단) 값 튜플
        """
        middle = close.rolling(self.bb_period).mean().iloc[-1]
        std = close.rolling(self.bb_period).std().iloc[-1]

        upper = middle + (std * self.bb_std_multiplier)  # 상단 밴드
        lower = middle - (std * self.bb_std_multiplier)  # 하단 밴드

        return upper, middle, lower

    # ══════════════════════════════════════════════════
    # ATR (Average True Range)
    # ══════════════════════════════════════════════════

    def _calc_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> float:
        """
        ATR(Average True Range)을 계산합니다.
        손절가 계산에 사용됩니다.

        True Range = max(고가-저가, |고가-전일종가|, |저가-전일종가|)
        ATR = True Range의 N일 이동평균

        Args:
            high: 고가 시리즈
            low: 저가 시리즈
            close: 종가 시리즈
            period: 평균 기간 (기본 14)

        Returns:
            ATR 값
        """
        tr_list = []
        for i in range(1, len(close)):
            h_l = high.iloc[i] - low.iloc[i]
            h_pc = abs(high.iloc[i] - close.iloc[i - 1])
            l_pc = abs(low.iloc[i] - close.iloc[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))

        if len(tr_list) < period:
            return np.mean(tr_list) if tr_list else 0.0

        return np.mean(tr_list[-period:])
