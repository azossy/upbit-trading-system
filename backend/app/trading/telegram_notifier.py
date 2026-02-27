"""
============================================================
텔레그램 알림 모듈 (Telegram Notifier)
매매 실행, 손절/익절, 시스템 알림을 텔레그램으로 전송합니다.

알림 유형:
  - 매수 체결 알림 (코인, 가격, 투자금)
  - 매도 체결 알림 (코인, 가격, 손익)
  - 손절/익절 알림 (사유, 손익률)
  - 시장 분석 요약 (시장 모드, 점수)
  - 일일 성과 리포트 (승률, 총 손익)
  - 에러/경고 알림 (시스템 이상)

의존성:
  - python-telegram-bot 라이브러리 사용
  - TELEGRAM_BOT_TOKEN, TELEGRAM_DEFAULT_CHAT_ID 환경변수 필요
============================================================
"""

from typing import Optional
from datetime import datetime
from loguru import logger

# 텔레그램 봇 라이브러리
import telegram
from telegram.constants import ParseMode

from app.config import settings


class TelegramNotifier:
    """
    텔레그램 알림 발송기.

    각 알림 유형별 메서드를 제공하며,
    텔레그램 봇 토큰이 설정되지 않은 경우 자동으로 건너뜁니다.

    사용법:
        notifier = TelegramNotifier()
        await notifier.send_buy_alert("KRW-BTC", 50000000, 100000)
    """

    def __init__(self, chat_id: Optional[str] = None):
        """
        Args:
            chat_id: 수신할 텔레그램 채팅 ID (없으면 기본값 사용)
        """
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_DEFAULT_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            # 텔레그램 봇 인스턴스 생성
            self.bot = telegram.Bot(token=self.bot_token)
            logger.info("[TELEGRAM] 텔레그램 알림 활성화됨")
        else:
            self.bot = None
            logger.info("[TELEGRAM] 텔레그램 토큰/채팅ID 미설정 — 알림 비활성")

    async def _send(self, message: str):
        """
        텔레그램 메시지를 전송합니다 (내부 공통 메서드).

        Args:
            message: 전송할 메시지 (HTML 포맷 지원)
        """
        if not self.enabled:
            return  # 비활성 시 건너뜀

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML,  # HTML 태그 지원 (<b>, <i>, <code> 등)
            )
        except Exception as e:
            logger.error(f"[TELEGRAM] 메시지 전송 실패: {e}")

    # ══════════════════════════════════════════════════
    # 매수 체결 알림
    # ══════════════════════════════════════════════════

    async def send_buy_alert(
        self,
        coin: str,
        price: float,
        invest_amount: float,
        reasons: list = None,
    ):
        """
        매수 체결 알림을 전송합니다.

        Args:
            coin: 코인 마켓 코드 (예: "KRW-BTC")
            price: 체결 가격
            invest_amount: 투자 금액 (원)
            reasons: 매수 근거 목록
        """
        reasons_text = ""
        if reasons:
            reasons_text = "\n".join([f"  • {r}" for r in reasons])

        msg = (
            f"🟢 <b>매수 체결</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"코인: <code>{coin}</code>\n"
            f"가격: <code>{price:,.0f}</code>원\n"
            f"투자금: <code>{invest_amount:,.0f}</code>원\n"
        )
        if reasons_text:
            msg += f"\n📊 매수 근거:\n{reasons_text}\n"

        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        await self._send(msg)

    # ══════════════════════════════════════════════════
    # 매도 체결 알림
    # ══════════════════════════════════════════════════

    async def send_sell_alert(
        self,
        coin: str,
        price: float,
        pnl_amount: float,
        pnl_pct: float,
        reason: str = "",
    ):
        """
        매도 체결 알림을 전송합니다.

        Args:
            coin: 코인 마켓 코드
            price: 체결 가격
            pnl_amount: 실현 손익 (원)
            pnl_pct: 실현 손익률 (%)
            reason: 매도 사유 (손절/익절/트레일링 스탑 등)
        """
        # 수익이면 초록, 손실이면 빨강 이모지
        emoji = "🔴" if pnl_amount < 0 else "🟢"
        pnl_sign = "+" if pnl_amount >= 0 else ""

        msg = (
            f"{emoji} <b>매도 체결</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"코인: <code>{coin}</code>\n"
            f"가격: <code>{price:,.0f}</code>원\n"
            f"손익: <code>{pnl_sign}{pnl_amount:,.0f}</code>원 "
            f"(<code>{pnl_sign}{pnl_pct:.1f}%</code>)\n"
            f"사유: {reason}\n"
            f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        await self._send(msg)

    # ══════════════════════════════════════════════════
    # 시장 분석 요약 알림
    # ══════════════════════════════════════════════════

    async def send_market_summary(
        self,
        mode: str,
        score: int,
        details: dict = None,
    ):
        """
        시장 분석 요약 알림을 전송합니다.

        Args:
            mode: 시장 모드 ("BULL", "SIDEWAYS", "BEAR")
            score: 시장 점수 (0~100)
            details: 세부 분석 항목 딕셔너리
        """
        mode_emoji = {"BULL": "🐂", "SIDEWAYS": "➡️", "BEAR": "🐻"}.get(mode, "❓")
        mode_text = {"BULL": "상승장", "SIDEWAYS": "횡보장", "BEAR": "하락장"}.get(mode, "분석중")

        msg = (
            f"📊 <b>시장 분석 요약</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"시장 모드: {mode_emoji} <b>{mode_text}</b>\n"
            f"시장 점수: <code>{score}/100</code>\n"
        )

        if details:
            msg += (
                f"\n세부 지표:\n"
                f"  BTC 추세: {details.get('btc_trend', '-')}\n"
                f"  거래량: {details.get('volume', '-')}\n"
                f"  변동성: {details.get('volatility', '-')}\n"
                f"  심리: {details.get('fear_greed', '-')}\n"
                f"  알트 모멘텀: {details.get('altcoin_momentum', '-')}\n"
            )

        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        await self._send(msg)

    # ══════════════════════════════════════════════════
    # 일일 성과 리포트
    # ══════════════════════════════════════════════════

    async def send_daily_report(
        self,
        total_trades: int,
        win_count: int,
        loss_count: int,
        daily_pnl: float,
        total_pnl: float,
    ):
        """
        일일 성과 리포트를 전송합니다.

        매일 자정에 자동으로 전송됩니다.

        Args:
            total_trades: 당일 총 거래 횟수
            win_count: 당일 승리 횟수
            loss_count: 당일 패배 횟수
            daily_pnl: 당일 손익 (원)
            total_pnl: 누적 총 손익 (원)
        """
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"

        msg = (
            f"{pnl_emoji} <b>일일 성과 리포트</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"날짜: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"거래 횟수: {total_trades}회\n"
            f"승률: {win_rate:.1f}% ({win_count}승 / {loss_count}패)\n"
            f"당일 손익: {'+'if daily_pnl >= 0 else ''}{daily_pnl:,.0f}원\n"
            f"누적 손익: {'+'if total_pnl >= 0 else ''}{total_pnl:,.0f}원\n"
        )
        await self._send(msg)

    # ══════════════════════════════════════════════════
    # 시스템 에러 알림
    # ══════════════════════════════════════════════════

    async def send_error_alert(self, error_message: str):
        """
        시스템 에러/경고 알림을 전송합니다.

        Args:
            error_message: 에러 메시지
        """
        msg = (
            f"⚠️ <b>시스템 경고</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{error_message}\n"
            f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        await self._send(msg)
