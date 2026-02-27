"""
============================================================
인증 관련 Pydantic 스키마
요청(Request) 및 응답(Response)의 데이터 검증과 직렬화를 담당합니다.
Pydantic v2를 사용하여 타입 안전성과 자동 문서화를 보장합니다.
============================================================
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ─── 회원가입 요청 스키마 ───
class RegisterRequest(BaseModel):
    """
    회원가입 요청 데이터.

    검증 규칙:
    - email: 유효한 이메일 형식 필수 (Pydantic EmailStr)
    - password: 8자 이상, 영문+숫자+특수문자 조합 필수
    - nickname: 2~20자, 한글/영문/숫자만 허용
    """
    email: EmailStr = Field(
        ...,
        description="사용자 이메일 (로그인 ID로 사용)",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="비밀번호 (8자 이상, 영문+숫자+특수문자 조합)",
        examples=["MyP@ssw0rd!"],
    )
    nickname: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="닉네임 (2~20자)",
        examples=["트레이더"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        비밀번호 강도 검증.
        영문, 숫자, 특수문자가 각각 1개 이상 포함되어야 합니다.
        """
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("비밀번호에 영문자가 1개 이상 포함되어야 합니다")
        if not re.search(r'\d', v):
            raise ValueError("비밀번호에 숫자가 1개 이상 포함되어야 합니다")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("비밀번호에 특수문자가 1개 이상 포함되어야 합니다")
        return v

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        """닉네임 검증 — 한글, 영문, 숫자만 허용"""
        if not re.match(r'^[가-힣a-zA-Z0-9]+$', v):
            raise ValueError("닉네임은 한글, 영문, 숫자만 사용 가능합니다")
        return v


# ─── 로그인 요청 스키마 ───
class LoginRequest(BaseModel):
    """
    로그인 요청 데이터.
    이메일과 비밀번호로 인증합니다.
    """
    email: EmailStr = Field(
        ...,
        description="사용자 이메일",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="비밀번호",
        examples=["MyP@ssw0rd!"],
    )


# ─── 토큰 응답 스키마 ───
class TokenResponse(BaseModel):
    """
    로그인 성공 시 반환되는 토큰 응답.
    Access Token은 응답 본문에, Refresh Token은 HttpOnly 쿠키에 설정됩니다.
    """
    access_token: str = Field(..., description="JWT Access Token")
    token_type: str = Field(default="bearer", description="토큰 유형")
    expires_in: int = Field(..., description="Access Token 만료까지 남은 초(seconds)")
    user: "UserResponse" = Field(..., description="로그인한 사용자 정보")


# ─── 토큰 갱신 응답 ───
class RefreshTokenResponse(BaseModel):
    """Refresh Token으로 새 Access Token 발급 시 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ─── 사용자 정보 응답 스키마 ───
class UserResponse(BaseModel):
    """
    사용자 정보 응답.
    비밀번호 해시는 절대 포함하지 않습니다.
    """
    id: int
    email: str
    nickname: str
    role: str
    is_active: bool
    is_email_verified: bool
    telegram_chat_id: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        # ORM 모델에서 직접 변환 허용
        from_attributes = True


# ─── 사용자 프로필 수정 요청 ───
class UserUpdateRequest(BaseModel):
    """사용자 프로필 수정 요청"""
    nickname: Optional[str] = Field(None, min_length=2, max_length=20)
    telegram_chat_id: Optional[str] = Field(None, max_length=100)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r'^[가-힣a-zA-Z0-9]+$', v):
            raise ValueError("닉네임은 한글, 영문, 숫자만 사용 가능합니다")
        return v


# ─── 비밀번호 변경 요청 ───
class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청 (현재 비밀번호 확인 필요)"""
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=128, description="새 비밀번호")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """새 비밀번호 강도 검증"""
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("비밀번호에 영문자가 1개 이상 포함되어야 합니다")
        if not re.search(r'\d', v):
            raise ValueError("비밀번호에 숫자가 1개 이상 포함되어야 합니다")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("비밀번호에 특수문자가 1개 이상 포함되어야 합니다")
        return v


