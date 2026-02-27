"""
============================================================
API 키 모델 (ApiKey)
사용자의 거래소 API 키를 AES-256-GCM으로 암호화하여 저장합니다.

⚠ 보안 규칙:
  - API 키와 시크릿은 반드시 암호화된 상태로만 DB에 저장
  - 복호화는 트레이딩 엔진 실행 시점에만 메모리에서 수행
  - 로그에는 절대 API 키 원문을 기록하지 않음
  - 업비트 API 키는 반드시 "출금 불가" 권한으로 발급할 것
============================================================
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


class ApiKey(Base):
    """
    거래소 API 키 테이블.

    컬럼 설명:
    - user_id: 소유 사용자 (FK → users.id)
    - exchange: 거래소 이름 (upbit, binance 등)
    - label: 사용자가 지정한 라벨 (예: "메인 계정", "테스트용")
    - encrypted_api_key: AES-256-GCM으로 암호화된 API Key
    - encrypted_api_secret: AES-256-GCM으로 암호화된 API Secret
    - ip_whitelist: API 키에 설정된 IP 화이트리스트 (참고용 기록)
    - is_active: 활성화 여부 (비활성화 시 트레이딩 엔진에서 사용하지 않음)
    - permissions: API 키 권한 메모 (예: "주문+조회, 출금불가")
    """
    __tablename__ = "api_keys"

    # ─── 기본 필드 ───
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # 유저 삭제 시 함께 삭제
        nullable=False,
        index=True,
    )

    # ─── 거래소 정보 ───
    exchange = Column(
        String(50),
        nullable=False,
        default="upbit",  # 기본값: 업비트
    )
    label = Column(String(100), nullable=True)  # 사용자 지정 라벨

    # ─── 암호화된 API 키 (절대 원문 저장 금지!) ───
    # AES-256-GCM 암호화 결과물 (Base64 인코딩된 문자열)
    encrypted_api_key = Column(Text, nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)

    # ─── 보안 메타데이터 ───
    ip_whitelist = Column(String(500), nullable=True)  # 참고용 IP 화이트리스트
    permissions = Column(String(200), nullable=True)  # 권한 메모 ("주문+조회, 출금불가")
    is_active = Column(Boolean, default=True, nullable=False)

    # ─── 타임스탬프 ───
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ─── 관계 ───
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        # ⚠ API 키 원문은 절대 로그/repr에 노출하지 않음
        return f"<ApiKey(id={self.id}, exchange='{self.exchange}', user_id={self.user_id})>"
