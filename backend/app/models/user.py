"""
============================================================
유저 모델 (User)
회원가입/로그인/권한 관리를 위한 사용자 테이블.
역할(role)로 일반 유저와 관리자를 구분합니다.
============================================================
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    """
    사용자 역할 구분.
    - user: 일반 사용자 (트레이딩 봇 운영)
    - admin: 관리자 (백오피스 접근, 전체 유저 관리)
    """
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    사용자 테이블.

    컬럼 설명:
    - email: 로그인용 이메일 (고유값, 인덱스)
    - password_hash: bcrypt로 해싱된 비밀번호 (원문 저장 금지)
    - nickname: 표시 이름 (대시보드에서 사용)
    - role: 사용자 역할 (user/admin)
    - is_active: 계정 활성화 여부 (관리자가 비활성화 가능)
    - is_email_verified: 이메일 인증 완료 여부
    - telegram_chat_id: 텔레그램 알림용 채팅 ID
    - last_login_at: 마지막 로그인 시간 (보안 모니터링용)
    - login_fail_count: 연속 로그인 실패 횟수 (5회 초과 시 잠금)
    - locked_until: 계정 잠금 해제 시간
    """
    __tablename__ = "users"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(
        String(255),
        unique=True,       # 중복 이메일 불가
        nullable=False,
        index=True,        # 로그인 시 빠른 조회를 위한 인덱스
    )
    password_hash = Column(String(255), nullable=False)  # bcrypt 해시값
    nickname = Column(String(100), nullable=False)

    # ─── 권한 및 상태 ───
    role = Column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)  # 관리자 비활성화 가능
    is_email_verified = Column(Boolean, default=False)  # 이메일 인증 여부

    # ─── 텔레그램 연동 ───
    telegram_chat_id = Column(String(100), nullable=True)  # 텔레그램 알림용

    # ─── 보안 필드 ───
    last_login_at = Column(DateTime, nullable=True)  # 마지막 로그인 시각
    login_fail_count = Column(Integer, default=0)  # 연속 로그인 실패 횟수
    locked_until = Column(DateTime, nullable=True)  # 계정 잠금 해제 시각

    # ─── 타임스탬프 ───
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,  # 업데이트 시 자동 갱신
        nullable=False,
    )

    # ─── 관계 (Relationships) ───
    # User 삭제 시 연관 데이터도 함께 삭제 (cascade)
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    bots = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
