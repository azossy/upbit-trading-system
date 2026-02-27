"""
============================================================
데이터베이스 연결 모듈
SQLAlchemy 비동기 엔진과 세션을 관리합니다.
FastAPI의 Dependency Injection을 통해 각 요청마다
독립적인 DB 세션을 제공합니다.
============================================================
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,    # 비동기 DB 엔진 생성
    AsyncSession,           # 비동기 세션 타입
    async_sessionmaker,     # 비동기 세션 팩토리
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# ─── 비동기 DB 엔진 생성 ───
# pool_size: 동시 연결 풀 크기 (다중 사용자 트레이딩 시스템이므로 넉넉하게)
# max_overflow: 풀이 가득 찼을 때 추가 허용 연결 수
# echo: SQL 쿼리 로깅 (개발 시 True, 프로덕션 시 False)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,       # 기본 연결 풀 크기
    max_overflow=10,    # 추가 연결 허용 수
    echo=settings.DEBUG,  # 디버그 모드에서만 SQL 로깅
    pool_pre_ping=True,   # 연결 유효성 사전 체크 (끊어진 연결 자동 복구)
)

# ─── 비동기 세션 팩토리 ───
# expire_on_commit=False: 커밋 후에도 객체 속성 접근 가능
# (FastAPI 응답 직렬화 시 필요)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── ORM 베이스 클래스 ───
# 모든 DB 모델이 이 클래스를 상속받음
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI Dependency Injection용 DB 세션 제공 함수.

    사용법 (라우터에서):
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    세션은 요청이 끝나면 자동으로 닫힘 (yield 이후 finally 블록 실행).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # 요청 종료 시 세션 정리
            await session.close()


async def init_db():
    """
    애플리케이션 시작 시 DB 테이블 생성.
    프로덕션에서는 Alembic 마이그레이션을 사용하는 것을 권장하지만,
    개발 편의를 위해 자동 생성 기능도 제공합니다.
    """
    async with engine.begin() as conn:
        # 모든 모델의 테이블을 생성 (이미 존재하면 무시)
        await conn.run_sync(Base.metadata.create_all)
