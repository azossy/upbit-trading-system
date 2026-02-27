/** @type {import('tailwindcss').Config} */
module.exports = {
  // ─── Tailwind CSS가 스캔할 파일 경로 ───
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  // ─── 다크 모드 설정 (클래스 기반) ───
  darkMode: "class",
  theme: {
    extend: {
      // ─── 커스텀 색상 (트레이딩 시스템 전용) ───
      colors: {
        // 상승(매수) — 빨간색 계열 (한국 주식 관습)
        rise: {
          50: "#fef2f2",
          500: "#ef4444",
          600: "#dc2626",
        },
        // 하락(매도) — 파란색 계열
        fall: {
          50: "#eff6ff",
          500: "#3b82f6",
          600: "#2563eb",
        },
        // 다크 모드 배경
        dark: {
          bg: "#0f172a",
          card: "#1e293b",
          border: "#334155",
        },
      },
    },
  },
  plugins: [],
};
