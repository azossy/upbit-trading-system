"""
============================================================
거래 기록 모델 (Trade)
모든 매수/매도 주문의 체결 기록을 저장합니다.
수수료, 슬리피지, 실제 손익까지 추적합니다.

v3.0 설계 반영:
  - 수수료 + 슬리피지 실제 손익비 기록
  - ATR 기반 동적 손절선 기록
  - 트레일링 스탑 관련 정보 기록
============================================================
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class TradeSide(str, enum.Enum):
    """매수/매도 구분"""
    BUY = "buy"    # 매수
    SELL = "sell"  # 매도


class OrderType(str, enum.Enum):
    """주문 유형"""
    MARKET = "market"  # 시장가 (즉시 체결)
    LIMIT = "limit"    # 지정가


class TradeReason(str, enum.Enum):
    """
    거래 사유 — 어떤 로직에 의해 발생한 거래인지 추적.
    백테스팅 및 전략 개선 시 매우 유용한 데이터.
    """
    # ─── 매수 사유 ───
    ENTRY_1ST = "entry_1st"          # 1차 분할 매수 (40%)
    ENTRY_2ND = "entry_2nd"          # 2차 분할 매수 (35%)
    ENTRY_3RD = "entry_3rd"          # 3차 분할 매수 (25%)
    SIDEWAYS_ENTRY_1ST = "sideways_entry_1st"  # 횡보장 1차 매수 (50%)
    SIDEWAYS_ENTRY_2ND = "sideways_entry_2nd"  # 횡보장 2차 매수 (50%)

    # ─── 매도(익절) 사유 ───
    TAKE_PROFIT_1ST = "take_profit_1st"    # 1차 익절 +5% (30%)
    TAKE_PROFIT_2ND = "take_profit_2nd"    # 2차 익절 +10% (30%)
    TAKE_PROFIT_3RD = "take_profit_3rd"    # 3차 익절 +15% (20%)
    TRAILING_STOP = "trailing_stop"        # 트레일링 스탑 청산 (20%)
    SIDEWAYS_TP_MID = "sideways_tp_mid"    # 횡보장 중간선 익절
    SIDEWAYS_TP_UPPER = "sideways_tp_upper"  # 횡보장 상단 익절
    SIDEWAYS_RSI_EXIT = "sideways_rsi_exit"  # 횡보장 RSI 익절

    # ─── 매도(손절) 사유 ───
    STOP_LOSS_ATR = "stop_loss_atr"        # ATR 기반 동적 손절
    STOP_LOSS_SIGNAL = "stop_loss_signal"  # 신호 손절 (데드크로스)
    STOP_LOSS_MODE = "stop_loss_mode"      # 국면 손절 (하락 전환)
    STOP_LOSS_TIME = "stop_loss_time"      # 시간 손절 (12시간 경과)
    SIDEWAYS_STOP = "sideways_stop"        # 횡보장 손절 (-1.5%)

    # ─── 기타 ───
    KILL_SWITCH = "kill_switch"      # 긴급 정지
    MANUAL = "manual"                # 수동 거래
    SECTOR_ROTATION = "sector_rotation"  # 섹터 로테이션 교체
    CANCEL = "cancel"                # 미체결 취소


class Trade(Base):
    """
    거래 기록 테이블.

    모든 매수/매도 체결 내역을 기록하며, 수수료와 슬리피지를 포함한
    실제 손익을 추적합니다.

    컬럼 설명:
    - coin: 거래 코인 심볼 (예: "KRW-BTC", "KRW-ETH")
    - side: 매수(buy) / 매도(sell)
    - order_type: 시장가(market) / 지정가(limit)
    - reason: 거래 발생 사유 (진입/익절/손절/트레일링 등)
    - price: 체결 가격 (원화)
    - quantity: 체결 수량
    - total_amount: 총 거래 금액 (price × quantity)
    - fee: 수수료 (원화, 업비트 0.05%)
    - slippage: 슬리피지 (예상가 대비 실제 체결가 차이, %)
    - realized_pnl: 이 거래로 인한 실현 손익 (매도 시에만, 원화)
    - realized_pnl_pct: 실현 손익률 (%, 수수료+슬리피지 포함 실제 기준)
    """
    __tablename__ = "trades"

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

    # ─── 거래 정보 ───
    coin = Column(String(30), nullable=False, index=True)  # 코인 심볼 (예: KRW-BTC)
    side = Column(Enum(TradeSide), nullable=False)  # 매수/매도
    order_type = Column(Enum(OrderType), nullable=False)  # 시장가/지정가
    reason = Column(Enum(TradeReason), nullable=False)  # 거래 사유

    # ─── 가격/수량 ───
    price = Column(Float, nullable=False)  # 체결 가격 (원화)
    quantity = Column(Float, nullable=False)  # 체결 수량
    total_amount = Column(Float, nullable=False)  # 총 금액 (price × quantity)

    # ─── 비용 ───
    fee = Column(Float, default=0.0)  # 수수료 (원화)
    slippage = Column(Float, default=0.0)  # 슬리피지 (%, 양수 = 불리한 방향)

    # ─── 손익 (매도 시에만 기록) ───
    realized_pnl = Column(Float, nullable=True)  # 실현 손익 (원화)
    realized_pnl_pct = Column(Float, nullable=True)  # 실현 손익률 (%, 수수료 포함)

    # ─── 업비트 주문 ID (체결 확인 및 추적용) ───
    upbit_order_id = Column(String(100), nullable=True, index=True)

    # ─── 메모 ───
    note = Column(Text, nullable=True)  # 추가 메모 (예: "강제 교체", "Kill Switch 발동")

    # ─── 타임스탬프 ───
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # ─── 관계 ───
    bot = relationship("Bot", back_populates="trades")
    user = relationship("User", back_populates="trades")

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, coin='{self.coin}', side='{self.side}', "
            f"price={self.price}, quantity={self.quantity})>"
        )
