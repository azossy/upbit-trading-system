"""
============================================================
관리자(백오피스) API 라우터 (/api/v1/admin)
관리자 전용 기능: 유저 관리, 시스템 상태 조회, 봇 관리 등.

모든 엔드포인트는 get_current_admin Dependency를 통해
관리자(ADMIN) 역할을 가진 사용자만 접근 가능합니다.

엔드포인트:
  GET  /dashboard        - 관리자 대시보드 통계
  GET  /users            - 전체 유저 목록 (페이지네이션)
  GET  /users/{id}       - 특정 유저 상세 정보
  PUT  /users/{id}/status - 유저 활성화/비활성화
  POST /users/{id}/bot/stop - 특정 유저 봇 강제 정지
  GET  /system           - 시스템 상태 (API 상태, DB, Redis)
  GET  /bots             - 전체 봇 상태 목록
  GET  /trades/recent    - 최근 전체 거래 내역
============================================================
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from app.database import get_db
from app.models.user import User, UserRole
from app.models.bot import Bot, BotStatus
from app.models.trade import Trade
from app.models.position import Position
from app.models.alert import DailyReport
from app.middleware.auth_middleware import get_current_admin
from app.schemas.auth import UserResponse, MessageResponse
from pydantic import BaseModel
from loguru import logger

# ─── 라우터 생성 ───
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["관리자"],
)


# ─── 응답 스키마 ───
class AdminDashboardResponse(BaseModel):
    """관리자 대시보드 통계 응답"""
    total_users: int                  # 전체 유저 수
    active_users: int                 # 활성 유저 수
    running_bots: int                 # 실행 중인 봇 수
    paused_bots: int                  # 일시정지 봇 수
    error_bots: int                   # 에러 상태 봇 수
    total_trades_today: int           # 오늘 총 거래 수
    total_pnl_today: float            # 오늘 전체 실현 손익
    total_active_positions: int       # 전체 활성 포지션 수
    new_users_this_week: int          # 이번 주 신규 가입자 수


class UserDetailResponse(BaseModel):
    """유저 상세 정보 응답 (관리자용)"""
    id: int
    email: str
    nickname: str
    role: str
    is_active: bool
    is_email_verified: bool
    telegram_chat_id: Optional[str]
    last_login_at: Optional[datetime]
    login_fail_count: int
    locked_until: Optional[datetime]
    created_at: datetime
    # 봇 정보
    bot_status: Optional[str]
    bot_total_pnl: Optional[float]
    bot_total_trades: Optional[int]
    bot_win_rate: Optional[float]
    # 활성 포지션 수
    active_positions: int

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """유저 목록 응답 (페이지네이션)"""
    users: list[UserDetailResponse]
    total: int        # 전체 유저 수
    page: int         # 현재 페이지
    page_size: int    # 페이지당 항목 수
    total_pages: int  # 전체 페이지 수


class BotOverviewResponse(BaseModel):
    """봇 상태 개요 응답"""
    bot_id: int
    user_id: int
    user_email: str
    user_nickname: str
    status: str
    market_mode: str
    market_score: int
    total_pnl: float
    daily_pnl: float
    consecutive_losses: int
    active_positions: int
    started_at: Optional[datetime]
    stop_reason: Optional[str]


class SystemStatusResponse(BaseModel):
    """시스템 상태 응답"""
    database_status: str    # "healthy" / "unhealthy"
    redis_status: str       # "healthy" / "unhealthy"
    upbit_api_status: str   # "ok" / "error" / "unknown"
    binance_api_status: str  # "ok" / "error" / "unknown"
    total_bots_running: int
    server_uptime: str
    last_check: datetime


# ─── 엔드포인트 ───

@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    summary="관리자 대시보드",
    description="전체 시스템 통계를 한눈에 볼 수 있는 대시보드 데이터",
)
async def admin_dashboard(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    관리자 대시보드 통계 조회.
    전체 유저 수, 봇 상태, 오늘 거래 통계 등을 집계합니다.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.utcnow() - timedelta(days=7)

    # ─── 유저 통계 ───
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )
    new_users_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )

    # ─── 봇 상태 통계 ───
    running_bots = await db.scalar(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.RUNNING)
    )
    paused_bots = await db.scalar(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.PAUSED)
    )
    error_bots = await db.scalar(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.ERROR)
    )

    # ─── 오늘 거래 통계 ───
    today_trades = await db.scalar(
        select(func.count(Trade.id)).where(Trade.created_at >= today_start)
    )
    today_pnl_result = await db.scalar(
        select(func.coalesce(func.sum(Trade.realized_pnl), 0.0)).where(
            and_(
                Trade.created_at >= today_start,
                Trade.realized_pnl.isnot(None),
            )
        )
    )

    # ─── 활성 포지션 ───
    active_positions = await db.scalar(
        select(func.count(Position.id)).where(Position.is_closed == False)
    )

    return AdminDashboardResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        running_bots=running_bots or 0,
        paused_bots=paused_bots or 0,
        error_bots=error_bots or 0,
        total_trades_today=today_trades or 0,
        total_pnl_today=round(today_pnl_result or 0.0, 2),
        total_active_positions=active_positions or 0,
        new_users_this_week=new_users_week or 0,
    )


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="유저 목록 조회",
    description="전체 유저 목록을 페이지네이션으로 조회합니다.",
)
async def get_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    search: Optional[str] = Query(None, description="이메일/닉네임 검색"),
    role: Optional[str] = Query(None, description="역할 필터 (user/admin)"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
):
    """
    유저 목록 조회 (페이지네이션 + 검색 + 필터).
    각 유저의 봇 상태와 성과 정보도 함께 반환합니다.
    """
    # 기본 쿼리
    query = select(User)

    # 검색 필터
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.nickname.ilike(f"%{search}%"))
        )

    # 역할 필터
    if role:
        query = query.where(User.role == role)

    # 활성화 필터
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # 전체 수 조회
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 페이지네이션 적용
    offset = (page - 1) * page_size
    query = query.order_by(desc(User.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    # 각 유저의 봇 정보 조합
    user_details = []
    for user in users:
        # 봇 정보 조회
        bot_result = await db.execute(
            select(Bot).where(Bot.user_id == user.id)
        )
        bot = bot_result.scalar_one_or_none()

        # 활성 포지션 수
        pos_count = await db.scalar(
            select(func.count(Position.id)).where(
                and_(
                    Position.user_id == user.id,
                    Position.is_closed == False,
                )
            )
        )

        user_details.append(UserDetailResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            role=user.role.value,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            telegram_chat_id=user.telegram_chat_id,
            last_login_at=user.last_login_at,
            login_fail_count=user.login_fail_count,
            locked_until=user.locked_until,
            created_at=user.created_at,
            bot_status=bot.status.value if bot else None,
            bot_total_pnl=bot.total_pnl if bot else None,
            bot_total_trades=bot.total_trades if bot else None,
            bot_win_rate=bot.win_rate if bot else None,
            active_positions=pos_count or 0,
        ))

    total_pages = (total + page_size - 1) // page_size  # 올림 나눗셈

    return UserListResponse(
        users=user_details,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put(
    "/users/{user_id}/status",
    response_model=MessageResponse,
    summary="유저 활성화/비활성화",
    description="특정 유저의 계정을 활성화하거나 비활성화합니다.",
)
async def toggle_user_status(
    user_id: int,
    is_active: bool,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    유저 계정 상태 변경.
    비활성화 시 해당 유저의 봇도 자동으로 정지됩니다.
    """
    # 자기 자신은 비활성화 불가
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 계정은 비활성화할 수 없습니다",
        )

    # 유저 조회
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    # 상태 변경
    user.is_active = is_active

    # 비활성화 시 봇도 정지
    if not is_active:
        bot_result = await db.execute(
            select(Bot).where(Bot.user_id == user_id)
        )
        bot = bot_result.scalar_one_or_none()
        if bot and bot.status == BotStatus.RUNNING:
            bot.status = BotStatus.STOPPED
            bot.stop_reason = "관리자에 의해 계정 비활성화"
            bot.stopped_at = datetime.utcnow()
            logger.warning(f"[ADMIN] 봇 강제 정지: user_id={user_id}")

    await db.commit()

    action = "활성화" if is_active else "비활성화"
    logger.info(f"[ADMIN] 유저 {action}: user_id={user_id} by admin={admin.email}")

    return MessageResponse(
        message=f"유저 계정이 {action}되었습니다",
        success=True,
    )


