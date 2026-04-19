import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import PortfoliosPage from "./pages/PortfoliosPage";
import PortfolioDetailPage from "./pages/PortfolioDetailPage";
import MarketPage from "./pages/MarketPage";
import RiskPage from "./pages/RiskPage";
import AdvisorPage from "./pages/AdvisorPage";
import TaxPage from "./pages/TaxPage";
import GoalsPage from "./pages/GoalsPage";
import SettingsPage from "./pages/SettingsPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-obsidian-900 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-2 border-obsidian-600 border-t-gold-500 animate-spin" />
        <p className="text-slate-500 text-sm font-mono">
          Initializing QuantumWealth...
        </p>
      </div>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;

  return (
    <Routes>
      <Route
        path="/login"
        element={!user ? <LoginPage /> : <Navigate to="/" replace />}
      />
      <Route
        path="/register"
        element={!user ? <RegisterPage /> : <Navigate to="/" replace />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="portfolios" element={<PortfoliosPage />} />
        <Route path="portfolios/:id" element={<PortfolioDetailPage />} />
        <Route path="market" element={<MarketPage />} />
        <Route path="risk" element={<RiskPage />} />
        <Route path="advisor" element={<AdvisorPage />} />
        <Route path="tax" element={<TaxPage />} />
        <Route path="goals" element={<GoalsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
