"""
============================================================
리스크 관리 모듈 (Risk Manager)
포지션별 손절/익절/트레일링 스탑을 관리하고,
전체 포트폴리오 리스크를 통제합니다.

핵심 기능:
  1. ATR 기반 동적 손절가 계산
  2. 3단계 분할 익절 (TP1: +7%, TP2: +15%, TP3: +25%)
  3. 트레일링 스탑 (15% 수익 후 활성화, 최고점 대비 5% 하락 시 청산)
  4. 일일 최대 손실 한도 (-3%)
  5. 연속 손실 시 투자금 자동 축소

리스크 파라미터 (기본값):
  - 최대 투자 비율: 50%
  - 최대 동시 보유: 7코인
  - ATR 배수: 1.5배
  - 손절 범위: 1.5% ~ 5.0%
  - 트레일링 스탑 활성화: +15%
  - 트레일링 스탑 폭: 5%
============================================================
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class RiskDecision:
    """
    리스크 관리 의사결정 결과.

    Attributes:
        action: "HOLD" (유지), "STOP_LOSS" (손절), "TAKE_PROFIT" (익절),
                "TRAILING_STOP" (트레일링 스탑)
        reason: 의사결정 근거
        price: 실행 가격 (해당 시)
        quantity_ratio: 매도 수량 비율 (0.0 ~ 1.0, 분할 익절 시 부분 매도)
    """
    action: str          # "HOLD" | "STOP_LOSS" | "TAKE_PROFIT" | "TRAILING_STOP"
    reason: str          # 의사결정 근거
    price: Optional[float] = None    # 실행 가격
    quantity_ratio: float = 1.0      # 매도 비율 (1.0 = 전량, 0.33 = 1/3)


class RiskManager:
    """
    리스크 관리자.

    포지션별 손절/익절/트레일링 스탑을 계산하고,
    포트폴리오 전체의 리스크 한도를 통제합니다.

    사용법:
        rm = RiskManager(config)
        # 진입 시 투자금 계산
        amount = rm.calculate_position_size(balance, atr, price, market_mode)
        # 포지션 모니터링
        decision = rm.check_position(position, current_price)
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: 봇 설정 딕셔너리 (BotConfigRequest 참고)
        """
        # ─── 투자 비율 ───
        self.max_investment_ratio = config.get("max_investment_ratio", 0.5)
        self.max_coins = config.get("max_coins", 7)

        # ─── ATR 손절 ───
        self.atr_multiplier = config.get("atr_multiplier", 1.5)
        self.min_stop_loss_pct = config.get("min_stop_loss_pct", 1.5)
        self.max_stop_loss_pct = config.get("max_stop_loss_pct", 5.0)

        # ─── 트레일링 스탑 ───
        self.trailing_stop_activation_pct = config.get(
            "trailing_stop_activation_pct", 15.0
        )
        self.trailing_stop_distance_pct = config.get(
            "trailing_stop_distance_pct", 5.0
        )

        # ─── 분할 익절 비율 (3단계) ───
        self.tp_levels = [
            {"pct": 7.0,  "sell_ratio": 0.33, "label": "TP1"},  # +7%에서 1/3 익절
            {"pct": 15.0, "sell_ratio": 0.33, "label": "TP2"},  # +15%에서 1/3 익절
            {"pct": 25.0, "sell_ratio": 0.34, "label": "TP3"},  # +25%에서 나머지 전량 익절
        ]

        # ─── 일일 최대 손실 ───
        self.daily_max_loss_pct = -3.0  # 일일 최대 손실률 (-3%)

        # ─── 연속 손실 보호 ───
        self.consecutive_loss_threshold = 3  # 3연속 손실 시 투자금 축소
        self.loss_reduction_ratio = 0.5       # 투자금 50% 축소

    # ══════════════════════════════════════════════════
    # 진입 시 — 포지션 크기 계산
    # ══════════════════════════════════════════════════

    def calculate_position_size(
        self,
        available_balance: float,
        atr: float,
        entry_price: float,
        market_mode: str,
        current_positions: int = 0,
        consecutive_losses: int = 0,
    ) -> Dict:
        """
        신규 진입 시 적정 투자금(포지션 크기)을 계산합니다.

        계산 로직:
          1. 시장 모드별 최대 투자 비율 결정
          2. 잔여 슬롯 확인 (최대 동시 보유 코인 수)
          3. 연속 손실 시 투자금 축소
          4. 최종 투자금 = 가용잔고 × 비율 / 잔여 슬롯

        Args:
            available_balance: 가용 잔고 (KRW)
            atr: 현재 ATR 값
            entry_price: 진입 예상 가격
            market_mode: 시장 모드 ("BULL", "SIDEWAYS", "BEAR")
            current_positions: 현재 보유 포지션 수
            consecutive_losses: 연속 손실 횟수

        Returns:
            {
                "invest_amount": float,    # 투자금 (KRW)
                "stop_loss_price": float,  # 손절가
                "stop_loss_pct": float,    # 손절률 (%)
                "can_enter": bool,         # 진입 가능 여부
                "reason": str,             # 불가 사유 (있을 경우)
            }
        """
        # ── 1) 잔여 슬롯 확인 ──
        remaining_slots = self.max_coins - current_positions
        if remaining_slots <= 0:
            return {
                "invest_amount": 0,
                "stop_loss_price": 0,
                "stop_loss_pct": 0,
                "can_enter": False,
                "reason": f"최대 보유 코인 수 초과 ({self.max_coins}개)",
            }

        # ── 2) 시장 모드별 투자 비율 ──
        mode_ratio = {
            "BULL": self.max_investment_ratio,           # 상승장: 최대 50%
            "SIDEWAYS": self.max_investment_ratio * 0.6,  # 횡보장: 최대 30%
            "BEAR": self.max_investment_ratio * 0.3,      # 하락장: 최대 15%
        }
        invest_ratio = mode_ratio.get(market_mode, self.max_investment_ratio * 0.6)

        # ── 3) 연속 손실 시 투자금 축소 ──
        if consecutive_losses >= self.consecutive_loss_threshold:
            invest_ratio *= self.loss_reduction_ratio
            logger.warning(
                f"[RISK] 연속 {consecutive_losses}회 손실 → "
                f"투자금 {self.loss_reduction_ratio*100:.0f}% 축소"
            )

        # ── 4) 슬롯당 투자금 계산 ──
        total_investable = available_balance * invest_ratio
        invest_amount = total_investable / remaining_slots

        # 최소 투자금 확인 (업비트 최소 주문: 5,000원)
        if invest_amount < 5000:
            return {
                "invest_amount": 0,
                "stop_loss_price": 0,
                "stop_loss_pct": 0,
                "can_enter": False,
                "reason": "투자금 부족 (최소 5,000원 미만)",
            }

        # ── 5) ATR 기반 손절가 계산 ──
        stop_loss_price, stop_loss_pct = self._calculate_stop_loss(
            entry_price, atr
        )

        return {
            "invest_amount": round(invest_amount),
            "stop_loss_price": round(stop_loss_price),
            "stop_loss_pct": round(stop_loss_pct, 2),
            "can_enter": True,
            "reason": "진입 가능",
        }

    # ══════════════════════════════════════════════════
    # 포지션 모니터링 — 손절/익절/트레일링 체크
    # ══════════════════════════════════════════════════

    def check_position(
        self,
        position: Dict,
        current_price: float,
    ) -> RiskDecision:
        """
        보유 포지션의 리스크 상태를 점검합니다.

        체크 순서:
          1. 손절가 도달 여부
          2. 분할 익절 레벨 도달 여부
          3. 트레일링 스탑 조건 확인

        Args:
            position: 포지션 정보 딕셔너리
                - avg_entry_price: 평균 진입가
                - stop_loss_price: 손절가
                - highest_price: 보유 기간 중 최고가
                - trailing_stop_active: 트레일링 스탑 활성화 여부
                - tp1_filled, tp2_filled, tp3_filled: 익절 체결 여부
            current_price: 현재 시장가

        Returns:
            RiskDecision 객체
        """
        entry_price = position["avg_entry_price"]
        stop_loss = position["stop_loss_price"]
        highest = position.get("highest_price", entry_price)

        # 현재 손익률 계산 (%)
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        # ── 1) 손절 체크 ──
        if current_price <= stop_loss:
            return RiskDecision(
                action="STOP_LOSS",
                reason=f"손절가 도달 (현재가 {current_price:,.0f} ≤ 손절가 {stop_loss:,.0f})",
                price=current_price,
                quantity_ratio=1.0,  # 전량 손절
            )

        # ── 2) 분할 익절 체크 (TP1 → TP2 → TP3) ──
        for tp in self.tp_levels:
            tp_label = tp["label"]
            tp_pct = tp["pct"]
            filled_key = f"{tp_label.lower()}_filled"

            # 이미 체결된 익절 레벨은 건너뜀
            if position.get(filled_key, False):
                continue

            if pnl_pct >= tp_pct:
                return RiskDecision(
                    action="TAKE_PROFIT",
                    reason=(
                        f"{tp_label} 익절 도달 "
                        f"(수익률 {pnl_pct:.1f}% ≥ 목표 {tp_pct}%)"
                    ),
                    price=current_price,
                    quantity_ratio=tp["sell_ratio"],  # 분할 매도 비율
                )

        # ── 3) 트레일링 스탑 체크 ──
        trailing_active = position.get("trailing_stop_active", False)

        if not trailing_active:
            # 트레일링 스탑 활성화 조건: 수익률 ≥ 활성화 기준
            if pnl_pct >= self.trailing_stop_activation_pct:
                logger.info(
                    f"[RISK] 트레일링 스탑 활성화: "
                    f"수익률 {pnl_pct:.1f}% ≥ {self.trailing_stop_activation_pct}%"
                )
                # 트레일링 스탑 활성화는 외부에서 position 업데이트 필요
                # 여기서는 HOLD + 활성화 플래그 반환
                return RiskDecision(
                    action="HOLD",
                    reason=f"트레일링 스탑 활성화됨 (수익률 {pnl_pct:.1f}%)",
                )
        else:
            # 트레일링 스탑이 활성화된 상태에서:
            # 최고점 대비 하락률이 기준 이상이면 청산
            if highest > 0:
                drawdown_pct = ((highest - current_price) / highest) * 100
                if drawdown_pct >= self.trailing_stop_distance_pct:
                    return RiskDecision(
                        action="TRAILING_STOP",
                        reason=(
                            f"트레일링 스탑 발동 "
                            f"(최고가 {highest:,.0f} → 현재 {current_price:,.0f}, "
                            f"하락 {drawdown_pct:.1f}%)"
                        ),
                        price=current_price,
                        quantity_ratio=1.0,  # 전량 청산
                    )

        # ── 4) 정상 보유 중 ──
        return RiskDecision(
            action="HOLD",
            reason=f"정상 보유 (손익률 {pnl_pct:.1f}%)",
        )

    # ══════════════════════════════════════════════════
    # 일일 손실 한도 체크
    # ══════════════════════════════════════════════════

    def check_daily_loss_limit(self, daily_pnl_pct: float) -> bool:
        """
        일일 최대 손실 한도를 초과했는지 확인합니다.

        일일 -3% 손실 시 당일 신규 진입을 차단합니다.

        Args:
            daily_pnl_pct: 당일 누적 손익률 (%)

        Returns:
            True = 한도 초과 (진입 차단), False = 정상
        """
        if daily_pnl_pct <= self.daily_max_loss_pct:
            logger.warning(
                f"[RISK] 일일 최대 손실 한도 도달! "
                f"({daily_pnl_pct:.1f}% ≤ {self.daily_max_loss_pct}%)"
            )
            return True
        return False

    # ══════════════════════════════════════════════════
    # 내부 — ATR 기반 손절가 계산
    # ══════════════════════════════════════════════════

    def _calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
    ) -> Tuple[float, float]:
        """
        ATR 기반 동적 손절가를 계산합니다.

        손절 폭 = ATR × 배수 (기본 1.5배)
        최소/최대 손절률 범위 내로 클리핑합니다.

        Args:
            entry_price: 진입 가격
            atr: ATR 값

        Returns:
            (손절가, 손절률%) 튜플
        """
        # ATR 기반 손절 폭
        stop_distance = atr * self.atr_multiplier
        stop_loss_pct = (stop_distance / entry_price) * 100

        # 최소/최대 범위 클리핑
        stop_loss_pct = max(self.min_stop_loss_pct, min(self.max_stop_loss_pct, stop_loss_pct))

        # 손절가 계산
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)

        return stop_loss_price, stop_loss_pct
