import { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  BarChart3,
  Activity,
  Layers,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  BarChart,
  Bar,
} from "recharts";
import { portfolio as portfolioApi, risk } from "../api/client";
import {
  SectionHeader,
  Spinner,
  Alert,
  Select,
  TabBar,
  EmptyState,
  MetricRow,
} from "../components/ui";

const SCENARIOS = [
  { value: "2008_crisis", label: "2008 Financial Crisis" },
  { value: "covid_crash", label: "COVID-19 Crash" },
  { value: "dot_com_bust", label: "Dot-Com Bust" },
  { value: "rate_shock", label: "Rate Shock" },
  { value: "inflation_spike", label: "Inflation Spike" },
  { value: "all", label: "All Scenarios" },
];

export default function RiskPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [tab, setTab] = useState("report");
  const [report, setReport] = useState(null);
  const [varData, setVarData] = useState(null);
  const [monteCarlo, setMonteCarlo] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [stressResult, setStressResult] = useState(null);
  const [scenario, setScenario] = useState("2008_crisis");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    portfolioApi
      .list()
      .then((d) => {
        const list = d?.results || d || [];
        setPortfolios(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch(() => {});
  }, []);

  const loadReport = async (id) => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const [r, v95, v99, mc, corr] = await Promise.allSettled([
        risk.report(id),
        risk.var(id, { confidence: 0.95, method: "historical" }),
        risk.var(id, { confidence: 0.99, method: "historical" }),
        risk.monteCarlo(id, { simulations: 1000, horizon_years: 10 }),
        risk.correlation(id),
      ]);
      setReport(r.value);
      // FIX: /risk/var/ returns one confidence level per call (var_pct,
      // cvar_pct, var_dollar, cvar_dollar - already percentages, no
      // var_95/var_99 split). Merge the two calls into the shape this
      // page renders, dividing the already-percent values by 100 so the
      // existing *100 display math produces the right number.
      const v95d = v95.value || {};
      const v99d = v99.value || {};
      setVarData({
        var_95: v95d.var_pct != null ? v95d.var_pct / 100 : undefined,
        var_99: v99d.var_pct != null ? v99d.var_pct / 100 : undefined,
        cvar_95: v95d.cvar_pct != null ? v95d.cvar_pct / 100 : undefined,
        cvar_99: v99d.cvar_pct != null ? v99d.cvar_pct / 100 : undefined,
        var_95_dollar: v95d.var_dollar,
        var_99_dollar: v99d.var_dollar,
        cvar_95_dollar: v95d.cvar_dollar,
        cvar_99_dollar: v99d.cvar_dollar,
      });
      setMonteCarlo(mc.value);
      setCorrelation(corr.value);
    } catch (e) {
      setError(
        "Failed to load risk report. Ensure your portfolio has holdings and price history.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId) loadReport(selectedId);
  }, [selectedId]);

  const runStress = async () => {
    setLoading(true);
    try {
      const res = await risk.stressTest(selectedId, { scenario });
      setStressResult(res);
    } catch {
      setError("Stress test failed.");
    } finally {
      setLoading(false);
    }
  };

  const perf = report?.performance || {};
  const rm = report?.risk_metrics || {};
  const portName =
    portfolios.find((p) => p.id == selectedId)?.name || "Portfolio";

  const mcSummary = monteCarlo?.percentiles || {};

  // Correlation data
  const corrTickers = correlation?.tickers || [];
  const corrMatrix = correlation?.matrix || [];

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="section-title text-3xl">Risk Engine</h1>
          <p className="text-slate-500 text-sm mt-1">
            Value at Risk, Monte Carlo, and stress testing.
          </p>
          <div className="accent-line mt-2" />
        </div>
        <Select
          value={selectedId}
          onChange={(v) => setSelectedId(v)}
          options={portfolios.map((p) => ({ value: p.id, label: p.name }))}
          className="w-56"
        />
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size={28} />
        </div>
      ) : !report && !varData ? (
        <div className="card p-12">
          <EmptyState
            icon={ShieldCheck}
            title="No risk data"
            description="Add holdings to your portfolio to run risk analysis."
          />
        </div>
      ) : (
        <>
          {/* Performance metrics */}
          {report && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  label: "Annualized Return",
                  value: `${((perf.annualized_return || 0) * 100).toFixed(2)}%`,
                  pos: (perf.annualized_return || 0) >= 0,
                },
                {
                  label: "Sharpe Ratio",
                  value: (perf.sharpe_ratio || 0).toFixed(3),
                  pos: (perf.sharpe_ratio || 0) >= 1,
                },
                {
                  label: "Max Drawdown",
                  value: `${((perf.max_drawdown || 0) * 100).toFixed(2)}%`,
                  pos: false,
                },
                {
                  label: "VaR 95% (1-day)",
                  value: rm.var_95_dollar
                    ? `-$${Math.abs(rm.var_95_dollar).toLocaleString()}`
                    : "—",
                  pos: false,
                },
              ].map((m) => (
                <div key={m.label} className="card p-4">
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                    {m.label}
                  </p>
                  <p
                    className={`text-xl font-mono font-bold ${m.pos ? "text-jade-500" : "text-crimson-400"}`}
                  >
                    {m.value}
                  </p>
                </div>
              ))}
            </div>
          )}

          <TabBar
            tabs={[
              { label: "Risk Report", value: "report" },
              { label: "VaR Analysis", value: "var" },
              { label: "Monte Carlo", value: "mc" },
              { label: "Correlation", value: "corr" },
              { label: "Stress Tests", value: "stress" },
            ]}
            active={tab}
            onChange={setTab}
          />

          {/* Report tab */}
          {tab === "report" && report && (
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="card p-6">
                <SectionHeader title="Performance Metrics" />
                <MetricRow
                  label="Annualized Return"
                  value={`${((perf.annualized_return || 0) * 100).toFixed(2)}%`}
                  highlight
                />
                <MetricRow
                  label="Annualized Volatility"
                  value={`${((perf.annualized_volatility || 0) * 100).toFixed(2)}%`}
                />
                <MetricRow
                  label="Sharpe Ratio"
                  value={(perf.sharpe_ratio || 0).toFixed(4)}
                  highlight
                />
                <MetricRow
                  label="Sortino Ratio"
                  value={(perf.sortino_ratio || 0).toFixed(4)}
                />
                <MetricRow
                  label="Calmar Ratio"
                  value={(perf.calmar_ratio || 0).toFixed(4)}
                />
                <MetricRow
                  label="Omega Ratio"
                  value={(perf.omega_ratio || 0).toFixed(4)}
                />
                <MetricRow
                  label="Max Drawdown"
                  value={`${((perf.max_drawdown || 0) * 100).toFixed(2)}%`}
                />
              </div>
              <div className="card p-6">
                <SectionHeader title="Risk Metrics" />
                <MetricRow
                  label="VaR 95% (1-day, $)"
                  value={
                    rm.var_95_dollar
                      ? `-$${Math.abs(rm.var_95_dollar).toLocaleString()}`
                      : "—"
                  }
                />
                <MetricRow
                  label="CVaR 95% (1-day, $)"
                  value={
                    rm.cvar_95_dollar
                      ? `-$${Math.abs(rm.cvar_95_dollar).toLocaleString()}`
                      : "—"
                  }
                  highlight
                />
                <MetricRow
                  label="VaR 95% (%)"
                  value={
                    rm.var_95_pct != null ? `${rm.var_95_pct.toFixed(2)}%` : "—"
                  }
                />
                <MetricRow
                  label="CVaR 95% (%)"
                  value={
                    rm.cvar_95_pct != null
                      ? `${rm.cvar_95_pct.toFixed(2)}%`
                      : "—"
                  }
                />
                {report.stress_tests &&
                  Object.entries(report.stress_tests).map(([k, v]) => (
                    <MetricRow
                      key={k}
                      label={k.replace("_", " ")}
                      value={`${v.toFixed(2)}%`}
                    />
                  ))}
              </div>
            </div>
          )}

          {/* VaR tab */}
          {tab === "var" && varData && (
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="card p-6">
                <SectionHeader
                  title="Value at Risk"
                  subtitle="Historical simulation method"
                />
                <div className="space-y-4">
                  {[
                    {
                      label: "95% VaR (1-day)",
                      value: varData.var_95 || varData.var,
                    },
                    { label: "99% VaR (1-day)", value: varData.var_99 },
                    {
                      label: "95% CVaR / Expected Shortfall",
                      value: varData.cvar_95 || varData.cvar,
                    },
                    {
                      label: "99% CVaR / Expected Shortfall",
                      value: varData.cvar_99,
                    },
                  ].map(
                    (m) =>
                      m.value !== undefined && (
                        <div
                          key={m.label}
                          className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700"
                        >
                          <p className="text-xs text-slate-500 mb-1">
                            {m.label}
                          </p>
                          <p className="font-mono font-bold text-2xl text-crimson-400">
                            {typeof m.value === "number"
                              ? `-${(Math.abs(m.value) * 100).toFixed(2)}%`
                              : String(m.value)}
                          </p>
                        </div>
                      ),
                  )}
                </div>
              </div>
              <div className="card p-6">
                <SectionHeader title="VaR in Dollar Terms" />
                <div className="space-y-4">
                  {[
                    { label: "95% VaR ($)", value: varData.var_95_dollar },
                    { label: "99% VaR ($)", value: varData.var_99_dollar },
                    { label: "95% CVaR ($)", value: varData.cvar_95_dollar },
                    { label: "99% CVaR ($)", value: varData.cvar_99_dollar },
                  ].map(
                    (m) =>
                      m.value !== undefined && (
                        <div
                          key={m.label}
                          className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700"
                        >
                          <p className="text-xs text-slate-500 mb-1">
                            {m.label}
                          </p>
                          <p className="font-mono font-bold text-2xl text-crimson-400">
                            -${Math.abs(m.value).toLocaleString()}
                          </p>
                        </div>
                      ),
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Monte Carlo */}
          {tab === "mc" && (
            <div className="space-y-6">
              <div className="card p-6">
                <SectionHeader
                  title="Monte Carlo Projection"
                  subtitle="10-year horizon, 1,000 simulations"
                />
                {mcSummary && Object.keys(mcSummary).length > 0 ? (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {[
                      { label: "10th Percentile", value: mcSummary.p10 },
                      {
                        label: "50th Percentile",
                        value: mcSummary.p50 || mcSummary.median,
                      },
                      { label: "90th Percentile", value: mcSummary.p90 },
                      {
                        label: "Expected Value",
                        value: monteCarlo?.expected_final_value,
                      },
                    ].map(
                      (m) =>
                        m.value !== undefined && (
                          <div
                            key={m.label}
                            className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700 text-center"
                          >
                            <p className="text-xs text-slate-500 mb-1">
                              {m.label}
                            </p>
                            <p className="font-mono font-bold text-lg text-jade-500">
                              $
                              {parseFloat(m.value).toLocaleString(undefined, {
                                maximumFractionDigits: 0,
                              })}
                            </p>
                          </div>
                        ),
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-12">
                    Monte Carlo simulation data is being processed.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Correlation */}
          {tab === "corr" && correlation && (
            <div className="card p-6">
              <SectionHeader
                title="Correlation Matrix"
                subtitle="Asset return correlations"
              />
              {corrTickers.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="text-xs font-mono">
                    <thead>
                      <tr>
                        <th className="p-2 text-left text-slate-500"></th>
                        {corrTickers.map((t) => (
                          <th key={t} className="p-2 text-slate-400">
                            {t}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {corrTickers.map((row, i) => (
                        <tr key={row}>
                          <td className="p-2 text-slate-400 font-semibold">
                            {row}
                          </td>
                          {corrTickers.map((col, j) => {
                            const val = corrMatrix[i]?.[j] ?? 0;
                            const intensity = Math.abs(val);
                            const isPos = val >= 0;
                            return (
                              <td
                                key={col}
                                className="p-2 text-center rounded"
                                style={{
                                  background: `rgba(${isPos ? "0,229,168" : "255,68,89"}, ${0.05 + intensity * 0.25})`,
                                }}
                              >
                                <span
                                  className={
                                    val >= 0
                                      ? "text-jade-500"
                                      : "text-crimson-400"
                                  }
                                >
                                  {val.toFixed(2)}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-8">
                  No correlation data available. Add multiple holdings.
                </p>
              )}
              {correlation.high_correlations?.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
                    High Correlation Pairs (&gt;0.8)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {correlation.high_correlations.map((pair) => (
                      <span
                        key={`${pair.ticker_a}-${pair.ticker_b}`}
                        className="badge-crimson"
                      >
                        {pair.ticker_a} / {pair.ticker_b}:{" "}
                        {pair.correlation?.toFixed(3)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Stress test */}
          {tab === "stress" && (
            <div className="space-y-6">
              <div className="card p-6">
                <SectionHeader title="Historical Stress Testing" />
                <div className="flex items-end gap-4 flex-wrap">
                  <Select
                    label="Scenario"
                    value={scenario}
                    onChange={setScenario}
                    options={SCENARIOS}
                    className="w-64"
                  />
                  <button
                    onClick={runStress}
                    disabled={loading}
                    className="btn-primary flex items-center gap-2"
                  >
                    {loading ? (
                      <Spinner size={14} className="text-obsidian-950" />
                    ) : (
                      <Activity size={14} />
                    )}
                    Run Stress Test
                  </button>
                </div>
              </div>

              {stressResult && (
                <div className="card p-6 border-crimson-500/20">
                  <SectionHeader
                    title="Stress Test Results"
                    subtitle={
                      SCENARIOS.find((s) => s.value === scenario)?.label
                    }
                  />
                  <div className="grid lg:grid-cols-3 gap-4">
                    {[
                      {
                        label: "Total Impact (%)",
                        value:
                          stressResult.total_impact_pct != null
                            ? `${stressResult.total_impact_pct >= 0 ? "+" : ""}${stressResult.total_impact_pct.toFixed(2)}%`
                            : "—",
                        negative: (stressResult.total_impact_pct ?? 0) < 0,
                      },
                      {
                        label: "Total Impact ($)",
                        value:
                          stressResult.total_impact_dollar != null
                            ? `${stressResult.total_impact_dollar >= 0 ? "+" : "-"}$${Math.abs(stressResult.total_impact_dollar).toLocaleString()}`
                            : "—",
                        negative: (stressResult.total_impact_dollar ?? 0) < 0,
                      },
                      {
                        label: "Stressed Portfolio Value",
                        value:
                          stressResult.stressed_value != null
                            ? `$${stressResult.stressed_value.toLocaleString()}`
                            : "—",
                        negative: false,
                      },
                    ].map((m) => (
                      <div
                        key={m.label}
                        className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700"
                      >
                        <p className="text-xs text-slate-500 mb-2 capitalize">
                          {m.label}
                        </p>
                        <p
                          className={`font-mono font-bold text-2xl ${m.negative ? "text-crimson-400" : "text-jade-500"}`}
                        >
                          {m.value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
