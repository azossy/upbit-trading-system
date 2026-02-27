"""
============================================================
알림 및 일일 리포트 모델 (Alert, DailyReport)
사용자에게 전달되는 알림과 일일/주간 성과 리포트를 저장합니다.
============================================================
"""

import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey,
    DateTime, Date, Enum, Text, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class AlertType(str, enum.Enum):
    """
    알림 유형.
    텔레그램 + 웹 UI 알림에 모두 사용됩니다.
    """
    TRADE_BUY = "trade_buy"       # 매수 체결
    TRADE_SELL = "trade_sell"     # 매도 체결
    STOP_LOSS = "stop_loss"       # 손절 발생
    TAKE_PROFIT = "take_profit"   # 익절 달성
    TRAILING_HIT = "trailing_hit"  # 트레일링 스탑 청산
    MODE_CHANGE = "mode_change"   # 시장 모드 전환
    KILL_SWITCH = "kill_switch"   # 긴급 정지
    API_ERROR = "api_error"       # API 오류
    BOT_PAUSED = "bot_paused"     # 봇 일시 정지 (연속 손절)
    DAILY_REPORT = "daily_report"  # 일일 리포트
    WEEKLY_REPORT = "weekly_report"  # 주간 리포트
    PREMIUM_ALERT = "premium_alert"  # 김치 프리미엄 이상 감지
    SECURITY_ALERT = "security_alert"  # 보안 관련 알림
    SYSTEM_INFO = "system_info"   # 시스템 정보


class Alert(Base):
    """
    알림 테이블.

    웹 UI의 알림 센터와 텔레그램 알림에 동시 사용됩니다.
    is_read로 읽음 상태를 관리하여 웹 UI에서 뱃지(미읽음 수) 표시.

    컬럼 설명:
    - type: 알림 유형 (trade_buy, stop_loss, kill_switch 등)
    - title: 알림 제목 (간략한 한줄 요약)
    - message: 알림 본문 (상세 내용)
    - is_read: 읽음 여부 (웹 UI에서 사용)
    - is_sent_telegram: 텔레그램 전송 완료 여부
    - extra_data: 추가 데이터 (JSON, 코인/가격 등 상세 정보)
    """
    __tablename__ = "alerts"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ─── 알림 내용 ───
    type = Column(Enum(AlertType), nullable=False)
    title = Column(String(200), nullable=False)  # 간략한 제목
    message = Column(Text, nullable=False)  # 상세 본문

    # ─── 상태 ───
    is_read = Column(Boolean, default=False, index=True)  # 웹 UI 읽음 상태
    is_sent_telegram = Column(Boolean, default=False)  # 텔레그램 전송 완료

    # ─── 추가 데이터 (선택) ───
    extra_data = Column(JSON, nullable=True)

    # ─── 타임스탬프 ───
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # ─── 관계 ───
    user = relationship("User", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.type}', title='{self.title}')>"


class DailyReport(Base):
    """
    일일 성과 리포트 테이블.

    매일 자정에 자동 생성되며, 당일 거래 내역을 집계합니다.
    대시보드의 일별 차트와 성과 추적에 사용됩니다.

    컬럼 설명:
    - report_date: 리포트 날짜
    - total_pnl: 당일 실현 손익 (원화)
    - total_pnl_pct: 당일 손익률 (%)
    - total_trades: 당일 거래 횟수
    - win_count / loss_count: 수익/손실 거래 수
    - best_trade_pnl: 당일 최고 수익 거래 (원화)
    - worst_trade_pnl: 당일 최악 손실 거래 (원화)
    - market_mode: 당일 주요 시장 모드
    - portfolio_value: 장마감 시점 포트폴리오 총 가치 (원화)
    """
    __tablename__ = "daily_reports"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_date = Column(Date, nullable=False, index=True)  # 리포트 날짜

    # ─── 성과 지표 ───
    total_pnl = Column(Float, default=0.0)  # 당일 실현 손익 (원화)
    total_pnl_pct = Column(Float, default=0.0)  # 당일 손익률 (%)
    total_trades = Column(Integer, default=0)  # 당일 거래 횟수
    win_count = Column(Integer, default=0)  # 수익 거래 수
    loss_count = Column(Integer, default=0)  # 손실 거래 수

    # ─── 극단값 추적 ───
    best_trade_pnl = Column(Float, default=0.0)  # 최고 수익 거래
    worst_trade_pnl = Column(Float, default=0.0)  # 최악 손실 거래
    best_coin = Column(String(30), nullable=True)  # 최고 수익 코인
    worst_coin = Column(String(30), nullable=True)  # 최악 손실 코인

    # ─── 시장 상태 ───
    market_mode = Column(String(20), nullable=True)  # 당일 주요 시장 모드
    market_score_avg = Column(Float, nullable=True)  # 당일 평균 시장 점수

    # ─── 포트폴리오 ───
    portfolio_value = Column(Float, default=0.0)  # 장마감 총 가치 (원화)
    cash_balance = Column(Float, default=0.0)  # 원화 잔고

    # ─── 타임스탬프 ───
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── 관계 ───
    user = relationship("User", back_populates="daily_reports")

    @property
    def win_rate(self) -> float:
        """당일 승률 (%)"""
        total = self.win_count + self.loss_count
        if total == 0:
            return 0.0
        return round((self.win_count / total) * 100, 2)

    def __repr__(self):
        return f"<DailyReport(user_id={self.user_id}, date={self.report_date}, pnl={self.total_pnl})>"
