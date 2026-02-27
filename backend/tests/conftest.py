"""
============================================================
pytest 픽스처(Fixture) 설정 파일
모든 테스트에서 공통으로 사용하는 픽스처들을 정의합니다.

pytest는 conftest.py를 자동으로 읽어 픽스처를 로드합니다.
별도 import 없이 테스트 함수 파라미터로 주입할 수 있습니다.

사용 기술:
  - pytest-asyncio: 비동기 테스트 지원
  - httpx.AsyncClient: FastAPI 테스트 클라이언트
  - SQLite (in-memory): 테스트 전용 DB (PostgreSQL 불필요)
  - SQLAlchemy AsyncSession: 비동기 DB 세션

실행 방법:
  cd backend/
  pytest tests/ -v                          # 전체 테스트
  pytest tests/test_auth.py -v              # 인증 테스트만
  pytest tests/ -v --tb=short               # 짧은 에러 출력
  pytest tests/ -v -k "test_login"          # 특정 테스트만
============================================================
"""

import asyncio  # 이벤트 루프 설정
from typing import AsyncGenerator  # 타입 힌트 (async generator)

import pytest  # 테스트 프레임워크
import pytest_asyncio  # 비동기 pytest 플러그인
from httpx import AsyncClient, ASGITransport  # FastAPI 비동기 테스트 클라이언트
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)  # 비동기 SQLAlchemy

# ─── FastAPI 앱 및 DB 설정 가져오기 ───
from main import app  # FastAPI 앱 엔트리포인트
from app.database import Base, get_db  # DB 베이스 클래스 + 의존성


# ─── 테스트 전용 DB URL ───
# SQLite in-memory 사용: 빠르고, PostgreSQL 설치 불필요, 테스트 후 자동 삭제
# aiosqlite: SQLite의 비동기 드라이버
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ─── pytest-asyncio 이벤트 루프 모드 설정 ───
# "auto": 모든 비동기 테스트에 자동으로 이벤트 루프 적용
# pytest.ini 또는 pyproject.toml에서도 설정 가능
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop():
    """
    테스트 세션 전체에서 공유하는 asyncio 이벤트 루프.
    scope="session": 세션당 1개 루프 (기본 "function"보다 효율적)

    Yields:
        asyncio.AbstractEventLoop: 공유 이벤트 루프
    """
    # 새 이벤트 루프 생성 (기존 루프와 충돌 방지)
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()  # 세션 종료 후 루프 정리


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 SQLite in-memory 데이터베이스 세션.
    각 테스트 함수마다 새로운 DB를 생성하고 테스트 후 삭제합니다.

    scope="function": 각 테스트마다 독립된 DB (데이터 격리)

    흐름:
      1. SQLite in-memory 엔진 생성
      2. Base.metadata.create_all()로 테이블 생성
      3. 세션 생성 → 테스트에 제공
      4. 테스트 완료 후 테이블 DROP

    Yields:
        AsyncSession: 테스트용 DB 세션
    """
    # ─── 1. 테스트 전용 비동기 엔진 생성 ───
    # check_same_thread=False: SQLite 멀티스레드 허용 (asyncio에 필요)
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite 특수 설정
        echo=False,  # SQL 쿼리 로그 비활성화 (필요 시 True로 변경)
    )

    # ─── 2. 모든 테이블 생성 ───
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ─── 3. 테스트용 세션 팩토리 생성 ───
    TestSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,  # commit 후에도 객체 속성 유지
        class_=AsyncSession,
    )

    # ─── 4. 세션 생성 및 테스트에 제공 ───
    async with TestSessionLocal() as session:
        yield session  # 테스트 함수에 세션 제공

    # ─── 5. 테스트 완료 후 테이블 삭제 (다음 테스트를 위한 초기화) ───
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # ─── 6. 엔진 종료 (커넥션 풀 정리) ───
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI 테스트 클라이언트.
    실제 HTTP 요청 없이 FastAPI 엔드포인트를 직접 호출합니다.

    의존성 오버라이드(override) 패턴:
      FastAPI의 get_db() 의존성을 test_db 세션으로 교체합니다.
      → 실제 PostgreSQL 대신 SQLite in-memory 사용

    Args:
        test_db: test_db 픽스처에서 제공된 DB 세션

    Yields:
        AsyncClient: httpx 비동기 클라이언트
    """
    # ─── FastAPI의 DB 의존성을 테스트 세션으로 오버라이드 ───
    async def override_get_db():
        """
        기존 get_db() 의존성을 test_db 세션으로 대체.
        실제 PostgreSQL 대신 SQLite in-memory를 사용합니다.
        """
        yield test_db  # 테스트용 세션 반환

    # ─── 의존성 교체 ───
    app.dependency_overrides[get_db] = override_get_db

    # ─── httpx 비동기 클라이언트 생성 ───
    # ASGITransport: ASGI 앱을 직접 호출 (실제 서버 필요 없음)
    # base_url: 요청 URL의 기본 경로
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac  # 테스트 함수에 클라이언트 제공

    # ─── 테스트 완료 후 의존성 오버라이드 초기화 ───
    # 다른 테스트에 영향을 주지 않도록 초기화
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """
    테스트용 기등록 사용자.
    회원가입 API를 호출하여 사용자를 생성하고 정보를 반환합니다.

    다른 테스트에서 '이미 등록된 사용자'가 필요할 때 이 픽스처를 사용합니다.

    Args:
        client: 테스트 클라이언트

    Returns:
        dict: {email, password, nickname, ...응답 데이터}
    """
    # ─── 회원가입 요청 ───
    user_data = {
        "email": "test@example.com",
        "password": "TestPass123!",
        "nickname": "테스트유저",
    }
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201, f"회원가입 실패: {response.text}"

    return {**user_data, **response.json()}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict:
    """
    인증된 사용자의 JWT 헤더.
    로그인하여 Access Token을 발급받고 Authorization 헤더를 반환합니다.

    인증이 필요한 엔드포인트 테스트 시 이 픽스처를 사용합니다.

    Args:
        client: 테스트 클라이언트
        registered_user: 기등록 사용자 정보

    Returns:
        dict: {"Authorization": "Bearer <access_token>"}
    """
    # ─── 로그인 요청 ───
    login_data = {
        "email": registered_user["email"],
        "password": registered_user["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200, f"로그인 실패: {response.text}"

    # ─── Access Token 추출 ───
    token = response.json()["access_token"]

    # ─── Authorization 헤더 반환 ───
    return {"Authorization": f"Bearer {token}"}
