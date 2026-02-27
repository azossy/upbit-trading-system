import React, { useState } from "react";
import { NavLink, Link, Outlet, useNavigate } from "react-router-dom";
import { useStore } from "../store/useStore";

const NAV_ITEMS = [
  { path: "/dashboard", label: "대시보드", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg> },
  { path: "/trades",    label: "거래 내역", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg> },
  { path: "/settings",  label: "봇 설정",   icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg> },
];
const ADMIN_ITEM = { path: "/admin", label: "관리자", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg> };

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, botStatus, logout } = useStore();
  const navigate = useNavigate();

  // botStatus는 API 응답 객체 { status, market_mode, ... }
  const isRunning = botStatus?.status === "running";
  const marketCondition = botStatus?.market_mode; // "bull" | "bear" | "sideways" | undefined

  const navItems = user?.role === "admin" ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS;
  const marketIcon = { bull: "🐂", bear: "🐻", sideways: "➡️" }[marketCondition] || "➡️";
  const marketLabel = { bull: "상승장", bear: "하락장", sideways: "횡보장" }[marketCondition] || "분석중";
  const handleLogout = () => { logout(); navigate("/"); };

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      {/* ─── 사이드바 ─── */}
      <aside className={`flex flex-col transition-all duration-300 bg-gray-900 border-r border-gray-800 ${collapsed ? "w-16" : "w-60"}`}>
        {/* 로고 */}
        <div className={`h-16 flex items-center border-b border-gray-800 ${collapsed ? "justify-center" : "px-4 gap-2.5"}`}>
          <Link to="/" className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-md flex-shrink-0">
              <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="16 7 22 7 22 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            {!collapsed && <span className="font-bold text-white text-sm truncate">Upbit<span className="text-blue-400">Auto</span></span>}
          </Link>
        </div>

        {/* 봇 상태 표시 */}
        <div className={`px-3 py-3 border-b border-gray-800 ${collapsed ? "flex justify-center" : ""}`}>
          {collapsed ? (
            <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
          ) : (
            <div className="bg-gray-800 rounded-xl p-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-gray-400 text-xs">봇 상태</span>
                <div className={`flex items-center gap-1.5 text-xs font-medium ${isRunning ? "text-green-400" : "text-gray-500"}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
                  {isRunning ? "실행 중" : "중지됨"}
                </div>
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <span>{marketIcon}</span>
                <span>{marketLabel}</span>
              </div>
            </div>
          )}
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${collapsed ? "justify-center" : ""} ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`
              }
              title={collapsed ? item.label : undefined}
            >
              {item.icon}
              {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* 사이드바 접기 + 로그아웃 */}
        <div className="border-t border-gray-800 p-2 space-y-1">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800 transition-all ${collapsed ? "justify-center" : ""}`}
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d={collapsed ? "M13 5l7 7-7 7M5 5l7 7-7 7" : "M11 19l-7-7 7-7m8 14l-7-7 7-7"} />
            </svg>
            {!collapsed && <span className="text-sm font-medium">사이드바 접기</span>}
          </button>
          <button
            onClick={handleLogout}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all ${collapsed ? "justify-center" : ""}`}
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {!collapsed && <span className="text-sm font-medium">로그아웃</span>}
          </button>
        </div>
      </aside>

      {/* ─── 메인 영역 ─── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 상단 헤더 */}
        <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6 flex-shrink-0">
          <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border ${
            marketCondition === "bull"
              ? "bg-green-500/10 text-green-400 border-green-500/30"
              : marketCondition === "bear"
              ? "bg-red-500/10 text-red-400 border-red-500/30"
              : "bg-gray-700/50 text-gray-400 border-gray-600/50"
          }`}>
            {marketIcon} {marketLabel}
          </span>
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-white text-sm font-medium">{user?.nickname || "사용자"}</div>
              <div className="text-gray-500 text-xs">{user?.email || ""}</div>
            </div>
            <div className="w-9 h-9 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-sm">
              {(user?.nickname || "U")[0].toUpperCase()}
            </div>
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
