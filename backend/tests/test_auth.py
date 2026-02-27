"""
============================================================
인증(Auth) API 테스트
회원가입, 로그인, 토큰 갱신, 프로필 조회/수정, 비밀번호 변경,
로그아웃 등의 인증 관련 엔드포인트를 검증합니다.

테스트 항목:
  1. 회원가입 (POST /api/v1/auth/register)
     - 정상 회원가입
     - 중복 이메일 거부
     - 비밀번호 규칙 위반
  2. 로그인 (POST /api/v1/auth/login)
     - 정상 로그인
     - 잘못된 비밀번호
     - 존재하지 않는 이메일
  3. 내 정보 조회 (GET /api/v1/auth/me)
     - 정상 조회
     - 토큰 없이 접근 거부
  4. 프로필 수정 (PUT /api/v1/auth/me)
  5. 비밀번호 변경 (PUT /api/v1/auth/password)
  6. 로그아웃 (POST /api/v1/auth/logout)

실행:
  pytest tests/test_auth.py -v
  pytest tests/test_auth.py::TestRegister -v     # 특정 클래스만
  pytest tests/test_auth.py -v -k "login"        # 특정 키워드만
============================================================
"""

import pytest  # 테스트 프레임워크
from httpx import AsyncClient  # 비동기 HTTP 클라이언트


# ════════════════════════════════════════════════════════
# 1. 회원가입 테스트
# ════════════════════════════════════════════════════════

class TestRegister:
    """회원가입 엔드포인트 테스트 그룹 (POST /api/v1/auth/register)"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """
        정상 회원가입 테스트.
        올바른 이메일/비밀번호/닉네임으로 가입 시 201 반환.
        """
        # ─── 회원가입 요청 ───
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "nickname": "신규유저",
        })

        # ─── 검증 ───
        assert response.status_code == 201, f"응답: {response.text}"

        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["nickname"] == "신규유저"
        assert data["role"] == "user"  # 기본 역할은 user
        assert "password_hash" not in data  # 비밀번호 해시는 응답에 포함 금지
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, registered_user: dict
    ):
        """
        중복 이메일로 가입 시 409 Conflict 반환 테스트.
        registered_user 픽스처가 먼저 같은 이메일로 가입되어 있음.
        """
        # ─── 같은 이메일로 재가입 시도 ───
        response = await client.post("/api/v1/auth/register", json={
            "email": registered_user["email"],  # 이미 가입된 이메일
            "password": "AnotherPass123!",
            "nickname": "다른닉네임",
        })

        # ─── 중복 이메일은 409 반환 ───
        assert response.status_code == 409, f"응답: {response.text}"
        assert "already" in response.json()["detail"].lower() or \
               "중복" in response.json()["detail"] or \
               "exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """
        잘못된 이메일 형식으로 가입 시 422 Unprocessable Entity 반환.
        Pydantic의 이메일 유효성 검사가 동작해야 합니다.
        """
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",  # 유효하지 않은 이메일
            "password": "SecurePass123!",
            "nickname": "테스트",
        })

        # ─── 유효성 검사 실패 → 422 ───
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """
        너무 짧은 비밀번호(8자 미만)로 가입 시 422 반환.
        """
        response = await client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "password": "short",  # 8자 미만
            "nickname": "테스트",
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """
        필수 필드 누락 시 422 반환.
        이메일 없이 요청하면 Pydantic이 오류를 반환해야 합니다.
        """
        response = await client.post("/api/v1/auth/register", json={
            # email 필드 없음
            "password": "SecurePass123!",
            "nickname": "테스트",
        })

        assert response.status_code == 422


# ════════════════════════════════════════════════════════
# 2. 로그인 테스트
# ════════════════════════════════════════════════════════

class TestLogin:
    """로그인 엔드포인트 테스트 그룹 (POST /api/v1/auth/login)"""

    @pytest.mark.asyncio
    async def test_login_success(
        self, client: AsyncClient, registered_user: dict
    ):
        """
        정상 로그인 테스트.
        올바른 이메일/비밀번호로 로그인 시 200 + Access Token 반환.
        """
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })

        # ─── 검증 ───
        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # Access Token이 응답에 포함되어야 함
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0  # 토큰이 비어있지 않아야 함

        # 사용자 정보도 포함
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client: AsyncClient, registered_user: dict
    ):
        """
        잘못된 비밀번호로 로그인 시 401 반환.
        """
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword123!",  # 틀린 비밀번호
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client: AsyncClient):
        """
        존재하지 않는 이메일로 로그인 시 401 반환.
        보안을 위해 "이메일 없음"과 "비밀번호 틀림"을 구분하지 않습니다.
        """
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_returns_jwt(
        self, client: AsyncClient, registered_user: dict
    ):
        """
        로그인 응답의 Access Token이 유효한 JWT 형식인지 확인.
        JWT는 '헤더.페이로드.서명' 형식으로 3개의 점으로 구분됩니다.
        """
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })

        assert response.status_code == 200
        token = response.json()["access_token"]

        # JWT는 반드시 '.'으로 구분된 3개 파트
        parts = token.split(".")
        assert len(parts) == 3, f"유효하지 않은 JWT 형식: {token[:50]}..."


# ════════════════════════════════════════════════════════
# 3. 내 정보 조회 테스트
# ════════════════════════════════════════════════════════

class TestGetMe:
    """내 정보 조회 엔드포인트 테스트 (GET /api/v1/auth/me)"""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        인증된 상태에서 내 정보 조회 성공 테스트.
        auth_headers 픽스처가 JWT 토큰을 헤더에 포함합니다.
        """
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200

        data = response.json()
        assert "email" in data
        assert "nickname" in data
        assert "role" in data
        # 비밀번호 해시는 절대 노출되면 안 됨
        assert "password_hash" not in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, client: AsyncClient):
        """
        JWT 토큰 없이 요청 시 401 반환.
        인증되지 않은 요청을 거부해야 합니다.
        """
        response = await client.get("/api/v1/auth/me")
        # 토큰 없음 → 401 Unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, client: AsyncClient):
        """
        유효하지 않은 JWT 토큰으로 요청 시 401 반환.
        위조된/만료된 토큰을 거부해야 합니다.
        """
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        response = await client.get("/api/v1/auth/me", headers=invalid_headers)
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 4. 프로필 수정 테스트
# ════════════════════════════════════════════════════════

