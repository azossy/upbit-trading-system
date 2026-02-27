"""
============================================================
인증 API 라우터 (/api/v1/auth)
회원가입, 로그인, 토큰 갱신, 로그아웃을 처리합니다.

엔드포인트:
  POST /register     - 회원가입
  POST /login        - 로그인 (JWT 발급)
  POST /refresh      - Access Token 갱신
  POST /logout       - 로그아웃 (Refresh Token 무효화)
  GET  /me           - 현재 사용자 정보 조회
  PUT  /me           - 프로필 수정
  PUT  /me/password  - 비밀번호 변경

보안:
  - 로그인 실패 5회 → 15분 계정 잠금
  - Refresh Token: HttpOnly + SameSite Cookie
  - 비밀번호: bcrypt (cost factor 12)
============================================================
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenResponse,
    UserResponse,
    UserUpdateRequest,
    PasswordChangeRequest,
    MessageResponse,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.middleware.auth_middleware import get_current_user
from app.config import settings
from loguru import logger

# ─── 라우터 생성 ───
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["인증"],
)

# ─── 계정 잠금 상수 ───
MAX_LOGIN_ATTEMPTS = 5       # 최대 로그인 시도 횟수
LOCKOUT_DURATION_MINUTES = 15  # 잠금 시간 (분)


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="이메일, 비밀번호, 닉네임으로 새 계정을 생성합니다.",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    회원가입 처리.

    1. 이메일 중복 확인
    2. 비밀번호 bcrypt 해싱
    3. 새 사용자 생성 및 DB 저장
    """
    # 이메일 중복 확인
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다",
        )

    # 새 사용자 생성
    new_user = User(
        email=request.email,
        password_hash=hash_password(request.password),  # bcrypt 해싱
        nickname=request.nickname,
        role=UserRole.USER,  # 기본 역할: 일반 사용자
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"[AUTH] 새 사용자 가입: {request.email}")

    return MessageResponse(
        message="회원가입이 완료되었습니다. 로그인해주세요.",
        success=True,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
    description="이메일과 비밀번호로 인증하고 JWT 토큰을 발급합니다.",
)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    로그인 처리.

    1. 이메일로 사용자 조회
    2. 계정 잠금 상태 확인
    3. 비밀번호 검증
    4. 로그인 실패 시 실패 카운터 증가 (5회 초과 시 잠금)
    5. 성공 시 Access Token + Refresh Token 발급
    """
    # 사용자 조회
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # 계정 잠금 확인
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"로그인 시도 횟수 초과. {remaining}분 후 다시 시도하세요.",
        )

    # 계정 활성화 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
        )

    # 비밀번호 검증
    if not verify_password(request.password, user.password_hash):
        # 로그인 실패 — 실패 카운터 증가
        user.login_fail_count += 1

        # 5회 초과 시 계정 잠금
        if user.login_fail_count >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
            logger.warning(
                f"[AUTH] 계정 잠금: {user.email} "
                f"(로그인 실패 {user.login_fail_count}회)"
            )

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # ─── 로그인 성공 ───

    # 실패 카운터 초기화
    user.login_fail_count = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # JWT 토큰 생성
    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Refresh Token을 HttpOnly 쿠키로 설정
    # ⚠ HttpOnly: JavaScript에서 접근 불가 (XSS 방지)
    # ⚠ SameSite=lax: CSRF 공격 방지
    # ⚠ Secure: HTTPS에서만 전송 (프로덕션)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,        # JavaScript 접근 차단
        samesite="lax",       # CSRF 방지
        secure=not settings.DEBUG,  # 프로덕션에서만 HTTPS 강제
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,  # 7일 (초)
        path="/api/v1/auth",  # 인증 경로에서만 쿠키 전송
    )

    logger.info(f"[AUTH] 로그인 성공: {user.email}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="토큰 갱신",
    description="Refresh Token으로 새 Access Token을 발급합니다.",
)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Access Token 갱신.
    HttpOnly 쿠키에 저장된 Refresh Token을 사용하여
    새로운 Access Token을 발급합니다.
    """
    # 쿠키에서 Refresh Token 추출
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없습니다. 다시 로그인해주세요.",
        )

    # Refresh Token 검증
    payload = decode_token(refresh_token_value)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 Refresh Token입니다. 다시 로그인해주세요.",
        )

    # 사용자 확인
    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없거나 비활성화된 계정입니다.",
        )

    # 새 Access Token 발급
    new_access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
    })

    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="로그아웃",
    description="Refresh Token 쿠키를 삭제하여 로그아웃합니다.",
)
async def logout(response: Response):
    """
    로그아웃 처리.
    HttpOnly 쿠키에 저장된 Refresh Token을 삭제합니다.
    """
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    return MessageResponse(message="로그아웃되었습니다")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="내 정보 조회",
    description="현재 로그인한 사용자의 정보를 반환합니다.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """현재 사용자 정보 반환"""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="프로필 수정",
    description="닉네임, 텔레그램 등 프로필 정보를 수정합니다.",
)
async def update_me(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로필 수정"""
    if request.nickname is not None:
        current_user.nickname = request.nickname
    if request.telegram_chat_id is not None:
        current_user.telegram_chat_id = request.telegram_chat_id

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="비밀번호 변경",
    description="현재 비밀번호를 확인 후 새 비밀번호로 변경합니다.",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """비밀번호 변경"""
    # 현재 비밀번호 확인
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다",
        )

    # 새 비밀번호로 변경
    current_user.password_hash = hash_password(request.new_password)
    await db.commit()

    logger.info(f"[AUTH] 비밀번호 변경: {current_user.email}")

    return MessageResponse(message="비밀번호가 변경되었습니다")
