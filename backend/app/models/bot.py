"""
============================================================
봇 모델 (Bot, BotLog)
각 사용자의 트레이딩 봇 인스턴스와 로그를 관리합니다.
봇은 사용자당 1개만 생성 가능하며, 상태 머신으로 관리됩니다.

봇 상태 전이:
  STOPPED → RUNNING → PAUSED → RUNNING
                   → ERROR  → STOPPED
                   → STOPPED
============================================================
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text,
    Enum, JSON, Float
)
from sqlalchemy.orm import relationship
from app.database import Base


class BotStatus(str, enum.Enum):
    """
    봇 상태 정의.
    - STOPPED: 정지됨 (수동 정지 또는 초기 상태)
    - RUNNING: 실행 중 (정상 트레이딩 수행)
    - PAUSED: 일시 정지 (연속 손절 등으로 자동 정지)
    - ERROR: 오류 발생 (API 오류, 긴급 정지 등)
    - MAINTENANCE: 점검 중 (업비트 점검 대응)
    """
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MarketMode(str, enum.Enum):
    """
    시장 국면 모드 (v3.0 기준).
    트레이딩 엔진의 시장 분석 결과에 따라 자동 전환됩니다.
    """
    BULL = "bull"           # 상승장
    SIDEWAYS = "sideways"   # 횡보장
    BEAR = "bear"           # 하락장
    UNKNOWN = "unknown"     # 판단 불가 (데이터 부족)


class Bot(Base):
    """
    트레이딩 봇 인스턴스 테이블.

    각 사용자는 1개의 봇 인스턴스를 가지며, 봇의 현재 상태,
    설정, 성과 통계를 기록합니다.

    컬럼 설명:
    - status: 봇 현재 상태 (stopped/running/paused/error/maintenance)
    - market_mode: 현재 감지된 시장 국면 (bull/sideways/bear)
    - market_score: 현재 시장 국면 점수 (-9 ~ +9)
    - config: 봇 설정 JSON (투자 비율, ATR 배수 등 사용자 커스텀 설정)
    - total_pnl: 누적 실현 손익 (원화 기준)
    - total_trades: 총 거래 횟수
    - win_rate: 승률 (%)
    - consecutive_losses: 현재 연속 손절 횟수 (리스크 관리용)
    - daily_pnl: 당일 손익 (일일 손실 한도 체크용)
    - weekly_pnl: 금주 손익 (주간 손실 한도 체크용)
    - monthly_pnl: 당월 손익 (월간 손실 한도 체크용)
    """
    __tablename__ = "bots"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 사용자당 1개의 봇만 허용
        index=True,
    )

    # ─── 봇 상태 ───
    status = Column(
        Enum(BotStatus),
        default=BotStatus.STOPPED,
        nullable=False,
    )
    market_mode = Column(
        Enum(MarketMode),
        default=MarketMode.UNKNOWN,
        nullable=False,
    )
    market_score = Column(Integer, default=0)  # 시장 국면 점수 (-9 ~ +9)

    # ─── 봇 설정 (JSON) ───
    # 사용자가 커스터마이징할 수 있는 파라미터들
    # 예: {"investment_ratio": 0.5, "atr_multiplier": 1.5, "max_coins": 7}
    config = Column(JSON, default=dict, nullable=False)

    # ─── 성과 통계 ───
    total_pnl = Column(Float, default=0.0)  # 누적 실현 손익 (원화)
    total_trades = Column(Integer, default=0)  # 총 거래 횟수
    win_count = Column(Integer, default=0)  # 수익 거래 횟수
    loss_count = Column(Integer, default=0)  # 손실 거래 횟수

    # ─── 리스크 관리 카운터 ───
    consecutive_losses = Column(Integer, default=0)  # 현재 연속 손절 횟수
    daily_pnl = Column(Float, default=0.0)  # 당일 손익 (%)
    weekly_pnl = Column(Float, default=0.0)  # 금주 손익 (%)
    monthly_pnl = Column(Float, default=0.0)  # 당월 손익 (%)

    # ─── 정지 사유 (에러/일시정지 시) ───
    stop_reason = Column(Text, nullable=True)

    # ─── 타임스탬프 ───
    started_at = Column(DateTime, nullable=True)  # 마지막 시작 시간
    stopped_at = Column(DateTime, nullable=True)  # 마지막 정지 시간
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ─── 관계 ───
    user = relationship("User", back_populates="bots")
    trades = relationship("Trade", back_populates="bot", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="bot", cascade="all, delete-orphan")
    logs = relationship("BotLog", back_populates="bot", cascade="all, delete-orphan")

    @property
    def win_rate(self) -> float:
        """승률 계산 (%)"""
        total = self.win_count + self.loss_count
        if total == 0:
            return 0.0
        return round((self.win_count / total) * 100, 2)

    def __repr__(self):
        return f"<Bot(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class BotLog(Base):
    """
    봇 로그 테이블.
    트레이딩 엔진의 주요 이벤트를 기록합니다.
    (매수/매도 신호, 모드 전환, 에러 등)

    컬럼 설명:
    - level: 로그 레벨 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - module: 발생 모듈 (engine/market_analyzer/entry_logic 등)
    - message: 로그 메시지
    - extra_data: 추가 데이터 (JSON, 선택적)
    """
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bot_id = Column(
        Integer,
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    level = Column(String(20), nullable=False)  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    module = Column(String(100), nullable=False)  # 발생 모듈명
    message = Column(Text, nullable=False)  # 로그 메시지
    extra_data = Column(JSON, nullable=True)  # 추가 데이터 (선택)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── 관계 ───
    bot = relationship("Bot", back_populates="logs")

    def __repr__(self):
        return f"<BotLog(bot_id={self.bot_id}, level='{self.level}', module='{self.module}')>"
