"""
============================================================
포지션 모델 (Position)
현재 보유 중인 코인 포지션을 관리합니다.

v3.0 설계 반영:
  - ATR 기반 동적 손절선 저장
  - 트레일링 스탑 상태 관리 (활성 여부, 최고가 기록)
  - 횡보장 포지션과 상승장 포지션 구분
  - 분할 진입/청산 단계 추적
============================================================
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey,
    DateTime, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class PositionType(str, enum.Enum):
    """포지션 유형 — 어떤 전략으로 진입했는지 구분"""
    BULL_TREND = "bull_trend"       # 상승장 추세 추종
    SIDEWAYS_REVERT = "sideways_revert"  # 횡보장 평균회귀


class Position(Base):
    """
    보유 포지션 테이블.

    현재 보유 중인 각 코인의 상태를 실시간으로 추적합니다.
    매수 완료 시 생성, 전량 매도 시 삭제(또는 is_closed=True).

    컬럼 설명:
    - coin: 코인 심볼 (예: "KRW-BTC")
    - position_type: 포지션 유형 (상승장/횡보장)
    - avg_entry_price: 분할 진입 평균 단가
    - total_quantity: 현재 보유 수량 (분할 청산으로 감소 가능)
    - total_invested: 총 투자 금액 (원화)
    - entry_count: 분할 진입 완료 횟수 (1~3)
    - current_pnl_pct: 현재 평가 손익률 (%, 실시간 업데이트)

    [손절 관련]
    - stop_loss_price: ATR 기반 동적 손절 가격
    - stop_loss_pct: 손절 비율 (%)
    - atr_at_entry: 진입 시점 ATR(14) 값 (손절 계산 기준)

    [익절 관련]
    - take_profit_1_price: 1차 익절 가격 (+5%)
    - take_profit_2_price: 2차 익절 가격 (+10%)
    - take_profit_3_price: 3차 익절 가격 (+15%)
    - tp1_filled / tp2_filled / tp3_filled: 각 단계 청산 완료 여부

    [트레일링 스탑]
    - trailing_stop_active: 트레일링 스탑 활성화 여부
    - highest_price: 진입 이후 최고가 (트레일링 기준점)
    - trailing_stop_price: 현재 트레일링 스탑 가격

    [시장 정보]
    - entry_market_score: 진입 시점 시장 국면 점수 (시간 손절 판단용)
    """
    __tablename__ = "positions"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bot_id = Column(
        Integer,
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ─── 코인 정보 ───
    coin = Column(String(30), nullable=False, index=True)
    position_type = Column(
        Enum(PositionType),
        default=PositionType.BULL_TREND,
        nullable=False,
    )

    # ─── 진입 정보 ───
    avg_entry_price = Column(Float, nullable=False)  # 분할 진입 평균 단가
    total_quantity = Column(Float, nullable=False)  # 현재 보유 수량
    total_invested = Column(Float, nullable=False)  # 총 투자 금액 (원화)
    entry_count = Column(Integer, default=1)  # 분할 진입 횟수 (1~3)
    is_closed = Column(Boolean, default=False, index=True)  # 청산 완료 여부

    # ─── 현재 평가 ───
    current_price = Column(Float, nullable=True)  # 현재 가격 (실시간 업데이트)
    current_pnl_pct = Column(Float, default=0.0)  # 현재 손익률 (%)
    current_pnl_amount = Column(Float, default=0.0)  # 현재 손익 금액 (원화)

    # ─── ATR 기반 동적 손절 ───
    atr_at_entry = Column(Float, nullable=True)  # 진입 시점 ATR(14) 값
    stop_loss_price = Column(Float, nullable=True)  # 손절 가격
    stop_loss_pct = Column(Float, nullable=True)  # 손절 비율 (%)

    # ─── 분할 익절 가격 ───
    take_profit_1_price = Column(Float, nullable=True)  # +5%
    take_profit_2_price = Column(Float, nullable=True)  # +10%
    take_profit_3_price = Column(Float, nullable=True)  # +15%
    tp1_filled = Column(Boolean, default=False)  # 1차 익절 완료
    tp2_filled = Column(Boolean, default=False)  # 2차 익절 완료
    tp3_filled = Column(Boolean, default=False)  # 3차 익절 완료

    # ─── 트레일링 스탑 ───
    trailing_stop_active = Column(Boolean, default=False)  # 활성화 여부
    highest_price = Column(Float, nullable=True)  # 진입 이후 최고가
    trailing_stop_price = Column(Float, nullable=True)  # 트레일링 스탑 가격

    # ─── 시장 상태 (진입 시점 기록) ───
    entry_market_score = Column(Integer, nullable=True)  # 진입 시 국면 점수
    entry_market_mode = Column(String(20), nullable=True)  # 진입 시 모드

    # ─── 횡보장 전용 필드 ───
    bollinger_mid_price = Column(Float, nullable=True)  # 볼린저 중간선 (횡보장 익절 기준)
    bollinger_upper_price = Column(Float, nullable=True)  # 볼린저 상단 (횡보장 익절 기준)

    # ─── 타임스탬프 ───
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # 포지션 개시 시각
    closed_at = Column(DateTime, nullable=True)  # 포지션 종료 시각
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ─── 관계 ───
    bot = relationship("Bot", back_populates="positions")
    user = relationship("User", back_populates="positions")

    def __repr__(self):
        return (
            f"<Position(id={self.id}, coin='{self.coin}', "
            f"qty={self.total_quantity}, pnl={self.current_pnl_pct}%)>"
        )
