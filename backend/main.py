"""
============================================================
업비트 자동매매 시스템 v3.0 — FastAPI 메인 엔트리포인트
============================================================
이 파일은 FastAPI 애플리케이션의 시작점입니다.
- CORS, Rate Limit, 미들웨어 설정
- 라우터 등록
- DB 초기화 및 관리자 계정 시드
- WebSocket 엔드포인트 (실시간 시세/상태)
============================================================
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.routers import auth, bot, admin
import app.models  # noqa: F401 — 모든 ORM 모델을 로드해야 init_db가 테이블을 인식


# ─── Loguru 로거 설정 ───
# 기본 stderr 핸들러를 제거하고, 포맷/레벨을 커스터마이즈
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,         # .env의 LOG_LEVEL 사용
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
           "{message}",
    colorize=True,
)
# 파일 로그: 일별 로테이션, 30일 보관
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",      # 매일 자정에 새 파일
    retention="30 days",   # 30일 이후 자동 삭제
    compression="gz",      # gzip 압축
    level="DEBUG",
    encoding="utf-8",
)


# ─── 애플리케이션 수명 주기 관리 (Lifespan) ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱 시작/종료 시 실행되는 수명 주기 이벤트.
    - 시작 시: DB 테이블 생성, 관리자 계정 시드
    - 종료 시: 리소스 정리
    """
    # ── 시작 (Startup) ──
    logger.info("=" * 60)
    logger.info("🚀 업비트 자동매매 시스템 v3.0 시작")
    logger.info("=" * 60)

    # DB 테이블 자동 생성 (Alembic 마이그레이션 대안)
    await init_db()
    logger.info("[DB] 데이터베이스 테이블 초기화 완료")

    # 관리자 초기 계정 시드 (없으면 생성)
    await _seed_admin_user()

    yield  # ← 이 지점에서 앱이 실행됨

    # ── 종료 (Shutdown) ──
    logger.info("🛑 업비트 자동매매 시스템 종료")


async def _seed_admin_user():
    """
    초기 관리자 계정을 생성합니다.
    이미 존재하면 건너뜁니다.
    """
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from app.utils.security import hash_password

    async with AsyncSessionLocal() as db:
        # 관리자 계정 존재 여부 확인
        result = await db.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            # 관리자 계정 생성
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                nickname="관리자",
                role=UserRole.ADMIN,
                is_active=True,
                is_email_verified=True,  # 관리자는 이메일 인증 면제
            )
            db.add(admin_user)
            await db.commit()
            logger.info(f"[SEED] 관리자 계정 생성 완료: {settings.ADMIN_EMAIL}")
        else:
            logger.info(f"[SEED] 관리자 계정 이미 존재: {settings.ADMIN_EMAIL}")


# ─── FastAPI 앱 인스턴스 생성 ───
app = FastAPI(
    title="업비트 자동매매 시스템 v3.0",
    description=(
        "업비트 거래소 API를 활용한 자동 트레이딩 봇 시스템.\n"
        "시장 상황 분석, 자동 매수/매도, 손절/익절, 트레일링 스탑,\n"
        "실시간 대시보드, 텔레그램 알림을 제공합니다."
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",              # Swagger UI 경로
    redoc_url="/redoc",            # ReDoc 경로
    openapi_url="/api/v1/openapi.json",  # OpenAPI 스키마 경로
)


# ─── CORS 미들웨어 설정 ───
# 프론트엔드(React)에서 API 호출을 허용하기 위한 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # 허용할 도메인 목록
    allow_credentials=True,       # 쿠키(Refresh Token) 전송 허용
    allow_methods=["*"],          # 모든 HTTP 메서드 허용
    allow_headers=["*"],          # 모든 헤더 허용
)


# ─── 라우터 등록 ───
# 각 도메인별 라우터를 앱에 등록
app.include_router(auth.router)   # /api/v1/auth — 인증 (회원가입/로그인/토큰)
app.include_router(bot.router)    # /api/v1/bot  — 봇 제어 (시작/정지/설정)
app.include_router(admin.router)  # /api/v1/admin — 관리자 백오피스


# ─── 헬스체크 엔드포인트 ───
@app.get("/health", tags=["시스템"])
async def health_check():
    """
    서버 상태 확인용 헬스체크.
    Docker/Kubernetes 헬스프로브에서 사용합니다.
    """
    return {
        "status": "healthy",
        "version": "3.0.0",
        "service": "upbit-auto-trading",
    }


# ─── 루트 경로 ───
@app.get("/", tags=["시스템"])
async def root():
    """루트 경로 — API 안내"""
    return {
        "message": "업비트 자동매매 시스템 v3.0 API",
        "docs": "/docs",
        "health": "/health",
    }


# ─── 직접 실행 시 uvicorn 서버 기동 ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,      # 개발 모드에서만 핫 리로드
        log_level=settings.LOG_LEVEL.lower(),
    )
