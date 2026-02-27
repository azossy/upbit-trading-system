"""
============================================================
통합 전략 엔진 (Strategy Engine)
시장 분석 → 코인 스캐닝 → 신호 생성 → 주문 실행 → 리스크 관리
전체 파이프라인을 하나의 사이클로 통합합니다.

실행 주기: 15분마다 1사이클
  1단계: 시장 상황 분석 (MarketAnalyzer)
  2단계: KRW 마켓 전체 코인 스캐닝 (SignalGenerator)
  3단계: 매수 신호 발생 코인에 주문 실행 (OrderExecutor)
  4단계: 기존 보유 포지션 리스크 점검 (RiskManager)
  5단계: 손절/익절/트레일링 스탑 실행

Celery 태스크로 비동기 실행되며,
봇 상태가 RUNNING일 때만 사이클을 반복합니다.
============================================================
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from app.trading.upbit_client import UpbitClient
from app.trading.market_analyzer import MarketAnalyzer
from app.trading.signal_generator import SignalGenerator, Signal
from app.trading.order_executor import OrderExecutor
from app.trading.risk_manager import RiskManager, RiskDecision


class TradingStrategy:
    """
    통합 트레이딩 전략 엔진.

    모든 하위 모듈(분석, 신호, 주문, 리스크)을 조합하여
    하나의 트레이딩 사이클을 실행합니다.

    사용법:
        strategy = TradingStrategy(
            access_key="...",
            secret_key="...",
            bot_config={...},
        )
        await strategy.run_cycle()
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bot_config: Dict,
        user_id: int = 0,
    ):
        """
        Args:
            access_key: 업비트 API Access Key (복호화된 원문)
            secret_key: 업비트 API Secret Key (복호화된 원문)
            bot_config: 봇 설정 딕셔너리
            user_id: 사용자 ID (DB 기록용)
        """
        # ─── 업비트 API 클라이언트 ───
        self.client = UpbitClient(access_key, secret_key)

        # ─── 하위 모듈 초기화 ───
        self.analyzer = MarketAnalyzer(self.client)       # 시장 분석
        self.signal_gen = SignalGenerator()                 # 신호 생성
        self.executor = OrderExecutor(self.client)          # 주문 실행
        self.risk_mgr = RiskManager(bot_config)             # 리스크 관리

        # ─── 상태 변수 ───
        self.user_id = user_id
        self.bot_config = bot_config
        self.current_market_mode = "UNKNOWN"   # 현재 시장 모드
        self.current_market_score = 50         # 현재 시장 점수
        self.is_running = False                # 봇 실행 상태 플래그

        # ─── 사이클 간격 (초) ───
        self.cycle_interval = 15 * 60  # 15분 = 900초

    # ══════════════════════════════════════════════════
    # 메인 루프 — 봇 실행
    # ══════════════════════════════════════════════════

    async def start(self):
        """
        트레이딩 봇을 시작합니다.
        stop()이 호출될 때까지 cycle_interval 간격으로 반복 실행됩니다.
        """
        self.is_running = True
        logger.info(f"[STRATEGY] 트레이딩 봇 시작 (user_id={self.user_id})")

        while self.is_running:
            try:
                # 1 사이클 실행
                await self.run_cycle()
            except Exception as e:
                logger.error(f"[STRATEGY] 사이클 실행 오류: {e}")

            # 다음 사이클까지 대기
            if self.is_running:
                logger.info(
                    f"[STRATEGY] 다음 사이클까지 {self.cycle_interval}초 대기..."
                )
                await asyncio.sleep(self.cycle_interval)

        logger.info(f"[STRATEGY] 트레이딩 봇 종료 (user_id={self.user_id})")

    async def stop(self):
        """
        트레이딩 봇을 정지합니다.
        현재 사이클이 완료된 후 루프가 종료됩니다.
        미체결 주문도 모두 취소합니다.
        """
        self.is_running = False
        # 미체결 주문 전체 취소 (안전 조치)
        await self.executor.cancel_all_orders()
        logger.info("[STRATEGY] 봇 정지 요청됨 — 미체결 주문 취소 완료")

    # ══════════════════════════════════════════════════
    # 1 사이클 실행
    # ══════════════════════════════════════════════════

    async def run_cycle(self):
        """
        트레이딩 1 사이클을 실행합니다.

        파이프라인:
          1. 시장 상황 분석
          2. 기존 포지션 리스크 점검 (손절/익절 실행)
          3. 신규 매수 기회 스캐닝
          4. 매수 신호 발생 시 주문 실행
        """
        cycle_start = datetime.utcnow()
        logger.info("=" * 50)
        logger.info(f"[CYCLE] 트레이딩 사이클 시작: {cycle_start.isoformat()}")

        # ─── 1단계: 시장 상황 분석 ───
        market = await self.analyzer.analyze()
        self.current_market_mode = market["mode"]
        self.current_market_score = market["score"]
        logger.info(
            f"[CYCLE] 시장 분석: mode={market['mode']}, "
            f"score={market['score']}"
        )

        # ─── 2단계: 기존 포지션 리스크 점검 ───
        await self._check_existing_positions()

        # ─── 3단계: 신규 매수 기회 스캐닝 ───
        # 하락장에서는 신규 진입을 매우 보수적으로
        if market["mode"] == "BEAR" and market["score"] < 30:
            logger.info("[CYCLE] 하락장 — 신규 진입 스킵")
        else:
            await self._scan_and_enter()

        elapsed = (datetime.utcnow() - cycle_start).total_seconds()
        logger.info(f"[CYCLE] 사이클 완료: {elapsed:.1f}초 소요")
        logger.info("=" * 50)

    # ══════════════════════════════════════════════════
    # 2단계: 기존 포지션 리스크 점검
    # ══════════════════════════════════════════════════

    async def _check_existing_positions(self):
        """
        기존 보유 포지션의 리스크 상태를 점검하고,
        손절/익절/트레일링 스탑 조건이 충족되면 매도를 실행합니다.
        """
        try:
            # 업비트 잔고에서 보유 코인 목록 조회
            accounts = await self.client.get_accounts()
            coin_holdings = [
                acc for acc in accounts
                if acc["currency"] != "KRW" and float(acc.get("balance", 0)) > 0
            ]

            if not coin_holdings:
                logger.info("[RISK] 보유 포지션 없음")
                return

            for holding in coin_holdings:
                currency = holding["currency"]
                market = f"KRW-{currency}"
                balance = float(holding.get("balance", 0))
                avg_price = float(holding.get("avg_buy_price", 0))

                if balance <= 0 or avg_price <= 0:
                    continue

                # 현재가 조회
                try:
                    tickers = await self.client.get_ticker([market])
                    if not tickers:
                        continue
                    current_price = tickers[0]["trade_price"]
                except Exception:
                    continue

                # 간이 포지션 정보 구성 (DB 포지션 데이터와 매핑)
                position_info = {
                    "avg_entry_price": avg_price,
                    "stop_loss_price": avg_price * (1 - self.risk_mgr.min_stop_loss_pct / 100),
                    "highest_price": max(avg_price, current_price),
                    "trailing_stop_active": False,
                    "tp1_filled": False,
                    "tp2_filled": False,
                    "tp3_filled": False,
                    "total_quantity": balance,
                }

                # 리스크 체크
                decision: RiskDecision = self.risk_mgr.check_position(
                    position_info, current_price
                )

                # 의사결정에 따른 실행
                if decision.action in ("STOP_LOSS", "TRAILING_STOP"):
                    # 전량 매도 (손절 또는 트레일링 스탑)
                    logger.warning(
                        f"[RISK] {decision.action}: {market} — {decision.reason}"
                    )
                    await self.executor.sell_market(market, balance)

                elif decision.action == "TAKE_PROFIT":
                    # 분할 매도 (익절)
                    logger.info(
                        f"[RISK] {decision.action}: {market} — {decision.reason}"
                    )
                    await self.executor.sell_partial(
                        market, balance, decision.quantity_ratio
                    )

                else:
                    # HOLD — 유지
                    pnl_pct = ((current_price - avg_price) / avg_price) * 100
                    logger.debug(
                        f"[RISK] HOLD: {market}, "
                        f"PnL={pnl_pct:.1f}%"
                    )

        except Exception as e:
            logger.error(f"[RISK] 포지션 점검 오류: {e}")

    # ══════════════════════════════════════════════════
    # 3단계: 신규 매수 기회 스캐닝
    # ══════════════════════════════════════════════════

    async def _scan_and_enter(self):
        """
        KRW 마켓 상위 코인을 스캐닝하여
        매수 신호 발생 시 주문을 실행합니다.
        """
        try:
            # KRW 마켓 목록 조회 (상위 20개 코인)
            markets = await self.client.get_market_list()
            target_markets = [m["market"] for m in markets[:20]]

            # 가용 잔고 조회
            krw_balance = await self.client.get_krw_balance()
            logger.info(f"[SCAN] 가용 잔고: {krw_balance:,.0f}원")

            # 현재 보유 포지션 수 확인
            accounts = await self.client.get_accounts()
            current_positions = sum(
                1 for a in accounts
                if a["currency"] != "KRW" and float(a.get("balance", 0)) > 0
            )

            buy_signals: List[Signal] = []

            for market in target_markets:
                try:
                    # 15분봉 캔들 데이터 조회 (200개)
                    candles = await self.client.get_candles(
                        market, interval="minutes/15", count=200
                    )

                    if not candles or len(candles) < 50:
                        continue

                    # 캔들 데이터를 DataFrame으로 변환
                    df = self.analyzer._candles_to_dataframe(candles)

                    # 매매 신호 생성
                    signal = self.signal_gen.generate(
                        market, df, self.current_market_mode
                    )

                    if signal.action == "BUY":
                        buy_signals.append(signal)
                        logger.info(
                            f"[SCAN] 매수 신호: {market}, "
                            f"강도={signal.strength:.2f}, "
                            f"근거={signal.reasons}"
                        )

                except Exception as e:
                    logger.debug(f"[SCAN] {market} 분석 실패: {e}")
                    continue

            # ── 매수 신호를 강도순으로 정렬 ──
            buy_signals.sort(key=lambda s: s.strength, reverse=True)

            # ── 상위 신호부터 주문 실행 ──
            for signal in buy_signals:
                # 포지션 크기 계산
                atr = signal.indicators.get("atr", 0)
                entry_price = signal.indicators.get("current_price", 0)

                size_info = self.risk_mgr.calculate_position_size(
                    available_balance=krw_balance,
                    atr=atr,
                    entry_price=entry_price,
                    market_mode=self.current_market_mode,
                    current_positions=current_positions,
                )

                if not size_info["can_enter"]:
                    logger.info(
                        f"[SCAN] 진입 불가: {signal.coin} — {size_info['reason']}"
                    )
                    continue

                # 매수 주문 실행
                result = await self.executor.buy_market(
                    signal.coin, size_info["invest_amount"]
                )

                if result["success"]:
                    current_positions += 1
                    krw_balance -= size_info["invest_amount"]
                    logger.info(
                        f"[ENTRY] 매수 체결: {signal.coin}, "
                        f"투자금={size_info['invest_amount']:,.0f}원, "
                        f"손절가={size_info['stop_loss_price']:,.0f}"
                    )
                else:
                    logger.warning(
                        f"[ENTRY] 매수 실패: {signal.coin} — "
                        f"{result.get('error', 'unknown')}"
                    )

        except Exception as e:
            logger.error(f"[SCAN] 스캐닝 오류: {e}")
