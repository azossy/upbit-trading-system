"""
============================================================
보안 유틸리티 모듈
JWT 토큰 생성/검증, 비밀번호 해싱을 담당합니다.

보안 설계:
  - Access Token: 30분 만료, 요청 헤더에 포함
  - Refresh Token: 7일 만료, HttpOnly 쿠키로 관리
  - 비밀번호: bcrypt (cost factor 12)로 해싱
  - 계정 잠금: 로그인 5회 실패 시 15분 잠금
============================================================
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt                              # bcrypt 직접 사용 (passlib 호환성 문제 회피)
from jose import JWTError, jwt            # python-jose: JWT 생성/검증 라이브러리
from app.config import settings


def hash_password(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱합니다.

    Args:
        password: 원문 비밀번호

    Returns:
        bcrypt 해시 문자열 (salt 포함, "$2b$12$..." 형식)
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    원문 비밀번호와 해시값을 비교합니다.

    Args:
        plain_password: 사용자가 입력한 원문 비밀번호
        hashed_password: DB에 저장된 bcrypt 해시값

    Returns:
        일치하면 True, 아니면 False
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT Access Token을 생성합니다.

    Args:
        data: 토큰에 포함할 데이터 (보통 {"sub": user_id, "role": "user"})
        expires_delta: 만료 시간 (기본값: settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        JWT 토큰 문자열

    토큰 구조:
        Header: {"alg": "HS256", "typ": "JWT"}
        Payload: {"sub": "123", "role": "user", "type": "access", "exp": 1234567890}
        Signature: HMAC-SHA256(header + payload, secret_key)
    """
    to_encode = data.copy()

    # 만료 시간 설정
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # 토큰 페이로드에 만료 시간과 유형 추가
    to_encode.update({
        "exp": expire,
        "type": "access",  # 토큰 유형 구분 (access vs refresh)
        "iat": datetime.utcnow(),  # 발급 시간
    })

    # JWT 인코딩 (서명)
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT Refresh Token을 생성합니다.
    Access Token보다 긴 만료 시간을 가지며, HttpOnly 쿠키로 관리합니다.

    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본값: settings.REFRESH_TOKEN_EXPIRE_DAYS)

    Returns:
        JWT Refresh Token 문자열
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "type": "refresh",  # Refresh 토큰으로 표시
        "iat": datetime.utcnow(),
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    JWT 토큰을 디코딩하고 유효성을 검증합니다.

    Args:
        token: JWT 토큰 문자열

    Returns:
        디코딩된 페이로드 딕셔너리, 또는 유효하지 않으면 None

    검증 항목:
        - 서명 유효성 (비밀키로 검증)
        - 만료 시간 (exp 클레임)
        - 알고리즘 일치 여부
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        # 서명 불일치, 만료, 형식 오류 등 모든 JWT 오류를 캐치
        return None
