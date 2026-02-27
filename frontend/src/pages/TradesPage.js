/**
 * ============================================================
 * 거래 내역 페이지 컴포넌트
 * 과거 거래 내역을 테이블 형태로 표시하고,
 * 코인별/기간별 필터 기능을 제공합니다.
 * ============================================================
 */
import React, { useEffect, useState } from "react";
import clsx from "clsx";
import dayjs from "dayjs";
import { botAPI } from "../services/api";

function TradesPage() {
  // ─── 로컬 상태 ───
  const [trades, setTrades] = useState([]);      // 거래 내역 목록
  const [loading, setLoading] = useState(false);  // 로딩 상태
  const [filters, setFilters] = useState({
    coin: "",         // 코인 필터 (빈 문자열 = 전체)
    days: 30,         // 조회 기간 (일)
    page: 1,          // 현재 페이지
  });

  // ─── 거래 내역 조회 ───
  useEffect(() => {
    const fetchTrades = async () => {
      setLoading(true);
      try {
        const params = {
          days: filters.days,
          page: filters.page,
          page_size: 50,
        };
        // 코인 필터가 있으면 추가
        if (filters.coin) {
          params.coin = filters.coin;
        }
        const response = await botAPI.getTrades(params);
        setTrades(response.data);
      } catch (error) {
        console.error("거래 내역 조회 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrades();
  }, [filters]);

  return (
    <div className="space-y-6">
      {/* ── 페이지 헤더 ── */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">거래 내역</h2>
      </div>

      {/* ── 필터 영역 ── */}
      <div className="card">
        <div className="flex flex-wrap gap-4 items-end">
          {/* 코인 필터 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">코인</label>
            <input
              type="text"
              value={filters.coin}
              onChange={(e) => setFilters({ ...filters, coin: e.target.value, page: 1 })}
              placeholder="KRW-BTC"
              className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* 기간 필터 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">기간</label>
            <select
              value={filters.days}
              onChange={(e) => setFilters({ ...filters, days: Number(e.target.value), page: 1 })}
              className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-sm text-white focus:outline-none"
            >
              <option value={7}>7일</option>
              <option value={30}>30일</option>
              <option value={90}>90일</option>
              <option value={180}>180일</option>
              <option value={365}>1년</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── 거래 내역 테이블 ── */}
      <div className="card">
        {loading ? (
          <div className="text-center py-8 text-gray-500">불러오는 중...</div>
        ) : trades.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            거래 내역이 없습니다
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-dark-border">
                  <th className="py-2 text-left">시간</th>
                  <th className="py-2 text-left">코인</th>
                  <th className="py-2 text-center">구분</th>
                  <th className="py-2 text-right">가격</th>
                  <th className="py-2 text-right">수량</th>
                  <th className="py-2 text-right">금액</th>
                  <th className="py-2 text-right">수수료</th>
                  <th className="py-2 text-right">실현손익</th>
                  <th className="py-2 text-left">사유</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr
                    key={trade.id}
                    className="border-b border-dark-border hover:bg-gray-800/50"
                  >
                    {/* 거래 시간 */}
                    <td className="py-2.5 text-gray-400 text-xs">
                      {dayjs(trade.created_at).format("MM/DD HH:mm")}
                    </td>
                    {/* 코인 */}
                    <td className="py-2.5 text-white font-medium">
                      {trade.coin}
                    </td>
                    {/* 매수/매도 구분 */}
                    <td className="py-2.5 text-center">
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-xs font-medium",
                          trade.side === "bid"
                            ? "bg-rise-500/20 text-rise-500"
                            : "bg-fall-500/20 text-fall-500"
                        )}
                      >
                        {trade.side === "bid" ? "매수" : "매도"}
                      </span>
                    </td>
                    {/* 체결 가격 */}
                    <td className="py-2.5 text-right text-gray-300">
                      {trade.price?.toLocaleString()}
                    </td>
                    {/* 체결 수량 */}
                    <td className="py-2.5 text-right text-gray-300">
                      {trade.quantity}
                    </td>
                    {/* 총 금액 */}
                    <td className="py-2.5 text-right text-gray-300">
                      {trade.total_amount?.toLocaleString()}원
                    </td>
                    {/* 수수료 */}
                    <td className="py-2.5 text-right text-gray-500">
                      {trade.fee?.toLocaleString()}원
                    </td>
                    {/* 실현 손익 */}
                    <td
                      className={clsx(
                        "py-2.5 text-right font-medium",
                        trade.realized_pnl == null
                          ? "text-gray-500"
                          : trade.realized_pnl >= 0
                            ? "text-green-400"
                            : "text-red-400"
                      )}
                    >
                      {trade.realized_pnl != null
                        ? `${trade.realized_pnl >= 0 ? "+" : ""}${trade.realized_pnl?.toLocaleString()}원`
                        : "-"}
                    </td>
                    {/* 거래 사유 */}
                    <td className="py-2.5 text-gray-400 text-xs">
                      {trade.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 페이지네이션 ── */}
        {trades.length > 0 && (
          <div className="flex justify-center gap-2 mt-4 pt-4 border-t border-dark-border">
            <button
              onClick={() => setFilters({ ...filters, page: Math.max(1, filters.page - 1) })}
              disabled={filters.page <= 1}
              className="px-3 py-1 bg-gray-700 rounded text-sm text-gray-300
                         hover:bg-gray-600 disabled:opacity-50"
            >
              이전
            </button>
            <span className="px-3 py-1 text-sm text-gray-400">
              {filters.page} 페이지
            </span>
            <button
              onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
              disabled={trades.length < 50}
              className="px-3 py-1 bg-gray-700 rounded text-sm text-gray-300
                         hover:bg-gray-600 disabled:opacity-50"
            >
              다음
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default TradesPage;