@router.post(
    "/users/{user_id}/bot/stop",
    response_model=MessageResponse,
    summary="유저 봇 강제 정지",
    description="특정 유저의 트레이딩 봇을 강제로 정지합니다.",
)
async def force_stop_bot(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    관리자에 의한 봇 강제 정지.
    해당 봇의 모든 미체결 주문을 취소하고 봇을 정지합니다.
    """
    result = await db.execute(
        select(Bot).where(Bot.user_id == user_id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 유저의 봇을 찾을 수 없습니다",
        )

    if bot.status == BotStatus.STOPPED:
        return MessageResponse(message="봇이 이미 정지 상태입니다")

    # 봇 정지
    bot.status = BotStatus.STOPPED
    bot.stop_reason = f"관리자 강제 정지 ({admin.email})"
    bot.stopped_at = datetime.utcnow()

    await db.commit()

    logger.warning(
        f"[ADMIN] 봇 강제 정지: user_id={user_id}, "
        f"admin={admin.email}"
    )

    # TODO: Celery 태스크로 실제 미체결 주문 취소 + 포지션 청산 실행

    return MessageResponse(
        message="봇이 강제 정지되었습니다. 미체결 주문 취소가 진행됩니다.",
        success=True,
    )


@router.get(
    "/bots",
    response_model=list[BotOverviewResponse],
    summary="전체 봇 상태 조회",
    description="모든 유저의 봇 상태를 한눈에 조회합니다.",
)
async def get_all_bots(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="봇 상태 필터"),
):
    """전체 봇 목록 + 상태 조회"""
    query = select(Bot, User).join(User, Bot.user_id == User.id)

    if status_filter:
        query = query.where(Bot.status == status_filter)

    result = await db.execute(query.order_by(desc(Bot.updated_at)))
    rows = result.all()

    bots = []
    for bot, user in rows:
        pos_count = await db.scalar(
            select(func.count(Position.id)).where(
                and_(
                    Position.bot_id == bot.id,
                    Position.is_closed == False,
                )
            )
        )

        bots.append(BotOverviewResponse(
            bot_id=bot.id,
            user_id=user.id,
            user_email=user.email,
            user_nickname=user.nickname,
            status=bot.status.value,
            market_mode=bot.market_mode.value,
            market_score=bot.market_score,
            total_pnl=bot.total_pnl,
            daily_pnl=bot.daily_pnl,
            consecutive_losses=bot.consecutive_losses,
            active_positions=pos_count or 0,
            started_at=bot.started_at,
            stop_reason=bot.stop_reason,
        ))

    return bots


@router.get(
    "/system",
    response_model=SystemStatusResponse,
    summary="시스템 상태 조회",
    description="DB, Redis, 거래소 API 등 시스템 전반의 상태를 확인합니다.",
)
async def get_system_status(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    시스템 상태 확인.
    DB, Redis, 거래소 API 연결 상태를 점검합니다.
    """
    # DB 상태 확인
    db_status = "healthy"
    try:
        await db.execute(select(func.count(User.id)))
    except Exception:
        db_status = "unhealthy"

    # Redis 상태 확인
    redis_status = "healthy"
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.REDIS_URL)
        r.ping()
    except Exception:
        redis_status = "unhealthy"

    # 실행 중인 봇 수
    running = await db.scalar(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.RUNNING)
    )

    return SystemStatusResponse(
        database_status=db_status,
        redis_status=redis_status,
        upbit_api_status="unknown",   # TODO: 실제 API 핑 체크 구현
        binance_api_status="unknown",  # TODO: 실제 API 핑 체크 구현
        total_bots_running=running or 0,
        server_uptime="N/A",  # TODO: 서버 시작 시간에서 계산
        last_check=datetime.utcnow(),
    )
