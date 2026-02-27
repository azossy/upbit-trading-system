"""
============================================================
봇 제어 API 라우터 (/api/v1/bot)
트레이딩 봇의 시작/정지/설정/상태 조회를 처리합니다.

엔드포인트:
  GET    /status         - 봇 현재 상태 조회
  POST   /start          - 봇 시작
  POST   /stop           - 봇 정지
  POST   /pause          - 봇 일시 정지
  PUT    /config         - 봇 설정 변경
  GET    /positions      - 현재 보유 포지션 조회
  GET    /trades         - 거래 내역 조회
  GET    /trades/summary - 거래 성과 요약
  POST   /api-keys       - API 키 등록
  GET    /api-keys       - API 키 목록
  DELETE /api-keys/{id}  - API 키 삭제
============================================================
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.database import get_db
from app.models.user import User
from app.models.bot import Bot, BotStatus, MarketMode
from app.models.trade import Trade
from app.models.position import Position
from app.models.api_key import ApiKey
from app.middleware.auth_middleware import get_current_user
from app.schemas.auth import (
    BotStatusResponse,
    BotConfigRequest,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    MessageResponse,
)
from app.utils.encryption import encrypt_api_key
from loguru import logger
from pydantic import BaseModel

# ─── 라우터 생성 ───
router = APIRouter(
    prefix="/api/v1/bot",
    tags=["봇 제어"],
)


# ─── 추가 응답 스키마 ───
class PositionResponse(BaseModel):
    """현재 보유 포지션 응답"""
    id: int
    coin: str
    position_type: str
    avg_entry_price: float
    total_quantity: float
    total_invested: float
    current_price: Optional[float]
    current_pnl_pct: float
    current_pnl_amount: float
    stop_loss_price: Optional[float]
    trailing_stop_active: bool
    highest_price: Optional[float]
    tp1_filled: bool
    tp2_filled: bool
    tp3_filled: bool
    opened_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """거래 내역 응답"""
    id: int
    coin: str
    side: str
    order_type: str
    reason: str
    price: float
    quantity: float
    total_amount: float
    fee: float
    realized_pnl: Optional[float]
    realized_pnl_pct: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class TradeSummaryResponse(BaseModel):
    """거래 성과 요약 응답"""
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    best_trade_pnl: float
    worst_trade_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float


# ─── 헬퍼 함수 ───
async def _get_or_create_bot(user: User, db: AsyncSession) -> Bot:
    """유저의 봇을 조회하거나, 없으면 새로 생성합니다."""
    result = await db.execute(
        select(Bot).where(Bot.user_id == user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        # 봇이 없으면 기본 설정으로 생성
        bot = Bot(
            user_id=user.id,
            status=BotStatus.STOPPED,
            market_mode=MarketMode.UNKNOWN,
            config={
                "max_investment_ratio": 0.5,
                "max_coins": 7,
                "atr_multiplier": 1.5,
                "min_stop_loss_pct": 1.5,
                "max_stop_loss_pct": 5.0,
                "trailing_stop_activation_pct": 15.0,
                "trailing_stop_distance_pct": 5.0,
            },
        )
        db.add(bot)
        await db.commit()
        await db.refresh(bot)

    return bot


# ─── 엔드포인트 ───

@router.get(
    "/status",
    response_model=BotStatusResponse,
    summary="봇 상태 조회",
    description="현재 봇의 상태, 시장 모드, 성과 통계를 조회합니다.",
)
async def get_bot_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """봇 상태 조회"""
    bot = await _get_or_create_bot(current_user, db)
    return BotStatusResponse.model_validate(bot)


@router.post(
    "/start",
    response_model=MessageResponse,
    summary="봇 시작",
    description="트레이딩 봇을 시작합니다. API 키가 등록되어 있어야 합니다.",
)
async def start_bot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    봇 시작.
    사전 조건: 활성화된 업비트 API 키가 등록되어 있어야 함.
    """
    bot = await _get_or_create_bot(current_user, db)

    # 이미 실행 중인지 확인
    if bot.status == BotStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="봇이 이미 실행 중입니다",
        )

    # API 키 등록 여부 확인
    api_key_result = await db.execute(
        select(ApiKey).where(
            and_(
                ApiKey.user_id == current_user.id,
                ApiKey.exchange == "upbit",
                ApiKey.is_active == True,
            )
        )
    )
    api_key = api_key_result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="활성화된 업비트 API 키가 필요합니다. 설정에서 API 키를 먼저 등록하세요.",
        )

    # 봇 상태 변경
    bot.status = BotStatus.RUNNING
    bot.started_at = datetime.utcnow()
    bot.stop_reason = None

    await db.commit()

    # TODO: Celery 태스크로 실제 트레이딩 엔진 시작
    # from app.trading.tasks import start_trading_engine
    # start_trading_engine.delay(bot.id, current_user.id)

    logger.info(f"[BOT] 봇 시작: user_id={current_user.id}")

    return MessageResponse(
        message="트레이딩 봇이 시작되었습니다",
        success=True,
    )


