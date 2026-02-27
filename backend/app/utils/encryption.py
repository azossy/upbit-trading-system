"""
============================================================
API 키 암호화 모듈 (AES-256-GCM)
사용자의 거래소 API 키를 안전하게 암호화/복호화합니다.

암호화 방식: AES-256-GCM (Galois/Counter Mode)
  - 256비트 키 사용 (최고 수준 보안)
  - GCM 모드: 암호화 + 인증(무결성 검증)을 동시에 수행
  - 각 암호화마다 고유한 IV(Initialization Vector) 사용
  - 복호화 시 데이터 변조 여부 자동 검증

⚠ 보안 규칙:
  - ENCRYPTION_KEY는 .env에서만 관리, 코드에 하드코딩 금지
  - 암호화된 값만 DB에 저장, 원문은 메모리에서만 사용
  - 로그에 암호화 키, 원문 API 키 절대 기록 금지
============================================================
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


def _get_encryption_key() -> bytes:
    """
    환경 변수에서 AES-256 암호화 키를 가져옵니다.

    Returns:
        32바이트 (256비트) 암호화 키

    Raises:
        ValueError: 키 길이가 올바르지 않은 경우

    참고:
        ENCRYPTION_KEY는 64자 hex 문자열이어야 합니다.
        생성 방법: openssl rand -hex 32
    """
    key_hex = settings.ENCRYPTION_KEY
    key_bytes = bytes.fromhex(key_hex)

    # AES-256은 정확히 32바이트(256비트) 키가 필요
    if len(key_bytes) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY must be 32 bytes (64 hex chars), "
            f"got {len(key_bytes)} bytes. "
            f"Generate with: openssl rand -hex 32"
        )

    return key_bytes


def encrypt_api_key(plain_text: str) -> str:
    """
    API 키를 AES-256-GCM으로 암호화합니다.

    Args:
        plain_text: 암호화할 원문 (API Key 또는 API Secret)

    Returns:
        Base64 인코딩된 암호문 문자열
        (형식: base64(IV + 암호문 + 인증태그))

    동작 과정:
        1. 12바이트 랜덤 IV(Nonce) 생성 — 매 암호화마다 고유
        2. AES-256-GCM으로 원문 암호화
        3. IV + 암호문 + 인증태그를 합쳐서 Base64 인코딩
        4. DB에 저장 가능한 문자열로 반환

    보안 특징:
        - 같은 원문이라도 매번 다른 암호문 생성 (랜덤 IV)
        - 인증 태그로 암호문 변조 감지 가능
    """
    key = _get_encryption_key()

    # AESGCM 인스턴스 생성
    aesgcm = AESGCM(key)

    # 12바이트 랜덤 IV (Nonce) 생성
    # ⚠ IV는 같은 키로 절대 재사용하면 안 됨 → os.urandom으로 매번 새로 생성
    iv = os.urandom(12)

    # 원문을 UTF-8 바이트로 변환 후 암호화
    # GCM 모드: 암호문에 16바이트 인증 태그가 자동으로 추가됨
    ciphertext = aesgcm.encrypt(iv, plain_text.encode('utf-8'), None)

    # IV + 암호문을 합쳐서 Base64 인코딩
    # (복호화 시 IV를 분리해야 하므로 함께 저장)
    encrypted_data = iv + ciphertext
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt_api_key(encrypted_text: str) -> str:
    """
    AES-256-GCM으로 암호화된 API 키를 복호화합니다.

    Args:
        encrypted_text: Base64 인코딩된 암호문 (encrypt_api_key의 반환값)

    Returns:
        복호화된 원문 문자열

    Raises:
        ValueError: 복호화 실패 (키 불일치, 데이터 변조, 형식 오류)

    동작 과정:
        1. Base64 디코딩
        2. 처음 12바이트를 IV로 분리
        3. 나머지를 암호문 + 인증태그로 사용
        4. AES-256-GCM 복호화 (동시에 무결성 검증)
    """
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)

        # Base64 디코딩
        encrypted_data = base64.b64decode(encrypted_text)

        # 처음 12바이트 = IV, 나머지 = 암호문 + 인증태그
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # 복호화 + 무결성 검증
        # ⚠ 인증 태그 검증 실패 시 InvalidTag 예외 발생
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode('utf-8')

    except Exception as e:
        raise ValueError(f"API 키 복호화 실패: {str(e)}")
