"""
============================================================
인증 미들웨어
FastAPI Dependency Injection을 활용한 인증 처리.
JWT 토큰을 검증하고 현재 사용자 정보를 라우터에 주입합니다.

사용법:
    @router.get("/protected")
    async def protected_route(
        current_user: User = Depends(get_current_user)
    ):
        ...

    @router.get("/admin-only")
    async def admin_route(
        current_user: User = Depends(get_current_admin)
    ):
        ...
============================================================
"""

from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.utils.security import decode_token


# ─── Bearer Token 추출기 ───
# Authorization 헤더에서 "Bearer <token>" 형식으로 토큰을 추출
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    현재 인증된 사용자를 반환하는 Dependency.

    처리 흐름:
    1. Authorization 헤더에서 Bearer 토큰 추출
    2. JWT 디코딩 + 서명 검증 + 만료 확인
    3. 토큰의 sub(subject)에서 user_id 추출
    4. DB에서 사용자 조회
    5. 계정 활성화 상태 확인

    Raises:
        401 Unauthorized: 토큰이 없거나, 유효하지 않거나, 만료된 경우
        403 Forbidden: 계정이 비활성화된 경우
    """
    # JWT 토큰 디코딩
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 토큰 유형 확인 (Access Token만 허용)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Token이 필요합니다 (Refresh Token 사용 불가)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 ID 추출
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # DB에서 사용자 조회
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 계정 활성화 상태 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
        )

    # 계정 잠금 상태 확인
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"계정이 잠겨있습니다. {user.locked_until.strftime('%H:%M')}까지 대기하세요.",
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    관리자 권한을 가진 사용자만 허용하는 Dependency.
    일반 사용자가 접근하면 403 Forbidden을 반환합니다.

    사용법:
        @router.get("/admin/users")
        async def admin_get_users(
            admin: User = Depends(get_current_admin)
        ):
            ...
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return current_user