# ─── API 키 등록 요청 ───
class ApiKeyCreateRequest(BaseModel):
    """
    거래소 API 키 등록 요청.
    원문 API 키는 서버에서 AES-256-GCM으로 암호화 후 저장됩니다.
    """
    exchange: str = Field(
        default="upbit",
        description="거래소 이름",
        examples=["upbit"],
    )
    label: Optional[str] = Field(
        None,
        max_length=100,
        description="라벨 (예: '메인 계정')",
    )
    api_key: str = Field(
        ...,
        description="거래소 API Key (서버에서 암호화 후 저장)",
    )
    api_secret: str = Field(
        ...,
        description="거래소 API Secret (서버에서 암호화 후 저장)",
    )
    ip_whitelist: Optional[str] = Field(
        None,
        description="API에 설정한 IP 화이트리스트 (참고용 메모)",
    )
    permissions: Optional[str] = Field(
        None,
        description="API 키 권한 메모 (예: '주문+조회, 출금불가')",
    )


# ─── API 키 응답 스키마 ───
class ApiKeyResponse(BaseModel):
    """
    API 키 정보 응답.
    ⚠ 복호화된 원문 키는 절대 응답에 포함하지 않습니다.
    마지막 4자리만 마스킹하여 표시합니다.
    """
    id: int
    exchange: str
    label: Optional[str]
    api_key_masked: str = Field(
        ...,
        description="마스킹된 API Key (마지막 4자리만 표시)",
        examples=["****abcd"],
    )
    ip_whitelist: Optional[str]
    permissions: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 봇 설정 요청 ───
class BotConfigRequest(BaseModel):
    """
    봇 설정 변경 요청.
    v3.0 설계 문서의 파라미터들을 사용자가 커스터마이징할 수 있습니다.
    """
    # 투자 비율 관련
    max_investment_ratio: Optional[float] = Field(
        None, ge=0.1, le=1.0,
        description="최대 투자 비율 (0.1~1.0, 예: 0.5 = 50%)",
    )
    max_coins: Optional[int] = Field(
        None, ge=1, le=7,
        description="최대 동시 보유 코인 수 (1~7)",
    )

    # ATR 기반 손절 관련
    atr_multiplier: Optional[float] = Field(
        None, ge=1.0, le=3.0,
        description="ATR 배수 (손절 계산, 기본 1.5)",
    )
    min_stop_loss_pct: Optional[float] = Field(
        None, ge=0.5, le=3.0,
        description="최소 손절 비율 (%, 기본 1.5)",
    )
    max_stop_loss_pct: Optional[float] = Field(
        None, ge=3.0, le=10.0,
        description="최대 손절 비율 (%, 기본 5.0)",
    )

    # 트레일링 스탑 관련
    trailing_stop_activation_pct: Optional[float] = Field(
        None, ge=5.0, le=30.0,
        description="트레일링 스탑 활성화 수익률 (%, 기본 15.0)",
    )
    trailing_stop_distance_pct: Optional[float] = Field(
        None, ge=2.0, le=10.0,
        description="트레일링 스탑 폭 (최고점 대비 하락%, 기본 5.0)",
    )


# ─── 봇 상태 응답 ───
class BotStatusResponse(BaseModel):
    """봇 현재 상태 응답"""
    id: int
    status: str
    market_mode: str
    market_score: int
    config: dict
    total_pnl: float
    total_trades: int
    win_rate: float
    consecutive_losses: int
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    stop_reason: Optional[str]

    class Config:
        from_attributes = True


# ─── 공통 응답 ───
class MessageResponse(BaseModel):
    """일반 메시지 응답 (성공/실패 메시지)"""
    message: str
    success: bool = True
