import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Briefcase,
  Target,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Info,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useAuth } from "../hooks/useAuth";
import { portfolio as portfolioApi, market, advisor } from "../api/client";
import {
  StatCard,
  SectionHeader,
  Spinner,
  EmptyState,
  RiskGauge,
} from "../components/ui";

const ASSET_COLORS = [
  "#e8b320",
  "#00e5a8",
  "#3b82f6",
  "#a855f7",
  "#f97316",
  "#06b6d4",
];

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [totalValue, setTotalValue] = useState(0);
  const [historyData, setHistoryData] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const [ps, sec, alloc] = await Promise.allSettled([
          portfolioApi.list(),
          market.sectors(),
          advisor.suggestedAllocation(),
        ]);
        const pList = ps.value || [];
        setPortfolios(pList);
        // Backend returns sectors as a dict keyed by sector name
        // (e.g. {"Technology": {"ticker": "XLK", "ytd_return_pct": 5.2}}),
        // not an array. Convert to the {sector, ytd_return} array shape
        // this page renders. ytd_return_pct is already a percentage, so
        // divide by 100 to match the *100 multiplication below.
        const sectorsObj = sec.value || {};
        setSectors(
          Object.entries(sectorsObj).map(([name, v]) => ({
            sector: name,
            ytd_return: (v?.ytd_return_pct ?? 0) / 100,
          })),
        );
        setSuggestions(alloc.value || null);

        // Compute total value & fetch history for first portfolio
        let total = 0;
        pList.forEach((p) => {
          total += parseFloat(p.total_value || p.cash_balance || 0);
        });
        setTotalValue(total);

        if (pList.length > 0) {
          const hist = await portfolioApi.history(pList[0].id);
          // Snapshots come back newest-first (model ordering is -date).
          // Take the most recent 90 (the first 90 in this order), then
          // reverse to ascending chronological order for the chart's
          // left-to-right X-axis.
          const arr = (hist?.snapshots || hist || []).slice(0, 90).reverse();
          setHistoryData(
            arr.map((s) => ({
              date: s.date?.slice(5),
              value: parseFloat(s.total_value || 0),
            })),
          );
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const riskScore = user?.risk_score ?? null;
  const riskProfile = user?.risk_profile ?? null;
  const totalPortfolios = portfolios.length;
  const firstPortfolio = portfolios[0];

  // Allocations from suggestion
  const allocationData = suggestions
    ? Object.entries(suggestions.suggested_allocation || {})
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({
          name: k.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase()),
          value: Math.round(v * 100),
        }))
    : [];

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={28} />
      </div>
    );

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Welcome */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-slate-100">
            Good {getGreeting()},{" "}
            <span className="gradient-text-gold">
              {user?.full_name?.split(" ")[0] || "Investor"}
            </span>
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Here&apos;s your financial overview for today.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2">
          <button
            onClick={() => navigate("/portfolios")}
            className="btn-primary flex items-center gap-2"
          >
            <Zap size={15} /> New Portfolio
          </button>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Portfolio Value"
          value={totalValue.toFixed(0)}
          prefix="$"
          icon={Briefcase}
          accent="gold"
        />
        <StatCard
          label="Active Portfolios"
          value={totalPortfolios}
          icon={TrendingUp}
          accent="jade"
        />
        <StatCard
          label="Risk Score"
          value={riskScore ?? "—"}
          suffix={riskScore ? "/100" : ""}
          icon={AlertTriangle}
          accent={riskScore > 60 ? "crimson" : "gold"}
        />
        <StatCard
          label="Goals Tracked"
          value="—"
          icon={Target}
          accent="slate"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Portfolio value chart */}
        <div className="lg:col-span-2 card p-6">
          <SectionHeader
            title="Portfolio Performance"
            subtitle={
              firstPortfolio
                ? `${firstPortfolio.name} — Last 90 days`
                : "No portfolios yet"
            }
          />
          {historyData.length > 1 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart
                data={historyData}
                margin={{ top: 5, right: 0, bottom: 0, left: 0 }}
              >
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e8b320" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#e8b320" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#475569", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#475569", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0d1521",
                    border: "1px solid #1a2840",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#94a3b8" }}
                  itemStyle={{ color: "#e8b320" }}
                  formatter={(v) => [`$${v.toLocaleString()}`, "Value"]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#e8b320"
                  strokeWidth={2}
                  fill="url(#grad)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              icon={TrendingUp}
              title="No history yet"
              description="Create a portfolio and add holdings to see performance here."
              action={
                <button
                  onClick={() => navigate("/portfolios")}
                  className="btn-primary text-sm"
                >
                  Get Started
                </button>
              }
            />
          )}
        </div>

        {/* Risk profile */}
        <div className="card p-6 flex flex-col">
          <SectionHeader
            title="Risk Profile"
            subtitle="Your investment tolerance"
          />
          {riskScore !== null ? (
            <div className="flex flex-col items-center flex-1 justify-center gap-4">
              <RiskGauge score={riskScore} profile={riskProfile} />
              <div className="w-full space-y-2 text-sm">
                {suggestions?.description && (
                  <p className="text-slate-400 text-xs text-center leading-relaxed px-2">
                    {suggestions.description}
                  </p>
                )}
              </div>
              <button
                onClick={() => navigate("/settings")}
                className="btn-ghost text-xs"
              >
                Retake Questionnaire →
              </button>
            </div>
          ) : (
            <EmptyState
              icon={Target}
              title="No risk profile"
              description="Complete the questionnaire to get personalized advice."
              action={
                <button
                  onClick={() => navigate("/settings")}
                  className="btn-primary text-sm"
                >
                  Take Quiz
                </button>
              }
            />
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Portfolios list */}
        <div className="lg:col-span-2 card p-6">
          <SectionHeader
            title="Your Portfolios"
            actions={
              <button
                onClick={() => navigate("/portfolios")}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                View all <ArrowRight size={12} />
              </button>
            }
          />
          {portfolios.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No portfolios yet"
              description="Create your first portfolio to start tracking your investments."
              action={
                <button
                  onClick={() => navigate("/portfolios")}
                  className="btn-primary text-sm"
                >
                  Create Portfolio
                </button>
              }
            />
          ) : (
            <div className="space-y-2">
              {portfolios.slice(0, 5).map((p) => (
                <div
                  key={p.id}
                  onClick={() => navigate(`/portfolios/${p.id}`)}
                  className="flex items-center justify-between p-4 rounded-xl bg-obsidian-900 border border-obsidian-700 hover:border-obsidian-500 cursor-pointer transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gold-500/10 border border-gold-500/20 flex items-center justify-center">
                      <Briefcase size={14} className="text-gold-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        {p.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {p.benchmark_ticker || "SPY"} benchmark
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-sm font-mono font-semibold text-slate-100">
                        $
                        {parseFloat(
                          p.total_value || p.cash_balance || 0,
                        ).toLocaleString()}
                      </p>
                      <p className="text-xs text-slate-500">
                        {p.holdings_count || 0} holdings
                      </p>
                    </div>
                    <ArrowRight
                      size={14}
                      className="text-slate-600 group-hover:text-gold-400 transition-colors"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Suggested allocation */}
        <div className="card p-6">
          <SectionHeader
            title="Suggested Allocation"
            subtitle="Based on your risk profile"
          />
          {allocationData.length > 0 ? (
            <div className="flex flex-col items-center gap-4">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {allocationData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={ASSET_COLORS[i % ASSET_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#0d1521",
                      border: "1px solid #1a2840",
                      borderRadius: 8,
                      fontSize: 11,
                    }}
                    formatter={(v) => [`${v}%`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="w-full space-y-1.5">
                {allocationData.map((d, i) => (
                  <div
                    key={d.name}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{
                          background: ASSET_COLORS[i % ASSET_COLORS.length],
                        }}
                      />
                      <span className="text-slate-400">{d.name}</span>
                    </div>
                    <span className="font-mono text-slate-300">{d.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Target}
              title="Complete your risk profile"
              description="Get personalized allocation suggestions."
            />
          )}
        </div>
      </div>

      {/* Sectors */}
      {sectors.length > 0 && (
        <div className="card p-6">
          <SectionHeader
            title="Sector Performance"
            subtitle="YTD returns across GICS sectors"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {sectors.slice(0, 12).map((s) => {
              const change = parseFloat(s.ytd_return || s.change || 0) * 100;
              return (
                <div
                  key={s.sector || s.name}
                  className="p-3 rounded-xl bg-obsidian-900 border border-obsidian-700 text-center"
                >
                  <p className="text-xs text-slate-500 mb-1 truncate">
                    {s.sector || s.name}
                  </p>
                  <p
                    className={`text-sm font-mono font-semibold ${change >= 0 ? "text-jade-500" : "text-crimson-400"}`}
                  >
                    {change >= 0 ? "+" : ""}
                    {change.toFixed(1)}%
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}
