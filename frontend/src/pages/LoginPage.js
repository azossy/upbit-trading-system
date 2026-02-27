/**
 * ============================================================
 * 로그인 페이지 컴포넌트
 * 이메일/비밀번호 입력 폼으로 JWT 인증을 수행합니다.
 * 로그인 성공 시 대시보드로 이동합니다.
 * ============================================================
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import useStore from "../store/useStore";

function LoginPage() {
  const navigate = useNavigate();
  const { login, authLoading } = useStore();

  // ─── 폼 상태 ───
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  /**
   * 로그인 폼 제출 핸들러.
   * Zustand store의 login 액션을 호출합니다.
   */
  const handleSubmit = async (e) => {
    e.preventDefault();

    const result = await login(email, password);

    if (result.success) {
      toast.success("로그인 성공!");
      navigate("/dashboard");        // 대시보드로 이동
    } else {
      toast.error(result.error);    // 에러 메시지 표시
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg">
      <div className="w-full max-w-md p-8 bg-dark-card rounded-2xl border border-dark-border shadow-2xl">
        {/* ── 헤더 ── */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">📈 자동매매 시스템</h1>
          <p className="text-gray-400 mt-2 text-sm">
            업비트 자동 트레이딩 봇 v3.0
          </p>
        </div>

        {/* ── 로그인 폼 ── */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 이메일 입력 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-white placeholder-gray-500 focus:outline-none focus:ring-2
                         focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* 비밀번호 입력 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">비밀번호</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                required
                className="w-full px-4 py-2.5 pr-11 bg-gray-800 border border-gray-700 rounded-lg
                           text-white placeholder-gray-500 focus:outline-none focus:ring-2
                           focus:ring-blue-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-200"
                tabIndex={-1}
              >
                {showPassword ? (
                  /* 눈 감김 아이콘 (비밀번호 숨기기) */
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7
                         a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243
                         M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29
                         M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7
                         a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  /* 눈 뜬 아이콘 (비밀번호 보기) */
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7
                         -1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* 로그인 버튼 */}
          <button
            type="submit"
            disabled={authLoading}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800
                       disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {authLoading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        {/* ── 회원가입 링크 ── */}
        <p className="mt-6 text-center text-sm text-gray-500">
          계정이 없으신가요?{" "}
          <Link to="/register" className="text-blue-400 hover:text-blue-300">
            회원가입
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