@router.post(
    "/stop",
    response_model=MessageResponse,
    summary="봇 정지",
    description="트레이딩 봇을 정지합니다.",
)
async def stop_bot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """봇 정지"""
    bot = await _get_or_create_bot(current_user, db)

    if bot.status == BotStatus.STOPPED:
        return MessageResponse(message="봇이 이미 정지 상태입니다")

    bot.status = BotStatus.STOPPED
    bot.stop_reason = "사용자 수동 정지"
    bot.stopped_at = datetime.utcnow()

    await db.commit()

    # TODO: Celery 태스크로 실제 트레이딩 엔진 정지 + 미체결 주문 취소
    logger.info(f"[BOT] 봇 정지: user_id={current_user.id}")

    return MessageResponse(
        message="트레이딩 봇이 정지되었습니다",
        success=True,
    )


@router.put(
    "/config",
    response_model=MessageResponse,
    summary="봇 설정 변경",
    description="봇의 투자 비율, 손절 기준 등을 변경합니다.",
)
async def update_bot_config(
    request: BotConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    봇 설정 변경.
    변경된 설정은 즉시 적용되지 않고, 다음 분석 사이클에서 반영됩니다.
    """
    bot = await _get_or_create_bot(current_user, db)

    # 기존 설정에 변경값만 업데이트
    config = bot.config or {}
    update_data = request.model_dump(exclude_none=True)

    for key, value in update_data.items():
        config[key] = value

    bot.config = config
    await db.commit()

    logger.info(f"[BOT] 설정 변경: user_id={current_user.id}, changes={update_data}")

    return MessageResponse(
        message="봇 설정이 변경되었습니다. 다음 분석 사이클에서 반영됩니다.",
        success=True,
    )


@router.get(
    "/positions",
    response_model=List[PositionResponse],
    summary="보유 포지션 조회",
    description="현재 보유 중인 코인 포지션 목록을 조회합니다.",
)
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_closed: bool = Query(False, description="청산된 포지션도 포함"),
):
    """보유 포지션 조회"""
    query = select(Position).where(Position.user_id == current_user.id)

    if not include_closed:
        query = query.where(Position.is_closed == False)

    query = query.order_by(desc(Position.opened_at))
    result = await db.execute(query)
    positions = result.scalars().all()

    return [PositionResponse.model_validate(p) for p in positions]


@router.get(
    "/trades",
    response_model=List[TradeResponse],
    summary="거래 내역 조회",
    description="거래 내역을 조회합니다. 날짜, 코인별 필터 가능.",
)
async def get_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    coin: Optional[str] = Query(None, description="코인 필터 (예: KRW-BTC)"),
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """거래 내역 조회 (페이지네이션)"""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Trade)
        .where(
            and_(
                Trade.user_id == current_user.id,
                Trade.created_at >= since,
            )
        )
    )

    if coin:
        query = query.where(Trade.coin == coin)

    query = query.order_by(desc(Trade.created_at))
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    trades = result.scalars().all()

    return [TradeResponse.model_validate(t) for t in trades]


@router.get(
    "/trades/summary",
    response_model=TradeSummaryResponse,
    summary="거래 성과 요약",
    description="전체 거래 성과를 요약합니다.",
)
async def get_trade_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """거래 성과 요약"""
    bot = await _get_or_create_bot(current_user, db)

    # 최고/최악 거래
    best = await db.scalar(
        select(func.max(Trade.realized_pnl)).where(
            and_(Trade.user_id == current_user.id, Trade.realized_pnl.isnot(None))
        )
    )
    worst = await db.scalar(
        select(func.min(Trade.realized_pnl)).where(
            and_(Trade.user_id == current_user.id, Trade.realized_pnl.isnot(None))
        )
    )
    avg_pnl = await db.scalar(
        select(func.avg(Trade.realized_pnl)).where(
            and_(Trade.user_id == current_user.id, Trade.realized_pnl.isnot(None))
        )
    )

    return TradeSummaryResponse(
        total_trades=bot.total_trades,
        win_count=bot.win_count,
        loss_count=bot.loss_count,
        win_rate=bot.win_rate,
        total_pnl=bot.total_pnl,
        avg_pnl_per_trade=round(avg_pnl or 0.0, 2),
        best_trade_pnl=round(best or 0.0, 2),
        worst_trade_pnl=round(worst or 0.0, 2),
        daily_pnl=bot.daily_pnl,
        weekly_pnl=bot.weekly_pnl,
        monthly_pnl=bot.monthly_pnl,
    )


# ─── API 키 관리 ───

@router.post(
    "/api-keys",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API 키 등록",
    description="거래소 API 키를 AES-256 암호화하여 안전하게 저장합니다.",
)
async def create_api_key(
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    API 키 등록.
    원문 API 키는 AES-256-GCM으로 암호화된 후 DB에 저장됩니다.
    원문은 서버 메모리에서만 일시적으로 사용되고 즉시 폐기됩니다.
    """
    # 같은 거래소에 이미 활성 키가 있는지 확인
    existing = await db.execute(
        select(ApiKey).where(
            and_(
                ApiKey.user_id == current_user.id,
                ApiKey.exchange == request.exchange,
                ApiKey.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이미 활성화된 {request.exchange} API 키가 있습니다. 기존 키를 삭제 후 등록하세요.",
        )

    # API 키 암호화
    encrypted_key = encrypt_api_key(request.api_key)
    encrypted_secret = encrypt_api_key(request.api_secret)

    # DB 저장
    api_key = ApiKey(
        user_id=current_user.id,
        exchange=request.exchange,
        label=request.label,
        encrypted_api_key=encrypted_key,
        encrypted_api_secret=encrypted_secret,
        ip_whitelist=request.ip_whitelist,
        permissions=request.permissions,
    )

    db.add(api_key)
    await db.commit()

    logger.info(
        f"[SECURITY] API 키 등록: user_id={current_user.id}, "
        f"exchange={request.exchange}"
    )

    return MessageResponse(
        message="API 키가 안전하게 등록되었습니다",
        success=True,
    )


@router.get(
    "/api-keys",
    response_model=List[ApiKeyResponse],
    summary="API 키 목록 조회",
    description="등록된 API 키 목록을 조회합니다. 원문은 표시되지 않습니다.",
)
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    API 키 목록 조회.
    ⚠ 원문 API 키는 절대 응답에 포함되지 않습니다.
    마지막 4자리만 마스킹하여 표시합니다.
    """
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id)
    )
    keys = result.scalars().all()

    response = []
    for key in keys:
        # 마스킹: 마지막 4자리만 표시
        # (실제로는 암호화된 값이므로, 라벨과 ID로만 구분)
        response.append(ApiKeyResponse(
            id=key.id,
            exchange=key.exchange,
            label=key.label,
            api_key_masked="****" + str(key.id).zfill(4),
            ip_whitelist=key.ip_whitelist,
            permissions=key.permissions,
            is_active=key.is_active,
            created_at=key.created_at,
        ))

    return response


@router.delete(
    "/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="API 키 삭제",
    description="등록된 API 키를 삭제합니다. 봇이 실행 중이면 삭제할 수 없습니다.",
)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API 키 삭제"""
    result = await db.execute(
        select(ApiKey).where(
            and_(
                ApiKey.id == key_id,
                ApiKey.user_id == current_user.id,
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API 키를 찾을 수 없습니다",
        )

    # 봇이 실행 중이면 삭제 불가
    bot_result = await db.execute(
        select(Bot).where(Bot.user_id == current_user.id)
    )
    bot = bot_result.scalar_one_or_none()
    if bot and bot.status == BotStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="봇이 실행 중일 때는 API 키를 삭제할 수 없습니다. 먼저 봇을 정지하세요.",
        )

    await db.delete(api_key)
    await db.commit()

    logger.info(f"[SECURITY] API 키 삭제: user_id={current_user.id}, key_id={key_id}")

    return MessageResponse(
        message="API 키가 삭제되었습니다",
        success=True,
    )
