import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  ShieldCheck,
  Bot,
  Receipt,
  Target,
  Settings,
  LogOut,
  Bell,
  ChevronRight,
  Activity,
  Menu,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { auth } from "../../api/client";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { to: "/portfolios", icon: Briefcase, label: "Portfolios" },
  { to: "/market", icon: TrendingUp, label: "Markets" },
  { to: "/risk", icon: ShieldCheck, label: "Risk Engine" },
  { to: "/advisor", icon: Bot, label: "AI Advisor" },
  { to: "/tax", icon: Receipt, label: "Tax Center" },
  { to: "/goals", icon: Target, label: "Goals" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    auth
      .unreadCount()
      .then((d) => setUnread(d?.unread_count || 0))
      .catch(() => {});
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const initials =
    user?.full_name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "QW";

  return (
    <div className="flex h-screen overflow-hidden bg-obsidian-900">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
        fixed lg:relative z-30 h-full flex flex-col
        w-64 bg-obsidian-950 border-r border-obsidian-700
        transition-transform duration-300 ease-out
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-obsidian-700">
          <div className="relative">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center shadow-gold">
              <Activity
                size={16}
                className="text-obsidian-950"
                strokeWidth={2.5}
              />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-jade-500 border-2 border-obsidian-950 animate-pulse-slow" />
          </div>
          <div>
            <h1 className="font-display font-semibold text-slate-100 text-base leading-tight tracking-tight">
              QuantumWealth
            </h1>
            <p className="text-[10px] font-mono text-slate-600 tracking-widest uppercase">
              AI Wealth Platform
            </p>
          </div>
        </div>

        {/* Market Status */}
        <div className="px-6 py-3 border-b border-obsidian-700/50">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider">
              Market
            </span>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-jade-500 animate-pulse-slow" />
              <span className="text-[10px] font-mono text-jade-500">OPEN</span>
            </div>
          </div>
          <p className="text-xs font-mono text-slate-500 mt-0.5">
            {time.toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              timeZone: "America/New_York",
            })}{" "}
            EST
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <div className="space-y-0.5">
            {navItems.map(({ to, icon: Icon, label, exact }) => (
              <NavLink
                key={to}
                to={to}
                end={exact}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-all duration-150 group relative
                  ${
                    isActive
                      ? "bg-gold-500/10 text-gold-400 border border-gold-500/20"
                      : "text-slate-500 hover:text-slate-300 hover:bg-obsidian-800"
                  }
                `}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-gold-500 rounded-r-full" />
                    )}
                    <Icon
                      size={16}
                      strokeWidth={isActive ? 2.5 : 2}
                      className="shrink-0"
                    />
                    <span>{label}</span>
                    {isActive && (
                      <ChevronRight size={12} className="ml-auto opacity-50" />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-obsidian-700/50 space-y-0.5">
            <NavLink
              to="/settings"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                transition-all duration-150
                ${
                  isActive
                    ? "bg-gold-500/10 text-gold-400 border border-gold-500/20"
                    : "text-slate-500 hover:text-slate-300 hover:bg-obsidian-800"
                }
              `}
            >
              <Settings size={16} strokeWidth={2} />
              <span>Settings</span>
            </NavLink>
          </div>
        </nav>

        {/* User */}
        <div className="px-3 py-4 border-t border-obsidian-700">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-obsidian-800 border border-obsidian-600">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold-500/30 to-gold-600/20 border border-gold-500/30 flex items-center justify-center shrink-0">
              <span className="text-xs font-semibold text-gold-400">
                {initials}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">
                {user?.full_name || "User"}
              </p>
              <p className="text-[10px] text-slate-600 truncate">
                {user?.email}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-600 hover:text-crimson-400 transition-colors"
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-obsidian-700 bg-obsidian-900/80 backdrop-blur-sm shrink-0">
          <button
            className="lg:hidden text-slate-400 hover:text-slate-200 transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>

          <div className="hidden lg:flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-jade-500" />
            <span className="text-xs font-mono text-slate-500">
              All systems operational
            </span>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => navigate("/settings")}
              className="relative flex items-center justify-center w-9 h-9 rounded-lg
                         bg-obsidian-800 border border-obsidian-600 hover:border-obsidian-500
                         text-slate-400 hover:text-slate-200 transition-all"
            >
              <Bell size={16} />
              {unread > 0 && (
                <span
                  className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-crimson-500
                                 text-[9px] font-bold text-white flex items-center justify-center"
                >
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </button>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-obsidian-800 border border-obsidian-600">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-gold-500/30 to-gold-600/20 border border-gold-500/30 flex items-center justify-center">
                <span className="text-[9px] font-bold text-gold-400">
                  {initials}
                </span>
              </div>
              <span className="text-xs font-medium text-slate-300 hidden sm:block">
                {user?.full_name?.split(" ")[0]}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-obsidian-900">
          <div className="max-w-7xl mx-auto px-6 py-8 animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
