/**
 * ============================================================
 * 대시보드 페이지 컴포넌트
 * 봇 상태, 수익률 차트, 보유 포지션, 시장 분석 결과를
 * 한 화면에서 확인할 수 있는 메인 대시보드입니다.
 *
 * 구성:
 *   1. 봇 상태 카드 (시작/정지 버튼 + 상태 표시)
 *   2. 수익률 통계 카드 (일/주/월 수익률)
 *   3. 수익률 차트 (Recharts 라인 차트)
 *   4. 보유 포지션 테이블
 *   5. 시장 분석 카드 (시장 모드 + 점수)
 * ============================================================
 */
import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
} from "recharts";
import toast from "react-hot-toast";
import clsx from "clsx";
import useStore from "../store/useStore";

function DashboardPage() {
  // ─── 전역 상태 ───
  const {
    botStatus, botLoading, fetchBotStatus,
    startBot, stopBot,
    positions, fetchPositions,
    tradeSummary, fetchTradeSummary,
  } = useStore();

  // ─── 로컬 상태 ───
  const [actionLoading, setActionLoading] = useState(false); // 봇 시작/정지 로딩

  // ─── 초기 데이터 로드 ───
  useEffect(() => {
    fetchBotStatus();
    fetchPositions();
    fetchTradeSummary();

    // 30초마다 자동 갱신 (실시간 느낌)
    const interval = setInterval(() => {
      fetchBotStatus();
      fetchPositions();
    }, 30000);

    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * 봇 시작/정지 토글 핸들러
   */
  const handleBotToggle = async () => {
    setActionLoading(true);
    try {
      if (botStatus?.status === "running") {
        // 봇 정지
        const result = await stopBot();
        if (result.success) toast.success("봇이 정지되었습니다");
        else toast.error(result.error);
      } else {
        // 봇 시작
        const result = await startBot();
        if (result.success) toast.success("봇이 시작되었습니다!");
        else toast.error(result.error);
      }
    } finally {
      setActionLoading(false);
    }
  };

  // ─── 수익률 차트 샘플 데이터 (실제로는 API에서 가져옴) ───
  const chartData = [
    { date: "1일", pnl: 0 },
    { date: "2일", pnl: 1.2 },
    { date: "3일", pnl: -0.5 },
    { date: "4일", pnl: 0.8 },
    { date: "5일", pnl: 2.1 },
    { date: "6일", pnl: 1.5 },
    { date: "7일", pnl: 3.2 },
  ];

  return (
    <div className="space-y-6">
      {/* ══════════ 상단: 봇 상태 + 통계 카드 ══════════ */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* ── 카드 1: 봇 상태 + 시작/정지 ── */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm text-gray-400">봇 상태</h3>
            <span
              className={clsx(
                "px-2 py-0.5 rounded-full text-xs font-medium",
                botStatus?.status === "running"
                  ? "bg-green-900 text-green-300"
                  : "bg-gray-700 text-gray-300"
              )}
            >
              {botStatus?.status === "running" ? "실행 중" : "정지됨"}
            </span>
          </div>
          <button
            onClick={handleBotToggle}
            disabled={actionLoading || botLoading}
            className={clsx(
              "w-full py-2 rounded-lg font-medium text-sm transition-colors",
              botStatus?.status === "running"
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-green-600 hover:bg-green-700 text-white",
              (actionLoading || botLoading) && "opacity-50 cursor-not-allowed"
            )}
          >
            {actionLoading
              ? "처리 중..."
              : botStatus?.status === "running"
                ? "봇 정지"
                : "봇 시작"}
          </button>
        </div>

        {/* ── 카드 2: 일일 수익률 ── */}
        <StatCard
          label="일일 수익률"
          value={tradeSummary?.daily_pnl ?? 0}
          suffix="%"
          isPercent
        />

        {/* ── 카드 3: 주간 수익률 ── */}
        <StatCard
          label="주간 수익률"
          value={tradeSummary?.weekly_pnl ?? 0}
          suffix="%"
          isPercent
        />

        {/* ── 카드 4: 승률 ── */}
        <StatCard
          label="승률"
          value={tradeSummary?.win_rate ?? 0}
          suffix="%"
        />
      </div>

      {/* ══════════ 중간: 수익률 차트 + 시장 분석 ══════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ── 수익률 차트 (2/3 너비) ── */}
        <div className="card lg:col-span-2">
          <h3 className="text-sm text-gray-400 mb-4">누적 수익률 추이</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  {/* 그라데이션 정의 (양수=초록, 음수=빨강) */}
                  <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="pnl"
                  stroke="#10b981"
                  fill="url(#pnlGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ── 시장 분석 카드 (1/3 너비) ── */}
        <div className="card">
          <h3 className="text-sm text-gray-400 mb-4">시장 분석</h3>
          <div className="text-center py-4">
            {/* 시장 모드 뱃지 */}
            <div
              className={clsx(
                "inline-block px-4 py-2 rounded-full text-lg font-bold mb-3",
                botStatus?.market_mode === "BULL"
                  ? "bg-green-900 text-green-300"
                  : botStatus?.market_mode === "BEAR"
                    ? "bg-red-900 text-red-300"
                    : "bg-yellow-900 text-yellow-300"
              )}
            >
              {botStatus?.market_mode === "BULL" ? "🐂 상승장" :
               botStatus?.market_mode === "BEAR" ? "🐻 하락장" :
               "➡️ 횡보장"}
            </div>
            {/* 시장 점수 */}
            <p className="text-3xl font-bold text-white">
              {botStatus?.market_score ?? "--"}
              <span className="text-sm text-gray-400 ml-1">/100</span>
            </p>
            <p className="text-xs text-gray-500 mt-2">시장 점수</p>
          </div>

          {/* 거래 통계 */}
          <div className="space-y-2 mt-4 border-t border-dark-border pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">총 거래</span>
              <span className="text-white">{tradeSummary?.total_trades ?? 0}회</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">승/패</span>
              <span className="text-white">
                <span className="text-green-400">{tradeSummary?.win_count ?? 0}승</span>
                {" / "}
                <span className="text-red-400">{tradeSummary?.loss_count ?? 0}패</span>
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">총 수익</span>
              <span className={clsx(
                (tradeSummary?.total_pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"
              )}>
                {(tradeSummary?.total_pnl ?? 0).toLocaleString()}원
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ══════════ 하단: 보유 포지션 테이블 ══════════ */}
      <div className="card">
        <h3 className="text-sm text-gray-400 mb-4">
          보유 포지션 ({positions.length}개)
        </h3>

        {positions.length === 0 ? (
          <p className="text-center text-gray-500 py-8">
            보유 중인 포지션이 없습니다
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-dark-border">
                  <th className="py-2 text-left">코인</th>
                  <th className="py-2 text-right">평균 매수가</th>
                  <th className="py-2 text-right">현재가</th>
                  <th className="py-2 text-right">수량</th>
                  <th className="py-2 text-right">수익률</th>
                  <th className="py-2 text-right">수익금</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr
                    key={pos.id}
                    className="border-b border-dark-border hover:bg-gray-800/50"
                  >
                    <td className="py-3 font-medium text-white">{pos.coin}</td>
                    <td className="py-3 text-right text-gray-300">
                      {pos.avg_entry_price?.toLocaleString()}
                    </td>
                    <td className="py-3 text-right text-gray-300">
                      {pos.current_price?.toLocaleString() ?? "-"}
                    </td>
                    <td className="py-3 text-right text-gray-300">
                      {pos.total_quantity}
                    </td>
                    <td
                      className={clsx(
                        "py-3 text-right font-medium",
                        pos.current_pnl_pct >= 0 ? "text-rise-500" : "text-fall-500"
                      )}
                    >
                      {pos.current_pnl_pct >= 0 ? "+" : ""}
                      {pos.current_pnl_pct?.toFixed(2)}%
                    </td>
                    <td
                      className={clsx(
                        "py-3 text-right",
                        pos.current_pnl_amount >= 0 ? "text-rise-500" : "text-fall-500"
                      )}
                    >
                      {pos.current_pnl_amount?.toLocaleString()}원
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


/**
 * 통계 카드 하위 컴포넌트.
 * 일일/주간 수익률 등의 숫자를 표시합니다.
 */
function StatCard({ label, value, suffix = "", isPercent = false }) {
  const isPositive = value >= 0;
  return (
    <div className="card">
      <h3 className="text-sm text-gray-400 mb-2">{label}</h3>
      <p
        className={clsx(
          "text-2xl font-bold",
          isPercent
            ? isPositive
              ? "text-green-400"
              : "text-red-400"
            : "text-white"
        )}
      >
        {isPercent && isPositive ? "+" : ""}
        {typeof value === "number" ? value.toFixed(2) : value}
        {suffix}
      </p>
    </div>
  );
}

export default DashboardPage;
