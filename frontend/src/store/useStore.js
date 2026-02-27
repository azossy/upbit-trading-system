/**
 * ============================================================
 * Zustand 전역 상태 관리 스토어
 * React의 Context API보다 간결하고 성능이 좋은
 * Zustand를 사용하여 전역 상태를 관리합니다.
 *
 * 상태 구조:
 *   - user: 로그인한 사용자 정보
 *   - isAuthenticated: 인증 여부
 *   - botStatus: 봇 현재 상태
 *   - positions: 보유 포지션 목록
 *   - tradeSummary: 거래 성과 요약
 * ============================================================
 */
import { create } from "zustand";
import { authAPI, botAPI } from "../services/api";

const useStore = create((set, get) => ({
  // ══════════════════════════════════════════════════
  // 인증 상태
  // ══════════════════════════════════════════════════

  /** 현재 로그인된 사용자 정보 (null이면 비로그인) */
  user: null,

  /** 인증 여부 */
  isAuthenticated: !!localStorage.getItem("access_token"),

  /** 인증 로딩 상태 */
  authLoading: false,

  /**
   * 로그인 처리.
   * Access Token을 localStorage에 저장하고, 사용자 정보를 상태에 설정합니다.
   *
   * @param {string} email - 이메일
   * @param {string} password - 비밀번호
   */
  login: async (email, password) => {
    set({ authLoading: true });
    try {
      const response = await authAPI.login({ email, password });
      const { access_token, user } = response.data;

      // Access Token 저장 (Refresh Token은 HttpOnly 쿠키로 자동 설정)
      localStorage.setItem("access_token", access_token);

      set({
        user,
        isAuthenticated: true,
        authLoading: false,
      });

      return { success: true };
    } catch (error) {
      set({ authLoading: false });
      const message =
        error.response?.data?.detail || "로그인에 실패했습니다";
      return { success: false, error: message };
    }
  },

  /**
   * 로그아웃 처리.
   * 서버에 로그아웃 요청 후, 로컬 상태와 토큰을 모두 초기화합니다.
   */
  logout: async () => {
    try {
      await authAPI.logout();
    } catch (e) {
      // 서버 요청 실패해도 로컬 로그아웃은 진행
    }
    localStorage.removeItem("access_token");
    set({
      user: null,
      isAuthenticated: false,
      botStatus: null,
      positions: [],
      tradeSummary: null,
    });
  },

  /**
   * 현재 로그인된 사용자 정보를 서버에서 조회합니다.
   * 페이지 새로고침 시 토큰이 유효한지 확인하는 용도로 사용됩니다.
   */
  fetchUser: async () => {
    try {
      const response = await authAPI.getMe();
      set({ user: response.data, isAuthenticated: true });
    } catch (error) {
      // 토큰 만료 등으로 실패 시 로그아웃 처리
      localStorage.removeItem("access_token");
      set({ user: null, isAuthenticated: false });
    }
  },


  // ══════════════════════════════════════════════════
  // 봇 상태
  // ══════════════════════════════════════════════════

  /** 봇 현재 상태 객체 */
  botStatus: null,

  /** 봇 상태 로딩 중 */
  botLoading: false,

  /**
   * 봇 상태를 서버에서 조회합니다.
   */
  fetchBotStatus: async () => {
    set({ botLoading: true });
    try {
      const response = await botAPI.getStatus();
      set({ botStatus: response.data, botLoading: false });
    } catch (error) {
      set({ botLoading: false });
    }
  },

  /**
   * 봇을 시작합니다.
   */
  startBot: async () => {
    try {
      await botAPI.start();
      // 시작 후 상태 갱신
      await get().fetchBotStatus();
      return { success: true };
    } catch (error) {
      const message =
        error.response?.data?.detail || "봇 시작에 실패했습니다";
      return { success: false, error: message };
    }
  },

  /**
   * 봇을 정지합니다.
   */
  stopBot: async () => {
    try {
      await botAPI.stop();
      await get().fetchBotStatus();
      return { success: true };
    } catch (error) {
      const message =
        error.response?.data?.detail || "봇 정지에 실패했습니다";
      return { success: false, error: message };
    }
  },


  // ══════════════════════════════════════════════════
  // 포지션 & 거래 내역
  // ══════════════════════════════════════════════════

  /** 보유 포지션 목록 */
  positions: [],

  /** 거래 성과 요약 */
  tradeSummary: null,

  /**
   * 보유 포지션 목록을 서버에서 조회합니다.
   */
  fetchPositions: async () => {
    try {
      const response = await botAPI.getPositions();
      set({ positions: response.data });
    } catch (error) {
      console.error("포지션 조회 실패:", error);
    }
  },

  /**
   * 거래 성과 요약을 서버에서 조회합니다.
   */
  fetchTradeSummary: async () => {
    try {
      const response = await botAPI.getTradeSummary();
      set({ tradeSummary: response.data });
    } catch (error) {
      console.error("성과 요약 조회 실패:", error);
    }
  },
}));

export default useStore;
export { useStore }; // named export — import { useStore } from "./store/useStore" 도 지원
