"""
============================================================
DB 모델 패키지
모든 SQLAlchemy 모델을 여기서 import하여 Alembic 및
애플리케이션에서 일괄 인식할 수 있도록 합니다.
============================================================
"""

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.bot import Bot, BotLog
from app.models.trade import Trade
from app.models.position import Position
from app.models.alert import Alert, DailyReport

# Alembic이 모든 모델을 감지할 수 있도록 __all__ 정의
__all__ = [
    "User",
    "ApiKey",
    "Bot",
    "BotLog",
    "Trade",
    "Position",
    "Alert",
    "DailyReport",
]
