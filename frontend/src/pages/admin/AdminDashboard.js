/**
 * ============================================================
 * 관리자 대시보드 페이지 컴포넌트
 * 전체 유저 관리, 시스템 상태 모니터링을 제공합니다.
 *
 * 기능:
 *   - 전체 유저 목록 조회 (이메일, 역할, 활성 상태)
 *   - 유저 활성화/비활성화 토글
 *   - 시스템 상태 모니터링 (DB, Redis, 봇 수)
 * ============================================================
 */
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import dayjs from "dayjs";
import { adminAPI } from "../../services/api";

function AdminDashboard() {
  // ─── 상태 ───
  const [users, setUsers] = useState([]);            // 유저 목록
  const [systemStatus, setSystemStatus] = useState(null); // 시스템 상태
  const [loading, setLoading] = useState(true);

  // ─── 초기 데이터 로드 ───
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 유저 목록과 시스템 상태를 동시에 조회
      const [usersRes, statusRes] = await Promise.all([
        adminAPI.getUsers({ page: 1, page_size: 100 }),
        adminAPI.getSystemStatus(),
      ]);
      setUsers(usersRes.data);
      setSystemStatus(statusRes.data);
    } catch (error) {
      console.error("관리자 데이터 로드 실패:", error);
      toast.error("데이터를 불러올 수 없습니다");
    } finally {
      setLoading(false);
    }
  };

  /**
   * 유저 활성화/비활성화 토글 핸들러.
   *
   * @param {number} userId - 대상 유저 ID
   * @param {boolean} currentStatus - 현재 활성 상태
   */
  const handleToggleUser = async (userId, currentStatus) => {
    try {
      await adminAPI.updateUserStatus(userId, {
        is_active: !currentStatus,
      });
      toast.success(
        currentStatus ? "유저가 비활성화되었습니다" : "유저가 활성화되었습니다"
      );
      fetchData(); // 목록 새로고침
    } catch (error) {
      toast.error("상태 변경 실패");
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16 text-gray-500">불러오는 중...</div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">관리자 대시보드</h2>

      {/* ══════════ 시스템 상태 카드 ══════════ */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatusCard
          label="전체 유저"
          value={systemStatus?.total_users ?? "-"}
        />
        <StatusCard
          label="활성 유저"
          value={systemStatus?.active_users ?? "-"}
        />
        <StatusCard
          label="실행 중인 봇"
          value={systemStatus?.running_bots ?? "-"}
        />
        <StatusCard
          label="오늘 거래"
          value={systemStatus?.today_trades ?? "-"}
        />
      </div>

      {/* ══════════ 유저 목록 테이블 ══════════ */}
      <div className="card">
        <h3 className="text-sm text-gray-400 mb-4">
          유저 관리 ({users.length}명)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-dark-border">
                <th className="py-2 text-left">ID</th>
                <th className="py-2 text-left">이메일</th>
                <th className="py-2 text-left">닉네임</th>
                <th className="py-2 text-center">역할</th>
                <th className="py-2 text-center">상태</th>
                <th className="py-2 text-left">마지막 로그인</th>
                <th className="py-2 text-center">가입일</th>
                <th className="py-2 text-center">액션</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-dark-border hover:bg-gray-800/50"
                >
                  <td className="py-2.5 text-gray-400">{user.id}</td>
                  <td className="py-2.5 text-white">{user.email}</td>
                  <td className="py-2.5 text-gray-300">{user.nickname}</td>
                  <td className="py-2.5 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        user.role === "admin"
                          ? "bg-purple-900 text-purple-300"
                          : "bg-gray-700 text-gray-300"
                      }`}
                    >
                      {user.role === "admin" ? "관리자" : "유저"}
                    </span>
                  </td>
                  <td className="py-2.5 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        user.is_active
                          ? "bg-green-900 text-green-300"
                          : "bg-red-900 text-red-300"
                      }`}
                    >
                      {user.is_active ? "활성" : "비활성"}
                    </span>
                  </td>
                  <td className="py-2.5 text-gray-400 text-xs">
                    {user.last_login_at
                      ? dayjs(user.last_login_at).format("MM/DD HH:mm")
                      : "-"}
                  </td>
                  <td className="py-2.5 text-center text-gray-400 text-xs">
                    {dayjs(user.created_at).format("YYYY/MM/DD")}
                  </td>
                  <td className="py-2.5 text-center">
                    {/* 관리자 자신은 비활성화 불가 */}
                    {user.role !== "admin" && (
                      <button
                        onClick={() => handleToggleUser(user.id, user.is_active)}
                        className={`text-xs px-2 py-1 rounded ${
                          user.is_active
                            ? "text-red-400 hover:bg-red-900/50"
                            : "text-green-400 hover:bg-green-900/50"
                        }`}
                      >
                        {user.is_active ? "비활성화" : "활성화"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/**
 * 시스템 상태 카드 하위 컴포넌트
 */
function StatusCard({ label, value }) {
  return (
    <div className="card">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

export default AdminDashboard;
