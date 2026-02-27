/**
 * ============================================================
 * React 앱 엔트리포인트
 * React 18의 createRoot를 사용하여 앱을 마운트합니다.
 * ============================================================
 */
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";          // Tailwind CSS + 글로벌 스타일
import App from "./App";       // 메인 App 컴포넌트

// React 18 루트 생성 및 렌더링
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
