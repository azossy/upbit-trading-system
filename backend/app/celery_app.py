"""
============================================================
Celery 앱 설정
트레이딩 봇의 비동기 작업을 처리하는 Celery 워커 설정.
브로커: Redis (redis://redis:6379/1)
큐: trading (봇 실행), default (일반 작업)
============================================================
"""

from celery import Celery
from app.config import settings

# ─── Celery 앱 인스턴스 생성 ───
celery_app = Celery(
    "upbit_trading",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=[
        # 실제 트레이딩 태스크가 추가되면 여기에 등록
        # "app.trading.tasks",
    ],
)

# ─── Celery 설정 ───
celery_app.conf.update(
    # 작업 직렬화 형식
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 타임존
    timezone="Asia/Seoul",
    enable_utc=True,

    # 태스크 결과 보관 시간 (1시간)
    result_expires=3600,

    # 큐 라우팅
    task_routes={
        "app.trading.tasks.*": {"queue": "trading"},
    },

    # 워커 설정
    worker_prefetch_multiplier=1,   # 한 번에 하나씩 처리 (트레이딩 안전성)
    task_acks_late=True,            # 작업 완료 후 ack (크래시 시 재처리)

    # Beat 스케줄 (주기적 작업)
    beat_schedule={
        # 예시: 1분마다 시장 분석
        # "analyze-market-every-minute": {
        #     "task": "app.trading.tasks.analyze_market",
        #     "schedule": 60.0,
        # },
    },
)

# ─── Flask-style 앱 참조 (Celery -A app.celery_app 명령용) ───
# docker-compose에서 `celery -A app.celery_app worker` 실행 시
# 이 모듈의 celery_app 인스턴스를 사용합니다.
