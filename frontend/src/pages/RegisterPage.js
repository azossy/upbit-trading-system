/**
 * ============================================================
 * 회원가입 페이지 컴포넌트
 * 이메일, 비밀번호, 닉네임을 입력받아 회원가입을 처리합니다.
 * 가입 성공 시 로그인 페이지로 이동합니다.
 * ============================================================
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { authAPI } from "../services/api";

function RegisterPage() {
  const navigate = useNavigate();

  // ─── 폼 상태 ───
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    passwordConfirm: "",
    nickname: "",
  });
  const [loading, setLoading] = useState(false);

  /**
   * 입력 필드 변경 핸들러.
   * formData 상태를 업데이트합니다.
   */
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  /**
   * 회원가입 폼 제출 핸들러.
   * 비밀번호 확인 검증 후 서버에 회원가입 요청을 보냅니다.
   */
  const handleSubmit = async (e) => {
    e.preventDefault();

    // 비밀번호 확인 검증
    if (formData.password !== formData.passwordConfirm) {
      toast.error("비밀번호가 일치하지 않습니다");
      return;
    }

    setLoading(true);
    try {
      await authAPI.register({
        email: formData.email,
        password: formData.password,
        nickname: formData.nickname,
      });

      toast.success("회원가입 성공! 로그인해주세요.");
      navigate("/login");

    } catch (error) {
      const message = error.response?.data?.detail || "회원가입에 실패했습니다";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg">
      <div className="w-full max-w-md p-8 bg-dark-card rounded-2xl border border-dark-border shadow-2xl">
        {/* ── 헤더 ── */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">회원가입</h1>
          <p className="text-gray-400 mt-2 text-sm">
            자동매매 시스템 계정을 생성합니다
          </p>
        </div>

        {/* ── 회원가입 폼 ── */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 이메일 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">이메일</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 닉네임 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">닉네임</label>
            <input
              type="text"
              name="nickname"
              value={formData.nickname}
              onChange={handleChange}
              placeholder="2~20자 (한글/영문/숫자)"
              required
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 비밀번호 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">비밀번호</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="8자 이상, 영문+숫자+특수문자"
              required
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 비밀번호 확인 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">비밀번호 확인</label>
            <input
              type="password"
              name="passwordConfirm"
              value={formData.passwordConfirm}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 가입 버튼 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50
                       text-white font-medium rounded-lg transition-colors mt-2"
          >
            {loading ? "가입 중..." : "회원가입"}
          </button>
        </form>

        {/* ── 로그인 링크 ── */}
        <p className="mt-6 text-center text-sm text-gray-500">
          이미 계정이 있으신가요?{" "}
          <Link to="/login" className="text-blue-400 hover:text-blue-300">
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
