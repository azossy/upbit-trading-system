import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useStore } from "./store/useStore";
import HomePage       from "./pages/HomePage";
import LoginPage      from "./pages/LoginPage";
import RegisterPage   from "./pages/RegisterPage";
import DashboardPage  from "./pages/DashboardPage";
import TradesPage     from "./pages/TradesPage";
import SettingsPage   from "./pages/SettingsPage";
import AdminDashboard from "./pages/admin/AdminDashboard";
import Layout         from "./components/Layout";

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useStore();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function AdminRoute({ children }) {
  const { user } = useStore();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{style:{background:"#1e293b",color:"#f1f5f9",border:"1px solid #334155"},success:{iconTheme:{primary:"#22c55e",secondary:"#1e293b"}},error:{iconTheme:{primary:"#ef4444",secondary:"#1e293b"}}}} />
      <Routes>
        <Route path="/"         element={<HomePage />} />
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/trades"    element={<TradesPage />} />
          <Route path="/settings"  element={<SettingsPage />} />
          <Route path="/admin"     element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
