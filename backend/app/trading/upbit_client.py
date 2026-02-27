"""
============================================================
업비트 API 클라이언트 래퍼
REST API + WebSocket을 통합 관리하는 비동기 클라이언트입니다.

주요 기능:
  - REST API: 잔고 조회, 주문 실행, 캔들 데이터 조회
  - WebSocket: 실시간 시세(Ticker), 호가(Orderbook) 수신
  - JWT 인증: 업비트 API 요구사항에 맞는 JWT 토큰 자동 생성
  - Rate Limiting: 초당 요청 제한 준수 (초당 10회)
============================================================
"""

import jwt               # PyJWT — 업비트 API 인증용 JWT 생성
import uuid              # UUID — 업비트 API의 nonce 값 생성
import hashlib            # 해시 — 쿼리스트링 해싱 (SHA-512)
import time               # 시간 — Rate Limiting 제어
import json               # JSON — WebSocket 메시지 파싱
import asyncio            # 비동기 — 동시성 제어
from urllib.parse import urlencode, unquote  # URL 인코딩 — 쿼리 파라미터 처리
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

import httpx              # 비동기 HTTP 클라이언트 — REST API 호출
import websockets         # WebSocket 클라이언트 — 실시간 데이터 수신
from loguru import logger


# ─── 업비트 API 기본 URL ───
UPBIT_REST_URL = "https://api.upbit.com/v1"
UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"


