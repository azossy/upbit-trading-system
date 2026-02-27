/**
 * ============================================================
 * API 클라이언트 모듈
 * Axios 기반 HTTP 클라이언트.
 * JWT 토큰 자동 첨부, 토큰 갱신, 에러 핸들링을 제공합니다.
 * ============================================================
 */
import axios from "axios";

// ─── 기본 API 인스턴스 생성 ───
// 환경변수 REACT_APP_API_URL이 없으면 기본값 사용
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "/api/v1",
  timeout: 15000,              // 요청 타임아웃: 15초
  withCredentials: true,       // HttpOnly 쿠키(Refresh Token) 전송 허용
  headers: {
    "Content-Type": "application/json",
  },
});


// ══════════════════════════════════════════════════
// 요청 인터셉터 — JWT Access Token 자동 첨부
// ══════════════════════════════════════════════════
api.interceptors.request.use(
  (config) => {
    // localStorage에서 Access Token 읽기
    const token = localStorage.getItem("access_token");
    if (token) {
      // Authorization 헤더에 Bearer 토큰 첨부
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);


// ══════════════════════════════════════════════════
// 응답 인터셉터 — 401 에러 시 토큰 갱신 시도
// ══════════════════════════════════════════════════
api.interceptors.response.use(
  // 정상 응답 — 그대로 반환
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    // 401 Unauthorized + 아직 재시도하지 않은 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;  // 무한 루프 방지 플래그

      try {
        // Refresh Token으로 새 Access Token 발급 시도
        // Refresh Token은 HttpOnly 쿠키에 저장되어 자동 전송됨
        const refreshResponse = await api.post("/auth/refresh");

        // 새 Access Token 저장
        const newToken = refreshResponse.data.access_token;
        localStorage.setItem("access_token", newToken);

        // 원래 요청에 새 토큰 적용 후 재시도
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);

      } catch (refreshError) {
        // Refresh Token도 만료된 경우 → 로그아웃 처리
        localStorage.removeItem("access_token");
        // 로그인 페이지로 리다이렉트
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);


// ══════════════════════════════════════════════════
// API 엔드포인트 함수들
// ══════════════════════════════════════════════════

// ─── 인증 API ───
export const authAPI = {
  /** 회원가입 */
  register: (data) => api.post("/auth/register", data),
  /** 로그인 */
  login: (data) => api.post("/auth/login", data),
  /** 로그아웃 */
  logout: () => api.post("/auth/logout"),
  /** 토큰 갱신 */
  refresh: () => api.post("/auth/refresh"),
  /** 내 정보 조회 */
  getMe: () => api.get("/auth/me"),
  /** 비밀번호 변경 */
  changePassword: (data) => api.put("/auth/password", data),
};

// ─── 봇 API ───
export const botAPI = {
  /** 봇 상태 조회 */
  getStatus: () => api.get("/bot/status"),
  /** 봇 시작 */
  start: () => api.post("/bot/start"),
  /** 봇 정지 */
  stop: () => api.post("/bot/stop"),
  /** 봇 설정 변경 */
  updateConfig: (data) => api.put("/bot/config", data),
  /** 보유 포지션 조회 */
  getPositions: (params) => api.get("/bot/positions", { params }),
  /** 거래 내역 조회 */
  getTrades: (params) => api.get("/bot/trades", { params }),
  /** 거래 성과 요약 */
  getTradeSummary: () => api.get("/bot/trades/summary"),
  /** API 키 목록 */
  getApiKeys: () => api.get("/bot/api-keys"),
  /** API 키 등록 */
  createApiKey: (data) => api.post("/bot/api-keys", data),
  /** API 키 삭제 */
  deleteApiKey: (id) => api.delete(`/bot/api-keys/${id}`),
};

// ─── 관리자 API ───
export const adminAPI = {
  /** 전체 유저 목록 */
  getUsers: (params) => api.get("/admin/users", { params }),
  /** 유저 상태 변경 (활성화/비활성화) */
  updateUserStatus: (userId, data) => api.put(`/admin/users/${userId}/status`, data),
  /** 시스템 상태 조회 */
  getSystemStatus: () => api.get("/admin/system/status"),
};

export default api;
