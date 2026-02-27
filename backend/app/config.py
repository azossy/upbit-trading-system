"""
============================================================
환경 변수 설정 모듈
.env 파일에서 환경 변수를 읽어와 애플리케이션 전체에서 사용할
설정값을 관리합니다. Pydantic Settings를 사용하여 타입 검증 수행.
============================================================
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    애플리케이션 전역 설정.
    .env 파일 또는 환경 변수에서 값을 자동으로 로드합니다.
    """

    # ─── 데이터베이스 설정 ───
    # PostgreSQL 연결 URL (asyncpg 드라이버 사용)
    DATABASE_URL: str = "postgresql+asyncpg://upbit_user:changeme@localhost:5432/upbit_trading"
    # 동기 URL (Alembic 마이그레이션용)
    DATABASE_URL_SYNC: str = "postgresql://upbit_user:changeme@localhost:5432/upbit_trading"

    # ─── Redis 설정 ───
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ─── JWT 인증 설정 ───
    # 반드시 .env에서 강력한 비밀키로 교체할 것
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    # Access Token 만료 시간 (분) — 30분
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Refresh Token 만료 시간 (일) — 7일
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── API 키 암호화 설정 ───
    # AES-256-GCM 암호화에 사용할 키 (64자 hex 문자열)
    ENCRYPTION_KEY: str = "CHANGE_ME_IN_PRODUCTION"

    # ─── 관리자 초기 계정 ───
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "CHANGE_ME_admin_password"

    # ─── CORS 설정 ───
    # 허용할 프론트엔드 도메인 목록 (쉼표로 구분)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS 허용 도메인을 리스트로 변환"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ─── 텔레그램 봇 설정 ───
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_DEFAULT_CHAT_ID: str = ""

    # ─── 서버 설정 ───
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── 트레이딩 엔진 기본값 ───
    # 최대 동시 보유 코인 수
    MAX_COINS: int = 7
    # 기본 ATR 배수 (손절 계산용)
    DEFAULT_ATR_MULTIPLIER: float = 1.5
    # 최소/최대 손절 비율 (%)
    MIN_STOP_LOSS_PCT: float = 1.5
    MAX_STOP_LOSS_PCT: float = 5.0
    # 트레일링 스탑 활성화 수익률 (%)
    TRAILING_STOP_ACTIVATION_PCT: float = 15.0
    # 트레일링 스탑 폭 (최고점 대비 하락률 %)
    TRAILING_STOP_DISTANCE_PCT: float = 5.0

    class Config:
        # .env 파일에서 환경 변수 로드
        env_file = ".env"
        # 대소문자 무시
        case_sensitive = False


# ─── 전역 설정 인스턴스 (싱글톤) ───
# 애플리케이션 전체에서 이 인스턴스를 import하여 사용
settings = Settings()
