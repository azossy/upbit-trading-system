"""
============================================================
시장 상황 분석 모듈 (Market Analyzer)
현재 시장이 상승장/횡보장/하락장인지 판단하고,
시장 점수(0~100)를 산출하여 투자 전략의 기본 파라미터를 결정합니다.

분석 요소 (5가지):
  1. BTC 가격 추세 (이동평균 크로스)
  2. 거래량 분석 (거래대금 증감)
  3. 변동성 분석 (ATR, 볼린저 밴드 폭)
  4. 시장 심리 (공포탐욕 지수 — 외부 API)
  5. 알트코인 모멘텀 (상위 코인 일괄 분석)

시장 모드:
  - BULL (상승장): 점수 60 이상 → 공격적 투자 (최대 50%)
  - SIDEWAYS (횡보장): 점수 40~59 → 보수적 투자 (최대 30%)
  - BEAR (하락장): 점수 39 이하 → 최소 투자 (최대 15%)
  - UNKNOWN: 데이터 부족 시
============================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.trading.upbit_client import UpbitClient


class MarketAnalyzer:
    """
    시장 상황 분석기.

    여러 기술적 지표를 종합하여 시장 점수(0~100)를 산출하고,
    이를 바탕으로 시장 모드(BULL/SIDEWAYS/BEAR)를 결정합니다.

    사용법:
        analyzer = MarketAnalyzer(upbit_client)
        result = await analyzer.analyze()
        print(result["mode"])   # "BULL" / "SIDEWAYS" / "BEAR"
        print(result["score"])  # 0 ~ 100
    """

    def __init__(self, client: UpbitClient):
        """
        Args:
            client: 업비트 API 클라이언트 인스턴스
        """
        self.client = client

    async def analyze(self) -> Dict:
        """
        시장 상황을 종합 분석합니다.

        5가지 분석 항목의 점수를 가중 평균하여 최종 시장 점수를 산출합니다.

        Returns:
            {
                "mode": "BULL" | "SIDEWAYS" | "BEAR",
                "score": int (0~100),
                "details": {
                    "btc_trend": float,       # BTC 추세 점수
                    "volume": float,          # 거래량 점수
                    "volatility": float,      # 변동성 점수
                    "fear_greed": float,      # 공포탐욕 점수
                    "altcoin_momentum": float, # 알트코인 모멘텀 점수
                },
                "analyzed_at": str (ISO 시간)
            }
        """
        try:
            # ── 1) BTC 일봉 캔들 데이터 수집 (200일) ──
            btc_candles = await self.client.get_candles(
                "KRW-BTC", interval="days", count=200
            )
            btc_df = self._candles_to_dataframe(btc_candles)

            # ── 2) 각 분석 항목 점수 계산 ──
            btc_trend_score = self._analyze_btc_trend(btc_df)        # BTC 추세
            volume_score = self._analyze_volume(btc_df)               # 거래량
            volatility_score = self._analyze_volatility(btc_df)       # 변동성
            fear_greed_score = await self._get_fear_greed_index()      # 공포탐욕
            altcoin_score = await self._analyze_altcoin_momentum()     # 알트코인

            # ── 3) 가중 평균으로 최종 점수 계산 ──
            # 가중치: BTC추세(30%) + 거래량(15%) + 변동성(15%) + 심리(20%) + 알트(20%)
            weights = {
                "btc_trend": 0.30,
                "volume": 0.15,
                "volatility": 0.15,
                "fear_greed": 0.20,
                "altcoin_momentum": 0.20,
            }
            final_score = (
                btc_trend_score * weights["btc_trend"]
                + volume_score * weights["volume"]
                + volatility_score * weights["volatility"]
                + fear_greed_score * weights["fear_greed"]
                + altcoin_score * weights["altcoin_momentum"]
            )
            final_score = int(round(final_score))

            # ── 4) 시장 모드 결정 ──
            if final_score >= 60:
                mode = "BULL"       # 상승장
            elif final_score >= 40:
                mode = "SIDEWAYS"   # 횡보장
            else:
                mode = "BEAR"       # 하락장

            result = {
                "mode": mode,
                "score": final_score,
                "details": {
                    "btc_trend": round(btc_trend_score, 1),
                    "volume": round(volume_score, 1),
                    "volatility": round(volatility_score, 1),
                    "fear_greed": round(fear_greed_score, 1),
                    "altcoin_momentum": round(altcoin_score, 1),
                },
                "analyzed_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"[MARKET] 시장 분석 완료: mode={mode}, score={final_score}, "
                f"details={result['details']}"
            )
            return result

        except Exception as e:
            logger.error(f"[MARKET] 시장 분석 실패: {e}")
            # 분석 실패 시 안전한 기본값 반환 (보수적)
            return {
                "mode": "UNKNOWN",
                "score": 50,
                "details": {},
                "analyzed_at": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    # ══════════════════════════════════════════════════
    # 유틸리티 — 캔들 데이터 → DataFrame 변환
    # ══════════════════════════════════════════════════

    def _candles_to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """
        업비트 캔들 응답을 pandas DataFrame으로 변환합니다.

        Args:
            candles: 업비트 API의 캔들 응답 리스트

        Returns:
            OHLCV DataFrame (시간순 정렬)
        """
        df = pd.DataFrame(candles)
        # 필요한 컬럼만 선택하고 이름 변환
        df = df.rename(columns={
            "candle_date_time_kst": "datetime",   # 한국 시간
            "opening_price": "open",               # 시가
            "high_price": "high",                  # 고가
            "low_price": "low",                    # 저가
            "trade_price": "close",                # 종가
            "candle_acc_trade_volume": "volume",    # 거래량
            "candle_acc_trade_price": "value",      # 거래대금(원)
        })
        df = df[["datetime", "open", "high", "low", "close", "volume", "value"]]
        df["datetime"] = pd.to_datetime(df["datetime"])
        # 시간순 정렬 (오래된 것이 앞)
        df = df.sort_values("datetime").reset_index(drop=True)
        return df

    # ══════════════════════════════════════════════════
    # 분석 1: BTC 추세 분석 (이동평균 크로스)
    # ══════════════════════════════════════════════════

    def _analyze_btc_trend(self, df: pd.DataFrame) -> float:
        """
        BTC 이동평균선 배열로 추세를 판단합니다.

        기준:
          - 단기(20일) > 중기(50일) > 장기(200일): 강한 상승 (80~100점)
          - 단기 > 중기, 장기 아래: 약한 상승 (60~80점)
          - 단기 < 중기 < 장기: 하락 (0~30점)
          - 그 외: 횡보 (40~60점)

        Args:
            df: BTC 일봉 OHLCV DataFrame

        Returns:
            추세 점수 (0~100)
        """
        if len(df) < 200:
            return 50.0  # 데이터 부족 시 중립

        close = df["close"]
        # 이동평균 계산
        ma20 = close.rolling(20).mean().iloc[-1]    # 20일 이동평균 (단기)
        ma50 = close.rolling(50).mean().iloc[-1]    # 50일 이동평균 (중기)
        ma200 = close.rolling(200).mean().iloc[-1]  # 200일 이동평균 (장기)
        current = close.iloc[-1]                     # 현재가

        score = 50.0  # 기본 점수 (중립)

        # ── 이동평균 정배열/역배열 판단 ──
        if current > ma20 > ma50 > ma200:
            # 완벽한 정배열: 강한 상승장
            score = 85.0
        elif current > ma20 > ma50:
            # 단기/중기 정배열
            score = 70.0
        elif current > ma20:
            # 단기 이평선 위
            score = 60.0
        elif current < ma20 < ma50 < ma200:
            # 완벽한 역배열: 강한 하락장
            score = 15.0
        elif current < ma20 < ma50:
            # 단기/중기 역배열
            score = 30.0
        elif current < ma20:
            # 단기 이평선 아래
            score = 40.0

        # ── 현재가 대비 200일 이평선 위치 가산 ──
        # 200일선 위에 있으면 가산, 아래면 감산
        ratio_200 = (current - ma200) / ma200  # 200일선 대비 비율
        score += ratio_200 * 50  # ±50% → ±25점

        # 점수 범위 제한
        return max(0.0, min(100.0, score))

    # ══════════════════════════════════════════════════
    # 분석 2: 거래량 분석
    # ══════════════════════════════════════════════════

    def _analyze_volume(self, df: pd.DataFrame) -> float:
        """
        거래대금 추세를 분석합니다.

        최근 7일 평균 거래대금 vs 30일 평균 거래대금을 비교하여
        시장 참여도 증감을 판단합니다.

        Args:
            df: BTC 일봉 OHLCV DataFrame

        Returns:
            거래량 점수 (0~100)
        """
        if len(df) < 30:
            return 50.0

        value = df["value"]  # 거래대금 (원)
        # 최근 7일 평균 vs 30일 평균
        avg_7 = value.tail(7).mean()    # 최근 7일 평균 거래대금
        avg_30 = value.tail(30).mean()  # 최근 30일 평균 거래대금

        if avg_30 == 0:
            return 50.0

        # 비율: 7일평균 / 30일평균
        ratio = avg_7 / avg_30

        # ratio > 1: 거래량 증가 (시장 활성화)
        # ratio < 1: 거래량 감소 (시장 침체)
        if ratio >= 2.0:
            return 90.0    # 거래량 2배 이상 급증
        elif ratio >= 1.5:
            return 75.0    # 거래량 50% 이상 증가
        elif ratio >= 1.1:
            return 60.0    # 약간 증가
        elif ratio >= 0.8:
            return 50.0    # 비슷한 수준
        elif ratio >= 0.5:
            return 35.0    # 감소
        else:
            return 20.0    # 급감

    # ══════════════════════════════════════════════════
    # 분석 3: 변동성 분석 (ATR + 볼린저 밴드)
    # ══════════════════════════════════════════════════

    def _analyze_volatility(self, df: pd.DataFrame) -> float:
        """
        시장 변동성을 분석합니다.

        적당한 변동성 = 매매 기회 (높은 점수)
        너무 높거나 낮은 변동성 = 위험하거나 기회 부족 (낮은 점수)

        지표:
          - ATR(14): Average True Range
          - 볼린저 밴드 폭 (Bandwidth)

        Args:
            df: BTC 일봉 OHLCV DataFrame

        Returns:
            변동성 점수 (0~100)
        """
        if len(df) < 20:
            return 50.0

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ── ATR 계산 (14일) ──
        tr_list = []
        for i in range(1, len(df)):
            # True Range = max(고가-저가, |고가-전일종가|, |저가-전일종가|)
            h_l = high.iloc[i] - low.iloc[i]
            h_pc = abs(high.iloc[i] - close.iloc[i - 1])
            l_pc = abs(low.iloc[i] - close.iloc[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))

        atr_14 = np.mean(tr_list[-14:])  # 14일 ATR
        atr_pct = (atr_14 / close.iloc[-1]) * 100  # ATR을 현재가 대비 %로 변환

        # ── 볼린저 밴드 폭 (Bandwidth) ──
        ma20 = close.rolling(20).mean().iloc[-1]
        std20 = close.rolling(20).std().iloc[-1]
        bb_width = (std20 * 4) / ma20 * 100  # 볼린저 밴드 폭 (%)

        # ── 변동성 점수 ──
        # 적당한 변동성(ATR 2~5%)이 높은 점수
        if 2.0 <= atr_pct <= 5.0:
            score = 70.0  # 적당한 변동성 → 매매 기회 좋음
        elif 1.0 <= atr_pct < 2.0:
            score = 55.0  # 낮은 변동성 → 기회 적음
        elif 5.0 < atr_pct <= 8.0:
            score = 50.0  # 높은 변동성 → 주의 필요
        elif atr_pct < 1.0:
            score = 40.0  # 매우 낮은 변동성
        else:
            score = 30.0  # 매우 높은 변동성 → 위험

        return score

    # ══════════════════════════════════════════════════
    # 분석 4: 공포탐욕 지수 (Fear & Greed Index)
    # ══════════════════════════════════════════════════

    async def _get_fear_greed_index(self) -> float:
        """
        암호화폐 공포탐욕 지수를 external API에서 가져옵니다.

        공포탐욕 지수 (0~100):
          - 0~25: 극도의 공포 (Extreme Fear) → 매수 기회
          - 25~45: 공포 (Fear)
          - 45~55: 중립 (Neutral)
          - 55~75: 탐욕 (Greed)
          - 75~100: 극도의 탐욕 (Extreme Greed) → 매도 고려

        Returns:
            시장 심리 점수 (0~100, 높을수록 긍정적)
        """
        try:
            import httpx
            # Alternative.me의 공포탐욕 지수 API
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    "https://api.alternative.me/fng/?limit=1",
                    timeout=10.0,
                )
                data = resp.json()
                fng_value = int(data["data"][0]["value"])

            # 공포탐욕 지수를 투자 적합성 점수로 변환
            # 극도의 공포(0~25)는 역발상 매수 기회 → 높은 점수
            # 극도의 탐욕(75~100)은 과열 → 낮은 점수
            if fng_value <= 25:
                return 75.0   # 극도의 공포 → 역발상 매수 기회
            elif fng_value <= 45:
                return 60.0   # 공포 → 매수 고려
            elif fng_value <= 55:
                return 50.0   # 중립
            elif fng_value <= 75:
                return 45.0   # 탐욕 → 주의
            else:
                return 30.0   # 극도의 탐욕 → 과열 경고

        except Exception as e:
            logger.warning(f"[MARKET] 공포탐욕 지수 조회 실패: {e}")
            return 50.0  # 조회 실패 시 중립값

    # ══════════════════════════════════════════════════
    # 분석 5: 알트코인 모멘텀
    # ══════════════════════════════════════════════════

    async def _analyze_altcoin_momentum(self) -> float:
        """
        상위 알트코인의 24시간 등락률을 분석하여
        전체 시장 모멘텀을 판단합니다.

        KRW 마켓 상위 20개 코인의 24시간 변동률을 분석합니다.

        Returns:
            알트코인 모멘텀 점수 (0~100)
        """
        try:
            # KRW 마켓 목록 조회
            markets = await self.client.get_market_list()
            market_codes = [m["market"] for m in markets[:20]]  # 상위 20개

            if not market_codes:
                return 50.0

            # 현재가 정보 조회
            tickers = await self.client.get_ticker(market_codes)

            # 24시간 등락률 수집
            change_rates = []
            for t in tickers:
                rate = t.get("signed_change_rate", 0) * 100  # % 변환
                change_rates.append(rate)

            if not change_rates:
                return 50.0

            # 통계 분석
            avg_change = np.mean(change_rates)          # 평균 등락률
            positive_count = sum(1 for r in change_rates if r > 0)  # 상승 코인 수
            positive_ratio = positive_count / len(change_rates)      # 상승 비율

            # ── 점수 계산 ──
            score = 50.0  # 기본 중립

            # 평균 등락률 반영 (±10% → ±30점)
            score += avg_change * 3.0

            # 상승 비율 반영 (80%이상 상승 → +15점, 20%이하 → -15점)
            score += (positive_ratio - 0.5) * 30

            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.warning(f"[MARKET] 알트코인 모멘텀 분석 실패: {e}")
            return 50.0
