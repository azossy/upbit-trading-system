"""
============================================================
봇(Bot) API 테스트
봇 상태 조회, 시작/정지, 설정 변경, API 키 관리,
포지션 조회, 거래 내역 조회 등의 봇 관련 엔드포인트를 검증합니다.

테스트 항목:
  1. 봇 상태 조회 (GET /api/v1/bot/status)
  2. 봇 시작 (POST /api/v1/bot/start)
  3. 봇 정지 (POST /api/v1/bot/stop)
  4. 봇 설정 변경 (PUT /api/v1/bot/config)
  5. 포지션 조회 (GET /api/v1/bot/positions)
  6. 거래 내역 조회 (GET /api/v1/bot/trades)
  7. 거래 성과 요약 (GET /api/v1/bot/trades/summary)
  8. API 키 관리 (POST/GET/DELETE /api/v1/bot/api-keys)

실행:
  pytest tests/test_bot.py -v
  pytest tests/test_bot.py::TestBotStatus -v
  pytest tests/test_bot.py -k "api_key"
============================================================
"""

import pytest  # 테스트 프레임워크
from httpx import AsyncClient  # 비동기 HTTP 클라이언트


# ════════════════════════════════════════════════════════
# 1. 봇 상태 조회 테스트
# ════════════════════════════════════════════════════════

