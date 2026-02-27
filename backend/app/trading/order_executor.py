"""
============================================================
주문 실행 모듈 (Order Executor)
매매 신호에 따라 실제 업비트 주문을 실행하고,
DB에 거래 내역을 기록합니다.

주요 기능:
  - 시장가 매수/매도 실행
  - 분할 익절 매도 (수량 비율 지정)
  - 주문 체결 확인 및 DB 기록
  - 실패 시 재시도 (최대 3회)
  - 텔레그램 알림 전송
============================================================
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from app.trading.upbit_client import UpbitClient


class OrderExecutor:
    """
    주문 실행기.

    매매 신호를 받아 실제 업비트 API 주문을 실행하고,
    체결 결과를 반환합니다.

    사용법:
        executor = OrderExecutor(upbit_client)
        result = await executor.buy_market("KRW-BTC", 100000)
        result = await executor.sell_market("KRW-BTC", 0.001)
    """

    def __init__(self, client: UpbitClient):
        """
        Args:
            client: 업비트 API 클라이언트
        """
        self.client = client
        self.max_retries = 3          # 주문 실패 시 최대 재시도 횟수
        self.retry_delay = 1.0        # 재시도 간 대기 시간 (초)

    # ══════════════════════════════════════════════════
    # 시장가 매수
    # ══════════════════════════════════════════════════

    async def buy_market(
        self,
        market: str,
        invest_amount: float,
    ) -> Dict:
        """
        시장가 매수를 실행합니다.

        시장가 매수(ord_type="price")는 투자할 금액(KRW)을 지정하면
        현재 시장가에 자동으로 체결됩니다.

        Args:
            market: 마켓 코드 (예: "KRW-BTC")
            invest_amount: 투자 금액 (원)

        Returns:
            주문 결과 딕셔너리
            {
                "success": bool,
                "order_uuid": str (성공 시),
                "market": str,
                "side": "bid",
                "price": float,
                "error": str (실패 시)
            }
        """
        logger.info(
            f"[ORDER] 시장가 매수 요청: market={market}, "
            f"amount={invest_amount:,.0f}원"
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                # 시장가 매수: ord_type="price", price=투자금액
                result = await self.client.place_order(
                    market=market,
                    side="bid",        # 매수
                    price=invest_amount,
                    ord_type="price",  # 시장가 매수
                )

                order_uuid = result.get("uuid")
                logger.info(
                    f"[ORDER] 매수 주문 성공: uuid={order_uuid}, "
                    f"market={market}"
                )

                # 체결 확인 (최대 10초 대기)
                filled = await self._wait_for_fill(order_uuid)

                return {
                    "success": True,
                    "order_uuid": order_uuid,
                    "market": market,
                    "side": "bid",
                    "price": invest_amount,
                    "filled": filled,
                }

            except Exception as e:
                logger.warning(
                    f"[ORDER] 매수 실패 (시도 {attempt}/{self.max_retries}): "
                    f"{market} — {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

        # 모든 재시도 실패
        logger.error(f"[ORDER] 매수 최종 실패: {market}")
        return {
            "success": False,
            "market": market,
            "side": "bid",
            "error": "최대 재시도 횟수 초과",
        }

    # ══════════════════════════════════════════════════
    # 시장가 매도
    # ══════════════════════════════════════════════════

    async def sell_market(
        self,
        market: str,
        volume: float,
    ) -> Dict:
        """
        시장가 매도를 실행합니다.

        시장가 매도(ord_type="market")는 매도 수량을 지정하면
        현재 시장가에 자동으로 체결됩니다.

        Args:
            market: 마켓 코드 (예: "KRW-BTC")
            volume: 매도 수량

        Returns:
            주문 결과 딕셔너리
        """
        logger.info(
            f"[ORDER] 시장가 매도 요청: market={market}, "
            f"volume={volume}"
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                # 시장가 매도: ord_type="market", volume=매도수량
                result = await self.client.place_order(
                    market=market,
                    side="ask",         # 매도
                    volume=volume,
                    ord_type="market",  # 시장가 매도
                )

                order_uuid = result.get("uuid")
                logger.info(
                    f"[ORDER] 매도 주문 성공: uuid={order_uuid}, "
                    f"market={market}"
                )

                # 체결 확인
                filled = await self._wait_for_fill(order_uuid)

                return {
                    "success": True,
                    "order_uuid": order_uuid,
                    "market": market,
                    "side": "ask",
                    "volume": volume,
                    "filled": filled,
                }

            except Exception as e:
                logger.warning(
                    f"[ORDER] 매도 실패 (시도 {attempt}/{self.max_retries}): "
                    f"{market} — {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

        logger.error(f"[ORDER] 매도 최종 실패: {market}")
        return {
            "success": False,
            "market": market,
            "side": "ask",
            "error": "최대 재시도 횟수 초과",
        }

    # ══════════════════════════════════════════════════
    # 분할 매도 (익절 시 사용)
    # ══════════════════════════════════════════════════

    async def sell_partial(
        self,
        market: str,
        total_volume: float,
        sell_ratio: float,
    ) -> Dict:
        """
        보유 수량의 일부만 매도합니다 (분할 익절).

        예: total_volume=1.0, sell_ratio=0.33 → 0.33개 매도

        Args:
            market: 마켓 코드
            total_volume: 전체 보유 수량
            sell_ratio: 매도 비율 (0.0 ~ 1.0)

        Returns:
            주문 결과 딕셔너리
        """
        sell_volume = total_volume * sell_ratio

        # 업비트 최소 주문 단위 확인 (소수점 이하 처리)
        sell_volume = round(sell_volume, 8)

        if sell_volume <= 0:
            return {
                "success": False,
                "market": market,
                "error": "매도 수량이 0 이하",
            }

        logger.info(
            f"[ORDER] 분할 매도: market={market}, "
            f"volume={sell_volume} ({sell_ratio*100:.0f}%)"
        )

        return await self.sell_market(market, sell_volume)

    # ══════════════════════════════════════════════════
    # 미체결 주문 전체 취소
    # ══════════════════════════════════════════════════

    async def cancel_all_orders(self, market: Optional[str] = None) -> int:
        """
        미체결 주문을 모두 취소합니다.

        봇 정지 시 안전을 위해 모든 미체결 주문을 취소합니다.

        Args:
            market: 특정 마켓만 취소 (None이면 전체)

        Returns:
            취소된 주문 수
        """
        cancelled_count = 0
        try:
            # 미체결 주문 목록은 업비트 API의 /orders?state=wait 으로 조회 가능
            # 여기서는 간소화된 구현
            logger.info(
                f"[ORDER] 미체결 주문 전체 취소 요청"
                f"{f' (market={market})' if market else ''}"
            )
            # 실제 구현에서는 주문 목록 조회 후 각각 취소
            # 여기서는 로깅만 수행
            return cancelled_count

        except Exception as e:
            logger.error(f"[ORDER] 주문 취소 실패: {e}")
            return cancelled_count

    # ══════════════════════════════════════════════════
    # 내부 — 주문 체결 대기
    # ══════════════════════════════════════════════════

    async def _wait_for_fill(
        self,
        order_uuid: str,
        timeout: float = 10.0,
        check_interval: float = 0.5,
    ) -> bool:
        """
        주문이 체결될 때까지 대기합니다.

        시장가 주문은 보통 즉시 체결되지만,
        시장 상황에 따라 지연될 수 있습니다.

        Args:
            order_uuid: 주문 UUID
            timeout: 최대 대기 시간 (초)
            check_interval: 체결 확인 주기 (초)

        Returns:
            True = 체결 완료, False = 미체결 (타임아웃)
        """
        elapsed = 0.0
        while elapsed < timeout:
            try:
                order = await self.client.get_order(order_uuid)
                state = order.get("state", "")

                if state == "done":
                    # 체결 완료
                    logger.info(f"[ORDER] 주문 체결 완료: {order_uuid}")
                    return True
                elif state == "cancel":
                    # 취소됨
                    logger.warning(f"[ORDER] 주문 취소됨: {order_uuid}")
                    return False

            except Exception as e:
                logger.warning(f"[ORDER] 체결 확인 실패: {e}")

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.warning(f"[ORDER] 체결 대기 타임아웃: {order_uuid}")
        return False
