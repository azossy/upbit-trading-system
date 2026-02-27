"""initial schema

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-02-25 00:00:00.000000

업비트 자동매매 시스템 v3.0 초기 데이터베이스 스키마.
모든 핵심 테이블을 한 번에 생성합니다:
  - users          : 사용자 계정
  - api_keys       : 업비트 API 키 (AES-256 암호화 저장)
  - bots           : 트레이딩 봇 인스턴스
  - bot_logs       : 봇 이벤트 로그
  - trades         : 매수/매도 체결 내역
  - positions      : 현재 보유 포지션
  - alerts         : 알림 기록
  - daily_reports  : 일일 성과 리포트
"""
from typing import Sequence, Union

import sqlalchemy as sa  # SQLAlchemy 타입 정의 (sa.String, sa.Integer 등)
from alembic import op  # DDL 명령 (op.create_table, op.add_column 등)

# ─── 마이그레이션 식별자 ───
revision: str = "a1b2c3d4e5f6"      # 이 마이그레이션의 고유 ID
down_revision: Union[str, None] = None  # None = 최초 마이그레이션 (이전 없음)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    초기 스키마 생성.
    테이블 생성 순서는 외래 키(FK) 의존성 순서를 따릅니다:
      users → api_keys, bots
      bots  → bot_logs, trades, positions
      users → alerts, daily_reports
    """

    # ════════════════════════════════════════════════════
    # 1. users 테이블 — 모든 테이블의 루트 (FK 없음)
    # ════════════════════════════════════════════════════
    op.create_table(
        "users",
        # ─── 기본 키 ───
        sa.Column(
            "id", sa.Integer,
            primary_key=True,
            autoincrement=True,
            comment="사용자 고유 ID (자동 증가)"
        ),
        # ─── 이메일 (로그인 아이디) ───
        sa.Column(
            "email", sa.String(255),
            nullable=False,
            comment="로그인용 이메일 주소 (고유값)"
        ),
        # ─── 비밀번호 해시 (원문 절대 저장 금지) ───
        sa.Column(
            "password_hash", sa.String(255),
            nullable=False,
            comment="bcrypt 해싱된 비밀번호 (원문 아님)"
        ),
        # ─── 표시 이름 ───
        sa.Column(
            "nickname", sa.String(100),
            nullable=False,
            comment="대시보드에 표시되는 닉네임"
        ),
        # ─── 역할 (user/admin) ───
        sa.Column(
            "role", sa.Enum("user", "admin", name="userrole"),
            nullable=False,
            server_default="user",
            comment="사용자 역할: user=일반, admin=관리자"
        ),
        # ─── 계정 상태 ───
        sa.Column(
            "is_active", sa.Boolean,
            nullable=False,
            server_default="true",
            comment="계정 활성화 여부 (관리자가 비활성화 가능)"
        ),
        sa.Column(
            "is_email_verified", sa.Boolean,
            nullable=False,
            server_default="false",
            comment="이메일 인증 완료 여부"
        ),
        # ─── 텔레그램 연동 ───
        sa.Column(
            "telegram_chat_id", sa.String(100),
            nullable=True,
            comment="텔레그램 알림 수신용 채팅 ID"
        ),
        # ─── 보안 필드 ───
        sa.Column(
            "last_login_at", sa.DateTime,
            nullable=True,
            comment="마지막 로그인 일시 (보안 모니터링)"
        ),
        sa.Column(
            "login_fail_count", sa.Integer,
            nullable=False,
            server_default="0",
            comment="연속 로그인 실패 횟수 (5회 초과 시 15분 잠금)"
        ),
        sa.Column(
            "locked_until", sa.DateTime,
            nullable=True,
            comment="계정 잠금 해제 시각 (null=잠금 없음)"
        ),
        # ─── 타임스탬프 ───
        sa.Column(
            "created_at", sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="계정 생성 일시"
        ),
        sa.Column(
            "updated_at", sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="마지막 수정 일시"
        ),
    )
    # ─── users 인덱스 ───
    # email은 로그인 시 WHERE email=? 쿼리에 사용 → UNIQUE INDEX 필수
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ════════════════════════════════════════════════════
    # 2. api_keys 테이블 — 업비트 API 키 (AES-256 암호화)
    # ════════════════════════════════════════════════════
    op.create_table(
        "api_keys",
        sa.Column(
            "id", sa.Integer,
            primary_key=True,
            autoincrement=True,
            comment="API 키 레코드 고유 ID"
        ),
        # ─── 소유자 FK ───
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="API 키 소유 사용자 ID (CASCADE: 유저 삭제 시 함께 삭제)"
        ),
        # ─── 거래소 정보 ───
        sa.Column(
            "exchange", sa.String(50),
            nullable=False,
            server_default="upbit",
            comment="거래소명 (현재는 upbit만 지원)"
        ),
        sa.Column(
            "label", sa.String(100),
            nullable=True,
            comment="API 키 별칭 (예: '주요 봇용', '테스트용')"
        ),
        # ─── 암호화된 API 키 ───
        # AES-256-GCM으로 암호화 (encryption.py 참고)
        # 형식: base64(iv) + ":" + base64(ciphertext) + ":" + base64(tag)
        sa.Column(
            "access_key_enc", sa.sa.Text,
            nullable=False,
            comment="AES-256-GCM 암호화된 Access Key"
        ),
        sa.Column(
            "secret_key_enc", sa.sa.Text,
            nullable=False,
            comment="AES-256-GCM 암호화된 Secret Key"
        ),
        # ─── 마지막 4자리 (UI 표시용, 원문 대신 사용) ───
        sa.Column(
            "access_key_last4", sa.String(4),
            nullable=True,
            comment="Access Key 마지막 4자리 (UI 표시용, 원문 아님)"
        ),
        # ─── 사용 여부 ───
        sa.Column(
            "is_active", sa.Boolean,
            nullable=False,
            server_default="true",
            comment="API 키 활성화 여부"
        ),
        # ─── 타임스탬프 ───
        sa.Column(
            "created_at", sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="API 키 등록 일시"
        ),
        sa.Column(
            "last_used_at", sa.DateTime,
            nullable=True,
            comment="마지막 사용 일시 (API 호출 시 갱신)"
        ),
    )
    # ─── api_keys 인덱스 ───
    op.create_index("ix_api_keys_id", "api_keys", ["id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # ════════════════════════════════════════════════════
    # 3. bots 테이블 — 트레이딩 봇 인스턴스 (사용자당 1개)
    # ════════════════════════════════════════════════════
    op.create_table(
        "bots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        # ─── 소유자 FK (사용자당 1개 → UNIQUE) ───
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,  # 사용자 1명당 봇 1개 제한
            comment="봇 소유 사용자 ID (1:1 관계)"
        ),
        # ─── 봇 상태 머신 ───
        sa.Column(
            "status",
            sa.Enum("stopped", "running", "paused", "error", "maintenance",
                    name="botstatus"),
            nullable=False,
            server_default="stopped",
            comment="봇 현재 상태"
        ),
        # ─── 시장 분석 결과 ───
        sa.Column(
            "market_mode",
            sa.Enum("bull", "sideways", "bear", "unknown", name="marketmode"),
            nullable=False,
            server_default="unknown",
            comment="현재 감지된 시장 국면"
        ),
        sa.Column(
            "market_score", sa.Integer,
            nullable=True,
            server_default="0",
            comment="시장 점수 (0~100, 60이상=상승장, 40미만=하락장)"
        ),
        # ─── 봇 설정 (JSON) ───
        # 예: {"investment_ratio": 0.5, "max_coins": 7, "atr_multiplier": 1.5}
        sa.Column(
            "config", sa.JSON,
            nullable=False,
            server_default="{}",
            comment="사용자 커스텀 봇 설정 (JSON)"
        ),
        # ─── 누적 성과 통계 ───
        sa.Column(
            "total_pnl", sa.Float,
            server_default="0.0",
            comment="누적 실현 손익 (원화)"
        ),
        sa.Column(
            "total_trades", sa.Integer,
            server_default="0",
            comment="총 거래 횟수"
        ),
        sa.Column(
            "win_count", sa.Integer,
            server_default="0",
            comment="수익 거래 횟수"
        ),
        sa.Column(
            "loss_count", sa.Integer,
            server_default="0",
            comment="손실 거래 횟수"
        ),
        # ─── 리스크 관리 카운터 ───
        sa.Column(
            "consecutive_losses", sa.Integer,
            server_default="0",
            comment="현재 연속 손절 횟수 (3회 초과 시 투자금 50% 축소)"
        ),
        sa.Column(
            "daily_pnl", sa.Float,
            server_default="0.0",
            comment="당일 손익 (%)"
        ),
        sa.Column(
            "weekly_pnl", sa.Float,
            server_default="0.0",
            comment="금주 손익 (%)"
        ),
        sa.Column(
            "monthly_pnl", sa.Float,
            server_default="0.0",
            comment="당월 손익 (%)"
        ),
        # ─── 정지 사유 ───
        sa.Column(
            "stop_reason", sa.Text,
            nullable=True,
            comment="봇 정지/에러 사유 (에러 발생 시 기록)"
        ),
        # ─── 타임스탬프 ───
        sa.Column("started_at", sa.DateTime, nullable=True,
                  comment="마지막 봇 시작 일시"),
        sa.Column("stopped_at", sa.DateTime, nullable=True,
                  comment="마지막 봇 정지 일시"),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_bots_id", "bots", ["id"])
    op.create_index("ix_bots_user_id", "bots", ["user_id"])

    # ════════════════════════════════════════════════════
    # 4. bot_logs 테이블 — 봇 이벤트 로그
    # ════════════════════════════════════════════════════
    op.create_table(
        "bot_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "bot_id", sa.Integer,
            sa.ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False,
            comment="로그가 속한 봇 ID"
        ),
        sa.Column(
            "level", sa.String(20),
            nullable=False,
            comment="로그 레벨: DEBUG/INFO/WARNING/ERROR/CRITICAL"
        ),
        sa.Column(
            "module", sa.String(100),
            nullable=False,
            comment="로그 발생 모듈명 (예: market_analyzer, signal_generator)"
        ),
        sa.Column("message", sa.Text, nullable=False,
                  comment="로그 메시지"),
        sa.Column(
            "extra_data", sa.JSON,
            nullable=True,
            comment="추가 데이터 (선택적, JSON)"
        ),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_bot_logs_id", "bot_logs", ["id"])
    op.create_index("ix_bot_logs_bot_id", "bot_logs", ["bot_id"])

    # ════════════════════════════════════════════════════
    # 5. trades 테이블 — 매수/매도 체결 내역
    # ════════════════════════════════════════════════════
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="거래한 사용자 ID"
        ),
        sa.Column(
            "bot_id", sa.Integer,
            sa.ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False,
            comment="거래를 실행한 봇 ID"
        ),
        # ─── 거래 기본 정보 ───
        sa.Column(
            "coin", sa.String(20),
            nullable=False,
            comment="코인 심볼 (예: KRW-BTC, KRW-ETH)"
        ),
        sa.Column(
            "side",
            sa.Enum("buy", "sell", name="tradeside"),
            nullable=False,
            comment="거래 방향: buy=매수, sell=매도"
        ),
        sa.Column(
            "order_type",
            sa.Enum("market", "limit", name="ordertype"),
            nullable=False,
            server_default="market",
            comment="주문 유형: market=시장가, limit=지정가"
        ),
        # ─── 체결 정보 ───
        sa.Column("price", sa.Float, nullable=False,
                  comment="체결 가격 (원화/코인)"),
        sa.Column("quantity", sa.Float, nullable=False,
                  comment="체결 수량 (코인 단위)"),
        sa.Column("amount", sa.Float, nullable=False,
                  comment="체결 금액 (원화 = price × quantity)"),
        sa.Column(
            "fee", sa.Float,
            server_default="0.0",
            comment="수수료 (원화, 업비트 0.05%)"
        ),
        # ─── 손익 (매도 시에만 유효) ───
        sa.Column(
            "realized_pnl", sa.Float,
            nullable=True,
            comment="실현 손익 (매도 시 = 매도금액 - 매수금액 - 수수료)"
        ),
        sa.Column(
            "pnl_percentage", sa.Float,
            nullable=True,
            comment="실현 손익률 (%)"
        ),
        # ─── 거래 사유 ───
        sa.Column(
            "reason",
            sa.Enum(
                "entry_1st", "entry_2nd", "entry_3rd",
                "sideways_entry_1st", "sideways_entry_2nd",
                "take_profit_1st", "take_profit_2nd", "take_profit_3rd",
                "trailing_stop",
                "sideways_tp_mid", "sideways_tp_upper", "sideways_rsi_exit",
                "stop_loss_atr", "stop_loss_signal", "stop_loss_mode", "stop_loss_time",
                "emergency", "manual",
                name="tradereason"
            ),
            nullable=True,
            comment="거래 발생 사유 (전략 분석용)"
        ),
        # ─── 업비트 주문 UUID ───
        sa.Column(
            "order_uuid", sa.String(100),
            nullable=True,
            comment="업비트에서 반환한 주문 UUID (체결 확인용)"
        ),
        sa.Column("executed_at", sa.DateTime, nullable=True,
                  comment="체결 일시"),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_trades_id", "trades", ["id"])
    op.create_index("ix_trades_user_id", "trades", ["user_id"])
    op.create_index("ix_trades_bot_id", "trades", ["bot_id"])
    # coin 기준 조회도 빈번하므로 인덱스 추가
    op.create_index("ix_trades_coin", "trades", ["coin"])

    # ════════════════════════════════════════════════════
    # 6. positions 테이블 — 현재 보유 포지션
    # ════════════════════════════════════════════════════
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "bot_id", sa.Integer,
            sa.ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False
        ),
        # ─── 포지션 정보 ───
        sa.Column("coin", sa.String(20), nullable=False,
                  comment="코인 심볼 (예: KRW-BTC)"),
        sa.Column(
            "position_type",
            sa.Enum("bull_trend", "sideways_revert", name="positiontype"),
            nullable=False,
            server_default="bull_trend",
            comment="포지션 유형 (상승장 추세/횡보장 평균회귀)"
        ),
        # ─── 진입 정보 ───
        sa.Column("avg_entry_price", sa.Float, nullable=False,
                  comment="분할 진입 평균 단가"),
        sa.Column("total_quantity", sa.Float, nullable=False,
                  comment="현재 총 보유 수량"),
        sa.Column("total_invested", sa.Float, nullable=False,
                  comment="총 투자 금액 (원화)"),
        sa.Column("entry_step", sa.Integer, server_default="1",
                  comment="현재 분할 진입 단계 (1,2,3차)"),
        # ─── 리스크 관리 기준선 ───
        sa.Column("stop_loss_price", sa.Float, nullable=True,
                  comment="ATR 기반 동적 손절가"),
        sa.Column("take_profit_1", sa.Float, nullable=True,
                  comment="1차 익절 목표가 (+7%)"),
        sa.Column("take_profit_2", sa.Float, nullable=True,
                  comment="2차 익절 목표가 (+15%)"),
        sa.Column("take_profit_3", sa.Float, nullable=True,
                  comment="3차 익절 목표가 (+25%)"),
        sa.Column("tp_step", sa.Integer, server_default="0",
                  comment="현재 분할 익절 단계 (0=미달성, 1=1차완료, 2=2차완료)"),
        # ─── 트레일링 스탑 ───
        sa.Column(
            "trailing_active", sa.Boolean,
            server_default="false",
            comment="+15% 수익 달성 시 트레일링 스탑 활성화"
        ),
        sa.Column(
            "trailing_high_price", sa.Float,
            nullable=True,
            comment="트레일링 스탑 추적 최고가 (이 가격의 -5%에서 청산)"
        ),
        # ─── 포지션 상태 ───
        sa.Column(
            "is_closed", sa.Boolean,
            server_default="false",
            comment="포지션 청산 완료 여부 (true=종료됨)"
        ),
        sa.Column("entry_at", sa.DateTime, nullable=True,
                  comment="최초 진입 일시"),
        sa.Column("closed_at", sa.DateTime, nullable=True,
                  comment="청산 완료 일시"),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_positions_id", "positions", ["id"])
    op.create_index("ix_positions_user_id", "positions", ["user_id"])
    op.create_index("ix_positions_bot_id", "positions", ["bot_id"])
    op.create_index("ix_positions_coin", "positions", ["coin"])

    # ════════════════════════════════════════════════════
    # 7. alerts 테이블 — 알림 기록
    # ════════════════════════════════════════════════════
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "alert_type",
            sa.Enum(
                "trade_buy", "trade_sell", "stop_loss", "take_profit",
                "trailing_hit", "mode_change", "kill_switch", "api_error",
                "bot_paused", "daily_report", "weekly_report",
                "premium_alert", "security_alert", "system_info",
                name="alerttype"
            ),
            nullable=False,
            comment="알림 유형"
        ),
        sa.Column("title", sa.String(200), nullable=False,
                  comment="알림 제목"),
        sa.Column("message", sa.Text, nullable=False,
                  comment="알림 내용 (Markdown 지원)"),
        sa.Column(
            "extra_data", sa.JSON,
            nullable=True,
            comment="추가 데이터 (JSON)"
        ),
        sa.Column(
            "is_read", sa.Boolean,
            server_default="false",
            comment="사용자 읽음 여부"
        ),
        sa.Column(
            "telegram_sent", sa.Boolean,
            server_default="false",
            comment="텔레그램 전송 완료 여부"
        ),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"])
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])

    # ════════════════════════════════════════════════════
    # 8. daily_reports 테이블 — 일일 성과 리포트
    # ════════════════════════════════════════════════════
    op.create_table(
        "daily_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        ),
        # ─── 리포트 기간 ───
        sa.Column("report_date", sa.Date, nullable=False,
                  comment="리포트 날짜 (YYYY-MM-DD)"),
        # ─── 거래 통계 ───
        sa.Column("total_trades", sa.Integer, server_default="0",
                  comment="당일 총 거래 횟수"),
        sa.Column("win_trades", sa.Integer, server_default="0",
                  comment="수익 거래 횟수"),
        sa.Column("loss_trades", sa.Integer, server_default="0",
                  comment="손실 거래 횟수"),
        # ─── 손익 정보 ───
        sa.Column("total_pnl", sa.Float, server_default="0.0",
                  comment="당일 총 실현 손익 (원화)"),
        sa.Column("pnl_percentage", sa.Float, server_default="0.0",
                  comment="당일 손익률 (%)"),
        sa.Column("best_trade_coin", sa.String(20), nullable=True,
                  comment="당일 최고 수익 코인"),
        sa.Column("best_trade_pnl", sa.Float, nullable=True,
                  comment="최고 수익 거래 손익 (원화)"),
        sa.Column("worst_trade_coin", sa.String(20), nullable=True,
                  comment="당일 최대 손실 코인"),
        sa.Column("worst_trade_pnl", sa.Float, nullable=True,
                  comment="최대 손실 거래 손익 (원화)"),
        # ─── 시장 환경 ───
        sa.Column(
            "market_mode",
            sa.Enum("bull", "sideways", "bear", "unknown",
                    name="marketmode_report"),
            nullable=True,
            comment="당일 주요 시장 국면"
        ),
        sa.Column("market_score_avg", sa.Float, nullable=True,
                  comment="당일 평균 시장 점수"),
        # ─── 원문 데이터 (텔레그램 전송용) ───
        sa.Column("raw_data", sa.JSON, nullable=True,
                  comment="리포트 전체 원문 데이터 (JSON)"),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_daily_reports_id", "daily_reports", ["id"])
    op.create_index("ix_daily_reports_user_id", "daily_reports", ["user_id"])
    # 날짜 + 사용자 조합은 UNIQUE (중복 리포트 방지)
    op.create_index(
        "uq_daily_reports_user_date", "daily_reports",
        ["user_id", "report_date"], unique=True
    )


def downgrade() -> None:
    """
    롤백 — 모든 테이블을 삭제합니다.
    upgrade()의 역순으로 삭제해야 FK 제약 오류가 발생하지 않습니다.

    삭제 순서 (FK 의존성 역순):
      daily_reports → alerts → positions → trades → bot_logs
      → bots → api_keys → users
    """
    # ─── 의존성이 높은 테이블부터 삭제 ───
    op.drop_index("uq_daily_reports_user_date", "daily_reports")
    op.drop_index("ix_daily_reports_user_id", "daily_reports")
    op.drop_index("ix_daily_reports_id", "daily_reports")
    op.drop_table("daily_reports")

    op.drop_index("ix_alerts_user_id", "alerts")
    op.drop_index("ix_alerts_id", "alerts")
    op.drop_table("alerts")

    op.drop_index("ix_positions_coin", "positions")
    op.drop_index("ix_positions_bot_id", "positions")
    op.drop_index("ix_positions_user_id", "positions")
    op.drop_index("ix_positions_id", "positions")
    op.drop_table("positions")

    op.drop_index("ix_trades_coin", "trades")
    op.drop_index("ix_trades_bot_id", "trades")
    op.drop_index("ix_trades_user_id", "trades")
    op.drop_index("ix_trades_id", "trades")
    op.drop_table("trades")

    op.drop_index("ix_bot_logs_bot_id", "bot_logs")
    op.drop_index("ix_bot_logs_id", "bot_logs")
    op.drop_table("bot_logs")

    op.drop_index("ix_bots_user_id", "bots")
    op.drop_index("ix_bots_id", "bots")
    op.drop_table("bots")

    op.drop_index("ix_api_keys_user_id", "api_keys")
    op.drop_index("ix_api_keys_id", "api_keys")
    op.drop_table("api_keys")

    op.drop_index("ix_users_email", "users")
    op.drop_index("ix_users_id", "users")
    op.drop_table("users")

    # ─── PostgreSQL ENUM 타입 삭제 ───
    # create_table() 시 자동 생성된 ENUM 타입을 명시적으로 삭제
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS botstatus")
    op.execute("DROP TYPE IF EXISTS marketmode")
    op.execute("DROP TYPE IF EXISTS marketmode_report")
    op.execute("DROP TYPE IF EXISTS tradeside")
    op.execute("DROP TYPE IF EXISTS ordertype")
    op.execute("DROP TYPE IF EXISTS tradereason")
    op.execute("DROP TYPE IF EXISTS positiontype")
    op.execute("DROP TYPE IF EXISTS alerttype")