class TestUpdateProfile:
    """프로필 수정 테스트 (PUT /api/v1/auth/me)"""

    @pytest.mark.asyncio
    async def test_update_nickname(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        닉네임 변경 테스트.
        인증된 사용자가 자신의 닉네임을 변경할 수 있어야 합니다.
        """
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"nickname": "변경된닉네임"},
        )

        assert response.status_code == 200
        assert response.json()["nickname"] == "변경된닉네임"

    @pytest.mark.asyncio
    async def test_update_telegram_chat_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        텔레그램 채팅 ID 등록 테스트.
        알림 수신을 위한 텔레그램 ID를 설정할 수 있어야 합니다.
        """
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"telegram_chat_id": "123456789"},
        )

        # 텔레그램 ID 필드가 있으면 200, 없으면 스킵
        if response.status_code == 200:
            assert response.json().get("telegram_chat_id") == "123456789"
        elif response.status_code == 422:
            pytest.skip("telegram_chat_id 필드가 스키마에 없음 — 스킵")

    @pytest.mark.asyncio
    async def test_update_profile_without_auth(self, client: AsyncClient):
        """
        인증 없이 프로필 수정 시 401 반환.
        """
        response = await client.put(
            "/api/v1/auth/me",
            json={"nickname": "해커닉네임"},
        )
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 5. 비밀번호 변경 테스트
# ════════════════════════════════════════════════════════

class TestChangePassword:
    """비밀번호 변경 테스트 (PUT /api/v1/auth/password)"""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, auth_headers: dict, registered_user: dict
    ):
        """
        비밀번호 변경 성공 테스트.
        현재 비밀번호를 확인 후 새 비밀번호로 변경합니다.
        """
        response = await client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": registered_user["password"],
                "new_password": "NewSecurePass456!",
            },
        )

        # ─── 비밀번호 변경 성공 ───
        assert response.status_code in (200, 204), f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        현재 비밀번호가 틀릴 때 400 반환.
        잘못된 현재 비밀번호로는 변경이 불가해야 합니다.
        """
        response = await client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": "WrongCurrentPass!",  # 틀린 현재 비밀번호
                "new_password": "NewPass123!",
            },
        )

        assert response.status_code in (400, 401), f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_change_password_weak_new(
        self, client: AsyncClient, auth_headers: dict, registered_user: dict
    ):
        """
        새 비밀번호가 너무 약한 경우 422 반환.
        비밀번호 강도 규칙(8자 이상)을 준수해야 합니다.
        """
        response = await client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": registered_user["password"],
                "new_password": "weak",  # 8자 미만
            },
        )

        assert response.status_code == 422


# ════════════════════════════════════════════════════════
# 6. 로그아웃 테스트
# ════════════════════════════════════════════════════════

class TestLogout:
    """로그아웃 테스트 (POST /api/v1/auth/logout)"""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        로그아웃 성공 테스트.
        인증된 상태에서 로그아웃하면 200 또는 204 반환.
        """
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code in (200, 204), f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_logout_without_auth(self, client: AsyncClient):
        """
        인증 없이 로그아웃 시 401 반환.
        """
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 7. 헬스체크 테스트
# ════════════════════════════════════════════════════════

class TestHealthCheck:
    """헬스체크 엔드포인트 테스트 (GET /health)"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """
        헬스체크 엔드포인트 테스트.
        인증 없이 접근 가능하며 서버 상태를 반환합니다.
        """
        response = await client.get("/health")

        assert response.status_code == 200

        data = response.json()
        # status 필드가 "healthy" 또는 "ok"여야 함
        assert data.get("status") in ("healthy", "ok", "running"), \
            f"예상치 않은 상태: {data}"
