/**
 * ============================================================
 * 봇 설정 페이지 컴포넌트
 * 봇 파라미터 변경, API 키 관리 기능을 제공합니다.
 *
 * 섹션:
 *   1. 투자 설정 (최대 투자 비율, 최대 코인 수)
 *   2. 손절/익절 설정 (ATR 배수, 손절 범위, 트레일링 스탑)
 *   3. API 키 관리 (등록/삭제)
 * ============================================================
 */
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { botAPI } from "../services/api";
import useStore from "../store/useStore";

function SettingsPage() {
  const { botStatus, fetchBotStatus } = useStore();

  // ─── 봇 설정 폼 상태 ───
  const [config, setConfig] = useState({
    max_investment_ratio: 0.5,
    max_coins: 7,
    atr_multiplier: 1.5,
    min_stop_loss_pct: 1.5,
    max_stop_loss_pct: 5.0,
    trailing_stop_activation_pct: 15.0,
    trailing_stop_distance_pct: 5.0,
  });

  // ─── API 키 상태 ───
  const [apiKeys, setApiKeys] = useState([]);          // 등록된 키 목록
  const [newKey, setNewKey] = useState({               // 새 키 입력
    api_key: "",
    api_secret: "",
    label: "",
  });
  const [saving, setSaving] = useState(false);         // 저장 로딩

  // ─── 초기 데이터 로드 ───
  useEffect(() => {
    fetchBotStatus();
    fetchApiKeys();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 봇 상태에서 현재 설정값 로드
  useEffect(() => {
    if (botStatus?.config) {
      setConfig((prev) => ({ ...prev, ...botStatus.config }));
    }
  }, [botStatus]);

  /** API 키 목록 조회 */
  const fetchApiKeys = async () => {
    try {
      const response = await botAPI.getApiKeys();
      setApiKeys(response.data);
    } catch (error) {
      console.error("API 키 조회 실패:", error);
    }
  };

  /** 설정 저장 핸들러 */
  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await botAPI.updateConfig(config);
      toast.success("설정이 저장되었습니다");
      fetchBotStatus(); // 설정 반영 확인을 위해 재조회
    } catch (error) {
      toast.error(error.response?.data?.detail || "설정 저장 실패");
    } finally {
      setSaving(false);
    }
  };

  /** API 키 등록 핸들러 */
  const handleAddApiKey = async () => {
    if (!newKey.api_key || !newKey.api_secret) {
      toast.error("API Key와 Secret을 모두 입력하세요");
      return;
    }
    try {
      await botAPI.createApiKey({
        exchange: "upbit",
        label: newKey.label || "기본 키",
        api_key: newKey.api_key,
        api_secret: newKey.api_secret,
      });
      toast.success("API 키가 등록되었습니다");
      setNewKey({ api_key: "", api_secret: "", label: "" });
      fetchApiKeys();
    } catch (error) {
      toast.error(error.response?.data?.detail || "API 키 등록 실패");
    }
  };

  /** API 키 삭제 핸들러 */
  const handleDeleteApiKey = async (keyId) => {
    if (!window.confirm("정말 이 API 키를 삭제하시겠습니까?")) return;
    try {
      await botAPI.deleteApiKey(keyId);
      toast.success("API 키가 삭제되었습니다");
      fetchApiKeys();
    } catch (error) {
      toast.error(error.response?.data?.detail || "삭제 실패");
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="text-xl font-bold text-white">봇 설정</h2>

      {/* ══════════ 1. 투자 설정 ══════════ */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-300 mb-4">투자 설정</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 최대 투자 비율 */}
          <SettingInput
            label="최대 투자 비율"
            help="총 잔고 대비 최대 투자 비율 (0.1 ~ 1.0)"
            value={config.max_investment_ratio}
            onChange={(v) => setConfig({ ...config, max_investment_ratio: v })}
            type="number"
            min={0.1}
            max={1.0}
            step={0.1}
          />
          {/* 최대 동시 보유 */}
          <SettingInput
            label="최대 보유 코인 수"
            help="동시에 보유할 수 있는 최대 코인 수 (1~7)"
            value={config.max_coins}
            onChange={(v) => setConfig({ ...config, max_coins: v })}
            type="number"
            min={1}
            max={7}
            step={1}
          />
        </div>
      </div>

      {/* ══════════ 2. 손절/익절 설정 ══════════ */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-300 mb-4">손절/익절 설정</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SettingInput
            label="ATR 배수"
            help="손절 계산에 사용되는 ATR 배수 (1.0~3.0)"
            value={config.atr_multiplier}
            onChange={(v) => setConfig({ ...config, atr_multiplier: v })}
            type="number"
            min={1.0}
            max={3.0}
            step={0.1}
          />
          <SettingInput
            label="최소 손절률 (%)"
            help="최소 손절 비율 (0.5~3.0%)"
            value={config.min_stop_loss_pct}
            onChange={(v) => setConfig({ ...config, min_stop_loss_pct: v })}
            type="number"
            min={0.5}
            max={3.0}
            step={0.5}
          />
          <SettingInput
            label="최대 손절률 (%)"
            help="최대 손절 비율 (3.0~10.0%)"
            value={config.max_stop_loss_pct}
            onChange={(v) => setConfig({ ...config, max_stop_loss_pct: v })}
            type="number"
            min={3.0}
            max={10.0}
            step={0.5}
          />
          <SettingInput
            label="트레일링 스탑 활성화 (%)"
            help="트레일링 스탑 활성화 수익률 (5~30%)"
            value={config.trailing_stop_activation_pct}
            onChange={(v) => setConfig({ ...config, trailing_stop_activation_pct: v })}
            type="number"
            min={5.0}
            max={30.0}
            step={1.0}
          />
          <SettingInput
            label="트레일링 스탑 폭 (%)"
            help="최고점 대비 하락 허용치 (2~10%)"
            value={config.trailing_stop_distance_pct}
            onChange={(v) => setConfig({ ...config, trailing_stop_distance_pct: v })}
            type="number"
            min={2.0}
            max={10.0}
            step={0.5}
          />
        </div>

        {/* 저장 버튼 */}
        <button
          onClick={handleSaveConfig}
          disabled={saving}
          className="mt-4 btn-primary disabled:opacity-50"
        >
          {saving ? "저장 중..." : "설정 저장"}
        </button>
      </div>

      {/* ══════════ 3. API 키 관리 ══════════ */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-300 mb-4">업비트 API 키</h3>

        {/* 등록된 키 목록 */}
        {apiKeys.length > 0 && (
          <div className="space-y-2 mb-4">
            {apiKeys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between p-3 bg-gray-800 rounded-lg"
              >
                <div>
                  <span className="text-sm text-white">{key.label || "업비트 키"}</span>
                  <span className="text-xs text-gray-500 ml-2">
                    {key.api_key_masked}
                  </span>
                  <span
                    className={`text-xs ml-2 ${key.is_active ? "text-green-400" : "text-gray-500"}`}
                  >
                    {key.is_active ? "활성" : "비활성"}
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteApiKey(key.id)}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  삭제
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 새 키 등록 폼 */}
        <div className="space-y-3 p-4 bg-gray-800/50 rounded-lg">
          <h4 className="text-xs text-gray-400">새 API 키 등록</h4>
          <input
            type="text"
            placeholder="라벨 (예: 메인 계정)"
            value={newKey.label}
            onChange={(e) => setNewKey({ ...newKey, label: e.target.value })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm
                       text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="API Access Key"
            value={newKey.api_key}
            onChange={(e) => setNewKey({ ...newKey, api_key: e.target.value })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm
                       text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="API Secret Key"
            value={newKey.api_secret}
            onChange={(e) => setNewKey({ ...newKey, api_secret: e.target.value })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm
                       text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button onClick={handleAddApiKey} className="btn-primary text-sm">
            API 키 등록
          </button>
        </div>
      </div>
    </div>
  );
}


/**
 * 설정 입력 필드 하위 컴포넌트
 */
function SettingInput({ label, help, value, onChange, type, min, max, step }) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg
                   text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {help && <p className="text-xs text-gray-500 mt-1">{help}</p>}
    </div>
  );
}

export default SettingsPage;