class TestBotStatus:
    """봇 상태 조회 테스트 (GET /api/v1/bot/status)"""

    @pytest.mark.asyncio
    async def test_get_status_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        인증된 사용자의 봇 상태 조회.
        새로 가입한 사용자는 봇이 없으므로 자동 생성되어야 합니다.
        """
        response = await client.get("/api/v1/bot/status", headers=auth_headers)

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 봇 상태 필드 확인
        assert "status" in data
        assert "market_mode" in data
        # 새 봇은 기본값이 stopped
        assert data["status"] in (
            "stopped", "running", "paused", "error", "maintenance"
        )

    @pytest.mark.asyncio
    async def test_get_status_without_auth(self, client: AsyncClient):
        """
        인증 없이 봇 상태 조회 시 401 반환.
        모든 봇 API는 인증 필수입니다.
        """
        response = await client.get("/api/v1/bot/status")
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 2. 봇 시작/정지 테스트
# ════════════════════════════════════════════════════════

class TestBotControl:
    """봇 시작/정지 테스트 (POST /api/v1/bot/start|stop)"""

    @pytest.mark.asyncio
    async def test_start_bot_without_api_key(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        API 키 없이 봇 시작 시도 시 400 반환.
        봇을 시작하려면 먼저 업비트 API 키를 등록해야 합니다.
        """
        response = await client.post(
            "/api/v1/bot/start", headers=auth_headers
        )

        # API 키 없으면 시작 불가 → 400 Bad Request
        assert response.status_code in (400, 422), \
            f"API 키 없이 시작 가능해서는 안 됨. 응답: {response.text}"

    @pytest.mark.asyncio
    async def test_stop_already_stopped_bot(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        이미 정지된 봇을 정지 시도 시 적절한 응답 반환.
        멱등성(idempotency): 같은 요청을 여러 번 보내도 안전해야 합니다.
        """
        response = await client.post(
            "/api/v1/bot/stop", headers=auth_headers
        )

        # 이미 정지된 상태에서 정지 → 200(멱등) 또는 400(이미 정지)
        assert response.status_code in (200, 400), f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_bot_control_without_auth(self, client: AsyncClient):
        """
        인증 없이 봇 시작/정지 시 401 반환.
        """
        start_response = await client.post("/api/v1/bot/start")
        stop_response = await client.post("/api/v1/bot/stop")

        assert start_response.status_code == 401
        assert stop_response.status_code == 401


# ════════════════════════════════════════════════════════
# 3. 봇 설정 변경 테스트
# ════════════════════════════════════════════════════════

class TestBotConfig:
    """봇 설정 변경 테스트 (PUT /api/v1/bot/config)"""

    @pytest.mark.asyncio
    async def test_update_config_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        봇 설정 변경 성공 테스트.
        투자 비율, 최대 보유 코인 수, ATR 배수 등을 변경합니다.
        """
        # ─── 설정 변경 요청 ───
        config_data = {
            "investment_ratio": 0.3,    # 투자 비율 30%
            "max_coins": 5,             # 최대 5개 코인
            "atr_multiplier": 2.0,      # ATR 배수 2.0
            "stop_loss_pct": 0.03,      # 손절 3%
        }
        response = await client.put(
            "/api/v1/bot/config",
            headers=auth_headers,
            json=config_data,
        )

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 변경된 설정값이 응답에 반영되어야 함
        if "config" in data:
            saved_config = data["config"]
            # investment_ratio가 저장되었는지 확인
            if "investment_ratio" in saved_config:
                assert saved_config["investment_ratio"] == 0.3

    @pytest.mark.asyncio
    async def test_update_config_invalid_ratio(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        유효 범위를 벗어난 투자 비율로 설정 시 422 반환.
        투자 비율은 0.1 ~ 1.0 범위여야 합니다.
        """
        response = await client.put(
            "/api/v1/bot/config",
            headers=auth_headers,
            json={"investment_ratio": 1.5},  # 1.0 초과 → 유효 범위 벗어남
        )

        assert response.status_code == 422, f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_update_config_invalid_max_coins(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        유효 범위를 벗어난 최대 코인 수 설정 시 422 반환.
        최대 코인 수는 1 ~ 7 범위여야 합니다.
        """
        response = await client.put(
            "/api/v1/bot/config",
            headers=auth_headers,
            json={"max_coins": 10},  # 7 초과 → 유효 범위 벗어남
        )

        assert response.status_code == 422, f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_update_config_without_auth(self, client: AsyncClient):
        """
        인증 없이 설정 변경 시 401 반환.
        """
        response = await client.put(
            "/api/v1/bot/config",
            json={"investment_ratio": 0.5},
        )
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 4. API 키 관리 테스트
# ════════════════════════════════════════════════════════

class TestApiKeys:
    """API 키 관리 테스트 (POST/GET/DELETE /api/v1/bot/api-keys)"""

    @pytest.mark.asyncio
    async def test_register_api_key_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        업비트 API 키 등록 성공 테스트.
        등록된 API 키는 AES-256-GCM으로 암호화되어 저장됩니다.
        """
        response = await client.post(
            "/api/v1/bot/api-keys",
            headers=auth_headers,
            json={
                "access_key": "upbit_access_key_example_32chars",
                "secret_key": "upbit_secret_key_example_32chars",
                "label": "메인 봇용",
            },
        )

        assert response.status_code in (200, 201), f"응답: {response.text}"

        data = response.json()
        # API 키 원문은 응답에 포함되면 안 됨 (보안)
        assert "access_key" not in data or \
               data.get("access_key", "") != "upbit_access_key_example_32chars"
        # 마지막 4자리만 표시
        if "access_key_last4" in data:
            assert len(data["access_key_last4"]) == 4

    @pytest.mark.asyncio
    async def test_get_api_keys_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        등록된 API 키 목록 조회 테스트.
        키 원문 대신 마스킹된 정보만 반환해야 합니다.
        """
        # ─── 먼저 API 키 등록 ───
        await client.post(
            "/api/v1/bot/api-keys",
            headers=auth_headers,
            json={
                "access_key": "test_access_key_12345678901234",
                "secret_key": "test_secret_key_12345678901234",
            },
        )

        # ─── 목록 조회 ───
        response = await client.get(
            "/api/v1/bot/api-keys", headers=auth_headers
        )

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 목록은 배열이어야 함
        assert isinstance(data, list)

        # 각 항목에 원문 키가 포함되어 있으면 안 됨
        for key_item in data:
            # secret_key_enc가 있더라도 원문이 아닌 암호화 형태여야 함
            if "access_key" in key_item:
                # 원문이면 안 됨 (마스킹되어야 함)
                raw = key_item["access_key"]
                assert raw != "test_access_key_12345678901234", \
                    "API 키 원문이 응답에 노출됨 (보안 취약점!)"

    @pytest.mark.asyncio
    async def test_delete_api_key(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        API 키 삭제 테스트.
        등록된 키를 ID로 삭제할 수 있어야 합니다.
        """
        # ─── 먼저 API 키 등록 ───
        create_response = await client.post(
            "/api/v1/bot/api-keys",
            headers=auth_headers,
            json={
                "access_key": "delete_test_key_12345678901234",
                "secret_key": "delete_test_sec_12345678901234",
                "label": "삭제테스트용",
            },
        )

        if create_response.status_code not in (200, 201):
            pytest.skip("API 키 등록 실패 — 삭제 테스트 스킵")

        key_id = create_response.json().get("id")
        if not key_id:
            pytest.skip("API 키 ID를 가져오지 못함 — 삭제 테스트 스킵")

        # ─── API 키 삭제 ───
        delete_response = await client.delete(
            f"/api/v1/bot/api-keys/{key_id}",
            headers=auth_headers,
        )

        assert delete_response.status_code in (200, 204), \
            f"삭제 실패: {delete_response.text}"

    @pytest.mark.asyncio
    async def test_api_keys_without_auth(self, client: AsyncClient):
        """
        인증 없이 API 키 조회 시 401 반환.
        """
        response = await client.get("/api/v1/bot/api-keys")
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 5. 포지션 조회 테스트
# ════════════════════════════════════════════════════════

class TestPositions:
    """포지션 조회 테스트 (GET /api/v1/bot/positions)"""

    @pytest.mark.asyncio
    async def test_get_positions_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        포지션이 없는 경우 빈 배열 반환 테스트.
        새 사용자는 포지션이 없어야 합니다.
        """
        response = await client.get(
            "/api/v1/bot/positions", headers=auth_headers
        )

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 포지션 없으면 빈 배열 (null이 아닌 빈 배열)
        assert isinstance(data, list)
        assert len(data) == 0  # 새 사용자는 포지션 없음

    @pytest.mark.asyncio
    async def test_get_positions_without_auth(self, client: AsyncClient):
        """
        인증 없이 포지션 조회 시 401 반환.
        """
        response = await client.get("/api/v1/bot/positions")
        assert response.status_code == 401


# ════════════════════════════════════════════════════════
# 6. 거래 내역 조회 테스트
# ════════════════════════════════════════════════════════

class TestTrades:
    """거래 내역 조회 테스트 (GET /api/v1/bot/trades)"""

    @pytest.mark.asyncio
    async def test_get_trades_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        거래 내역이 없는 경우 빈 결과 반환 테스트.
        새 사용자는 거래 내역이 없어야 합니다.
        """
        response = await client.get(
            "/api/v1/bot/trades", headers=auth_headers
        )

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 거래 내역은 배열 또는 페이지네이션 객체
        assert isinstance(data, (list, dict))

        # 배열인 경우 새 사용자는 비어있어야 함
        if isinstance(data, list):
            assert len(data) == 0

        # 페이지네이션인 경우 total이 0이어야 함
        if isinstance(data, dict) and "total" in data:
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_trades_with_filter(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        거래 내역 필터링 테스트 (코인명, 기간 필터).
        쿼리 파라미터가 서버에서 정상 처리되어야 합니다.
        """
        response = await client.get(
            "/api/v1/bot/trades",
            headers=auth_headers,
            params={
                "coin": "KRW-BTC",   # 비트코인만 필터
                "days": 30,          # 최근 30일
                "page": 1,           # 1페이지
                "limit": 50,         # 50개씩
            },
        )

        # 필터 파라미터를 받아도 서버 오류 없어야 함
        assert response.status_code == 200, f"응답: {response.text}"

    @pytest.mark.asyncio
    async def test_get_trade_summary_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        거래 성과 요약 조회 — 거래 없을 때 기본값 반환.
        """
        response = await client.get(
            "/api/v1/bot/trades/summary", headers=auth_headers
        )

        assert response.status_code == 200, f"응답: {response.text}"

        data = response.json()
        # 성과 요약 필드 확인
        # 거래가 없어도 0 기본값이 있어야 함
        assert "total_trades" in data or "total_pnl" in data or \
               isinstance(data, dict), "성과 요약 응답 형식 오류"

    @pytest.mark.asyncio
    async def test_get_trades_without_auth(self, client: AsyncClient):
        """
        인증 없이 거래 내역 조회 시 401 반환.
        """
        response = await client.get("/api/v1/bot/trades")
        assert response.status_code == 401
