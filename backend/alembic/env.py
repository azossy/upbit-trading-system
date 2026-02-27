"""
============================================================
Alembic 환경 설정 파일
비동기 SQLAlchemy(asyncpg)와 FastAPI 앱의 설정을 연동합니다.

Alembic은 기본적으로 동기(sync) 방식으로 동작하지만,
우리 앱은 asyncpg(비동기 PostgreSQL 드라이버)를 사용합니다.
따라서 asyncio.run()을 활용한 비동기 마이그레이션 방식을 사용합니다.

실행 방법:
  cd backend/
  alembic upgrade head        # DB에 최신 마이그레이션 적용
  alembic downgrade base      # 모든 마이그레이션 롤백 (DB 초기화)
  alembic revision --autogenerate -m "설명"  # 변경사항 자동 감지 후 파일 생성
============================================================
"""

import asyncio  # 비동기 실행을 위한 표준 라이브러리
from logging.config import fileConfig  # alembic.ini의 로깅 설정 적용

from sqlalchemy import pool  # 커넥션 풀 설정
from sqlalchemy.engine import Connection  # 동기 커넥션 타입 힌트
from sqlalchemy.ext.asyncio import async_engine_from_config  # 비동기 엔진 생성

from alembic import context  # Alembic 런타임 컨텍스트 (설정, 메타데이터 등)

# ─── 우리 앱의 설정과 모델 가져오기 ───
# settings: .env 파일에서 DATABASE_URL 등 환경변수 로드
# Base: SQLAlchemy ORM의 DeclarativeBase (모든 모델의 부모 클래스)
from app.config import settings
from app.database import Base  # 모든 테이블 메타데이터가 여기에 등록됨

# ─── 모든 모델을 import하여 Base.metadata에 등록 ───
# Alembic이 autogenerate 시 모델 변경사항을 감지하려면
# 반드시 모든 모델 클래스가 import되어 있어야 합니다.
from app.models import (  # noqa: F401
    user,      # User 모델 (이메일, 비밀번호, 역할, 잠금)
    api_key,   # ApiKey 모델 (AES-256 암호화 API 키)
    bot,       # BotStatus 모델 (봇 설정, 성과 통계)
    trade,     # Trade 모델 (거래 내역)
    position,  # Position 모델 (보유 포지션)
    alert,     # Alert 모델 (알림, 일일 리포트)
)

# ─── alembic.ini의 로깅 설정 적용 ───
# alembic.ini 파일에 정의된 [loggers], [handlers], [formatters] 섹션 사용
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── 마이그레이션 대상 메타데이터 설정 ───
# Base.metadata: 모든 모델의 테이블 구조 정보
# autogenerate 기능이 이 메타데이터와 실제 DB를 비교하여 변경사항 감지
target_metadata = Base.metadata

# ─── DB URL을 환경변수에서 가져오기 ───
# alembic.ini의 sqlalchemy.url을 앱 설정의 DATABASE_URL로 오버라이드
# .env 파일의 DATABASE_URL이 실제로 사용됩니다.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """
    오프라인 모드에서 마이그레이션 실행.
    DB 연결 없이 SQL 스크립트만 생성합니다.

    사용 사례:
      - DB 접근 불가 환경에서 마이그레이션 SQL 미리 확인
      - DBA에게 SQL 파일로 전달할 때

    실행: alembic upgrade head --sql > migration.sql
    """
    # DB URL 가져오기 (alembic.ini 또는 set_main_option으로 설정된 값)
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # SQL 파라미터를 리터럴 값으로 표현
        dialect_opts={"paramstyle": "named"},  # PostgreSQL 파라미터 스타일
        compare_type=True,  # 컬럼 타입 변경도 감지 (중요!)
        compare_server_default=True,  # 서버 기본값 변경도 감지
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    실제 마이그레이션 실행 함수 (동기).
    비동기 컨텍스트에서 동기 Alembic API를 호출하는 브릿지 함수.

    Args:
        connection: SQLAlchemy 동기 커넥션 객체
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 컬럼 타입 변경 감지 (VARCHAR(50)→VARCHAR(100) 등)
        compare_server_default=True,  # DEFAULT 값 변경 감지
        # ─── 네이밍 컨벤션 ───
        # Alembic이 자동생성하는 제약조건명의 패턴을 명시합니다.
        # 이를 통해 마이그레이션 파일이 더 명확하고 일관성 있게 생성됩니다.
        render_as_batch=False,  # PostgreSQL은 batch 모드 불필요 (SQLite용)
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    비동기 모드에서 마이그레이션 실행.
    asyncpg 드라이버와 호환되도록 비동기 엔진을 사용합니다.

    흐름:
      1. alembic.ini 설정으로 비동기 엔진 생성
      2. 비동기 커넥션 획득
      3. 동기 함수(do_run_migrations)를 비동기로 실행 (sync_fallback)
      4. 엔진 종료 (커넥션 풀 정리)
    """
    # alembic.ini의 [alembic] 섹션 설정으로 비동기 엔진 생성
    # NullPool: 마이그레이션 완료 후 커넥션을 즉시 반환 (풀 미사용)
    # → 마이그레이션은 단발성 실행이므로 풀이 불필요
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 마이그레이션 후 커넥션 즉시 해제
    )

    async with connectable.connect() as connection:
        # sync_fallback: 비동기 커넥션에서 동기 함수를 안전하게 실행
        # Alembic의 내부 API는 동기식이므로 이 방식이 필요합니다.
        await connection.run_sync(do_run_migrations)

    # 엔진 종료 — 커넥션 풀과 리소스 정리
    await connectable.dispose()


def run_migrations_online() -> None:
    """
    온라인 모드에서 마이그레이션 실행 (일반적인 사용).
    asyncio.run()으로 비동기 마이그레이션 함수를 실행합니다.

    실행: alembic upgrade head
    """
    # asyncio.run(): 새로운 이벤트 루프를 생성하고 코루틴을 실행
    # FastAPI 앱과 별도로 마이그레이션만을 위한 이벤트 루프 사용
    asyncio.run(run_async_migrations())


# ─── 실행 모드 분기 ───
# Alembic이 --sql 플래그로 실행되면 오프라인 모드 (SQL 스크립트 생성)
# 그 외에는 온라인 모드 (실제 DB에 마이그레이션 적용)
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