class UpbitClient:
    """
    업비트 거래소 API 비동기 클라이언트.

    사용법:
        client = UpbitClient(access_key="...", secret_key="...")
        balance = await client.get_balance()
        await client.place_order("KRW-BTC", "bid", price=50000000, volume=0.001)

    Rate Limiting:
        업비트 API는 초당 10회 제한이므로, 내부적으로 요청 간격을 제어합니다.
    """

    def __init__(self, access_key: str, secret_key: str):
        """
        Args:
            access_key: 업비트 API Access Key
            secret_key: 업비트 API Secret Key
        """
        self.access_key = access_key  # 업비트 API 인증 키
        self.secret_key = secret_key  # 업비트 API 비밀 키
        self._last_request_time = 0.0  # 마지막 API 요청 시간 (Rate Limiting용)
        self._request_interval = 0.1   # 요청 간 최소 간격 (초) — 초당 10회 제한
        self._lock = asyncio.Lock()    # 동시 요청 방지용 락

    # ─── JWT 토큰 생성 ───
    def _create_token(self, query: Optional[Dict] = None) -> str:
        """
        업비트 API 인증용 JWT 토큰을 생성합니다.

        업비트 API는 각 요청마다 고유한 JWT 토큰이 필요합니다.
        쿼리 파라미터가 있는 경우 SHA-512 해시를 포함해야 합니다.

        Args:
            query: API 요청의 쿼리 파라미터 딕셔너리

        Returns:
            Bearer 접두사가 포함된 JWT 토큰 문자열
        """
        # JWT 페이로드 구성
        payload = {
            "access_key": self.access_key,     # API Access Key
            "nonce": str(uuid.uuid4()),         # 요청마다 고유한 값 (재전송 공격 방지)
        }

        # 쿼리 파라미터가 있으면 해시를 페이로드에 추가
        if query:
            # 쿼리스트링을 SHA-512로 해싱 (업비트 API 요구사항)
            query_string = unquote(urlencode(query, doseq=True))
            query_hash = hashlib.sha512(query_string.encode()).hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        # JWT 토큰 생성 (HS256 알고리즘)
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return f"Bearer {token}"

    # ─── Rate Limiting 적용 요청 ───
    async def _rate_limited_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict:
        """
        Rate Limiting이 적용된 HTTP 요청을 실행합니다.

        업비트 API는 초당 10회 요청 제한이 있으므로,
        최소 0.1초 간격으로 요청을 보냅니다.

        Args:
            method: HTTP 메서드 ("GET", "POST", "DELETE")
            url: 요청 URL
            **kwargs: httpx 요청에 전달할 추가 인자

        Returns:
            API 응답 JSON 딕셔너리

        Raises:
            httpx.HTTPStatusError: API 응답이 4xx/5xx인 경우
        """
        async with self._lock:
            # Rate Limiting: 최소 간격 보장
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._request_interval:
                await asyncio.sleep(self._request_interval - elapsed)

            # HTTP 요청 실행
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                self._last_request_time = time.time()
                response.raise_for_status()  # 에러 응답 시 예외 발생
                return response.json()

    # ══════════════════════════════════════════════════
    # REST API — 계좌/잔고 관련
    # ══════════════════════════════════════════════════

    async def get_accounts(self) -> List[Dict]:
        """
        전체 계좌 잔고를 조회합니다.

        Returns:
            계좌 목록 (각 코인별 잔고 정보 포함)
            예: [{"currency": "KRW", "balance": "1000000", ...}, ...]
        """
        url = f"{UPBIT_REST_URL}/accounts"
        headers = {"Authorization": self._create_token()}
        return await self._rate_limited_request("GET", url, headers=headers)

    async def get_krw_balance(self) -> float:
        """
        원화(KRW) 가용 잔고만 조회합니다.

        Returns:
            원화 잔고 (float)
        """
        accounts = await self.get_accounts()
        for acc in accounts:
            if acc["currency"] == "KRW":
                # balance: 주문 가능 금액, locked: 주문 중 동결 금액
                return float(acc.get("balance", 0))
        return 0.0

    # ══════════════════════════════════════════════════
    # REST API — 시세 데이터
    # ══════════════════════════════════════════════════

    async def get_ticker(self, markets: List[str]) -> List[Dict]:
        """
        현재가 정보를 조회합니다 (여러 마켓 동시 조회 가능).

        Args:
            markets: 마켓 코드 리스트 (예: ["KRW-BTC", "KRW-ETH"])

        Returns:
            마켓별 현재가 정보 리스트
        """
        url = f"{UPBIT_REST_URL}/ticker"
        params = {"markets": ",".join(markets)}
        return await self._rate_limited_request("GET", url, params=params)

    async def get_candles(
        self,
        market: str,
        interval: str = "minutes/15",
        count: int = 200,
    ) -> List[Dict]:
        """
        캔들(OHLCV) 데이터를 조회합니다.

        기술적 지표 계산에 필요한 과거 가격 데이터를 가져옵니다.

        Args:
            market: 마켓 코드 (예: "KRW-BTC")
            interval: 캔들 간격
                - "minutes/1", "minutes/3", "minutes/5", "minutes/15",
                  "minutes/30", "minutes/60", "minutes/240"
                - "days", "weeks", "months"
            count: 조회할 캔들 개수 (최대 200)

        Returns:
            캔들 데이터 리스트 (최신 → 과거 순)
        """
        url = f"{UPBIT_REST_URL}/candles/{interval}"
        params = {"market": market, "count": count}
        return await self._rate_limited_request("GET", url, params=params)

    async def get_orderbook(self, markets: List[str]) -> List[Dict]:
        """
        호가(Orderbook) 정보를 조회합니다.

        Args:
            markets: 마켓 코드 리스트

        Returns:
            마켓별 호가 정보 (매수/매도 호가 15단계)
        """
        url = f"{UPBIT_REST_URL}/orderbook"
        params = {"markets": ",".join(markets)}
        return await self._rate_limited_request("GET", url, params=params)

    async def get_market_list(self) -> List[Dict]:
        """
        업비트에 상장된 전체 마켓 목록을 조회합니다.
        KRW 마켓만 필터링하여 반환합니다.

        Returns:
            KRW 마켓 목록 (예: [{"market": "KRW-BTC", "korean_name": "비트코인"}, ...])
        """
        url = f"{UPBIT_REST_URL}/market/all"
        params = {"isDetails": "true"}
        all_markets = await self._rate_limited_request("GET", url, params=params)
        # KRW 마켓만 필터링 (원화 거래 마켓)
        return [m for m in all_markets if m["market"].startswith("KRW-")]

    # ══════════════════════════════════════════════════
    # REST API — 주문 실행
    # ══════════════════════════════════════════════════

    async def place_order(
        self,
        market: str,
        side: str,
        volume: Optional[float] = None,
        price: Optional[float] = None,
        ord_type: str = "limit",
    ) -> Dict:
        """
        주문을 실행합니다.

        Args:
            market: 마켓 코드 (예: "KRW-BTC")
            side: "bid" (매수) 또는 "ask" (매도)
            volume: 주문 수량 (지정가/시장가 매도 시 필수)
            price: 주문 가격 (지정가/시장가 매수 시 필수)
            ord_type: 주문 유형
                - "limit": 지정가 (price, volume 모두 필요)
                - "price": 시장가 매수 (price = 총 투자금액)
                - "market": 시장가 매도 (volume = 매도 수량)

        Returns:
            주문 결과 정보 (uuid, side, ord_type 등)

        Raises:
            ValueError: 잘못된 파라미터 조합
        """
        url = f"{UPBIT_REST_URL}/orders"

        # 주문 파라미터 구성
        query = {
            "market": market,
            "side": side,
            "ord_type": ord_type,
        }
        if volume is not None:
            query["volume"] = str(volume)
        if price is not None:
            query["price"] = str(price)

        headers = {"Authorization": self._create_token(query)}

        logger.info(
            f"[ORDER] 주문 실행: market={market}, side={side}, "
            f"type={ord_type}, price={price}, volume={volume}"
        )

        return await self._rate_limited_request(
            "POST", url, headers=headers, json=query
        )

    async def cancel_order(self, order_uuid: str) -> Dict:
        """
        미체결 주문을 취소합니다.

        Args:
            order_uuid: 취소할 주문의 UUID

        Returns:
            취소된 주문 정보
        """
        url = f"{UPBIT_REST_URL}/order"
        query = {"uuid": order_uuid}
        headers = {"Authorization": self._create_token(query)}
        return await self._rate_limited_request(
            "DELETE", url, headers=headers, params=query
        )

    async def get_order(self, order_uuid: str) -> Dict:
        """
        개별 주문 상세 정보를 조회합니다.

        Args:
            order_uuid: 조회할 주문의 UUID

        Returns:
            주문 상세 정보 (체결 여부, 수량, 가격 등)
        """
        url = f"{UPBIT_REST_URL}/order"
        query = {"uuid": order_uuid}
        headers = {"Authorization": self._create_token(query)}
        return await self._rate_limited_request(
            "GET", url, headers=headers, params=query
        )

    # ══════════════════════════════════════════════════
    # WebSocket — 실시간 데이터 수신
    # ══════════════════════════════════════════════════

    async def subscribe_ticker(
        self,
        markets: List[str],
        callback: Callable[[Dict], Any],
    ):
        """
        실시간 시세(Ticker) 데이터를 WebSocket으로 구독합니다.

        연결이 끊어지면 자동으로 재연결을 시도합니다 (최대 5회).

        Args:
            markets: 구독할 마켓 코드 리스트 (예: ["KRW-BTC", "KRW-ETH"])
            callback: 시세 데이터 수신 시 호출할 콜백 함수
        """
        # WebSocket 구독 메시지 구성
        subscribe_msg = [
            {"ticket": str(uuid.uuid4())},            # 구독 식별자
            {"type": "ticker", "codes": markets},      # 시세 타입 + 마켓 코드
            {"format": "DEFAULT"},                     # 응답 포맷
        ]

        retry_count = 0       # 재연결 시도 횟수
        max_retries = 5       # 최대 재연결 횟수

        while retry_count < max_retries:
            try:
                # WebSocket 연결
                async with websockets.connect(
                    UPBIT_WS_URL,
                    ping_interval=30,    # 30초마다 ping 전송 (연결 유지)
                    ping_timeout=10,     # 10초 내 pong 응답 없으면 끊김 처리
                ) as ws:
                    # 구독 요청 전송
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"[WS] 실시간 시세 구독 시작: {len(markets)}개 마켓")
                    retry_count = 0  # 연결 성공 시 재시도 카운터 리셋

                    # 데이터 수신 루프
                    async for message in ws:
                        try:
                            # 바이너리 → JSON 파싱
                            data = json.loads(message)
                            await callback(data)  # 콜백 함수 호출
                        except json.JSONDecodeError:
                            logger.warning("[WS] JSON 파싱 실패, 메시지 무시")
                        except Exception as e:
                            logger.error(f"[WS] 콜백 처리 오류: {e}")

            except websockets.exceptions.ConnectionClosed:
                retry_count += 1
                wait_time = min(2 ** retry_count, 30)  # 지수 백오프 (최대 30초)
                logger.warning(
                    f"[WS] 연결 끊김 — {wait_time}초 후 재연결 "
                    f"({retry_count}/{max_retries})"
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                retry_count += 1
                logger.error(f"[WS] WebSocket 오류: {e}")
                await asyncio.sleep(5)

        logger.error("[WS] 최대 재연결 횟수 초과 — WebSocket 구독 종료")
