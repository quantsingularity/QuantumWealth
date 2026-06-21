import { useState, useEffect } from "react";
import {
  Bot,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  Scale,
} from "lucide-react";
import { portfolio as portfolioApi, advisor } from "../api/client";
import {
  SectionHeader,
  Spinner,
  Alert,
  Select,
  TabBar,
  EmptyState,
  Modal,
} from "../components/ui";

const GOAL_TYPES = [
  "retirement",
  "education",
  "house",
  "emergency_fund",
  "vacation",
  "custom",
];

export default function AdvisorPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [tab, setTab] = useState("recommendations");
  const [recommendations, setRecommendations] = useState(null);
  const [drift, setDrift] = useState(null);
  const [rebalanceResult, setRebalanceResult] = useState(null);
  const [suggestedAlloc, setSuggestedAlloc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showGoalPlan, setShowGoalPlan] = useState(false);
  const [goalPlan, setGoalPlan] = useState(null);

  useEffect(() => {
    portfolioApi.list().then((d) => {
      const list = d?.results || d || [];
      setPortfolios(list);
      if (list.length > 0) setSelectedId(list[0].id);
    });
    advisor
      .suggestedAllocation()
      .then(setSuggestedAlloc)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    Promise.allSettled([
      advisor.recommendations(selectedId),
      advisor.drift(selectedId),
    ])
      .then(([rec, dr]) => {
        setRecommendations(rec.value);
        setDrift(dr.value);
      })
      .finally(() => setLoading(false));
  }, [selectedId]);

  const handleRebalance = async (method, threshold) => {
    setLoading(true);
    try {
      const res = await advisor.rebalance(selectedId, {
        method,
        drift_threshold: threshold,
      });
      setRebalanceResult(res);
    } catch {
      setError("Rebalancing analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const recList = recommendations?.recommendations || recommendations || [];
  const driftItems = drift?.drift_data || [];

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="section-title text-3xl">AI Advisor</h1>
          <p className="text-slate-500 text-sm mt-1">
            Personalized recommendations, rebalancing, and goal planning.
          </p>
          <div className="accent-line mt-2" />
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={selectedId}
            onChange={setSelectedId}
            options={portfolios.map((p) => ({ value: p.id, label: p.name }))}
            className="w-48"
          />
          <button
            onClick={() => setShowGoalPlan(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Lightbulb size={14} /> Goal Planner
          </button>
        </div>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {/* Suggested allocation summary */}
      {suggestedAlloc && (
        <div className="card p-5 border-gold-500/15">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gold-500/10 flex items-center justify-center">
              <Bot size={16} className="text-gold-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">
                AI Recommendation
              </p>
              <p className="text-xs text-slate-500">
                Based on your risk profile
              </p>
            </div>
          </div>
          <p className="text-sm text-slate-300">{suggestedAlloc.description}</p>
          {suggestedAlloc.suggested_allocation && (
            <div className="flex flex-wrap gap-2 mt-3">
              {Object.entries(suggestedAlloc.suggested_allocation).map(
                ([k, v]) => (
                  <span key={k} className="badge-gold">
                    {k.replace("_", " ")}: {(v * 100).toFixed(0)}%
                  </span>
                ),
              )}
            </div>
          )}
        </div>
      )}

      <TabBar
        tabs={[
          { label: "Recommendations", value: "recommendations" },
          { label: "Drift Analysis", value: "drift" },
          { label: "Rebalancing", value: "rebalance" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size={28} />
        </div>
      ) : (
        <>
          {/* Recommendations */}
          {tab === "recommendations" &&
            (recList.length === 0 ? (
              <div className="card p-12">
                <EmptyState
                  icon={Bot}
                  title="No recommendations yet"
                  description="Add holdings to your portfolio to receive AI-powered insights."
                />
              </div>
            ) : (
              <div className="space-y-3">
                {recList.map((rec, i) => {
                  const icon =
                    rec.severity === "high"
                      ? AlertTriangle
                      : rec.severity === "medium"
                        ? TrendingUp
                        : CheckCircle2;
                  const color =
                    rec.severity === "high"
                      ? "crimson"
                      : rec.severity === "medium"
                        ? "gold"
                        : "jade";
                  const Icon = icon;
                  return (
                    <div
                      key={i}
                      className={`card-hover p-5 border-l-2 ${color === "crimson" ? "border-l-crimson-500" : color === "gold" ? "border-l-gold-500" : "border-l-jade-500"}`}
                    >
                      <div className="flex items-start gap-4">
                        <div
                          className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${color === "crimson" ? "bg-crimson-500/10 text-crimson-400" : color === "gold" ? "bg-gold-500/10 text-gold-400" : "bg-jade-500/10 text-jade-500"}`}
                        >
                          <Icon size={15} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-sm font-semibold text-slate-200">
                              {(rec.type || "").replace(/_/g, " ") ||
                                "Recommendation"}
                            </p>
                            <span
                              className={`badge badge-${color === "crimson" ? "crimson" : color === "gold" ? "gold" : "jade"} text-[10px]`}
                            >
                              {rec.severity || "info"}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 leading-relaxed">
                            {rec.message}
                          </p>
                          {rec.ticker && (
                            <p className="text-xs font-mono text-gold-400 mt-2">
                              {rec.ticker}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}

          {/* Drift */}
          {tab === "drift" && (
            <div className="card p-6">
              <SectionHeader
                title="Allocation Drift"
                subtitle="Current vs target allocation"
              />
              {driftItems.length === 0 ? (
                <EmptyState
                  icon={Scale}
                  title="No drift data"
                  description="Set target allocations in your portfolio."
                />
              ) : (
                <div className="space-y-4">
                  {driftItems.map((item) => {
                    const drift = parseFloat(
                      item.drift ||
                        item.current_weight - item.target_weight ||
                        0,
                    );
                    const isOver = drift > 0;
                    return (
                      <div
                        key={item.ticker}
                        className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-mono font-semibold text-gold-400">
                            {item.ticker}
                          </span>
                          <span
                            className={`badge ${Math.abs(drift) > 0.05 ? "badge-crimson" : "badge-jade"}`}
                          >
                            Drift: {isOver ? "+" : ""}
                            {(drift * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-3 text-xs">
                            <span className="text-slate-500 w-24">Current</span>
                            <div className="flex-1 bg-obsidian-800 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-gold-500 rounded-full"
                                style={{
                                  width: `${Math.min((item.current_weight || 0) * 100, 100)}%`,
                                }}
                              />
                            </div>
                            <span className="font-mono text-slate-300 w-12 text-right">
                              {((item.current_weight || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs">
                            <span className="text-slate-500 w-24">Target</span>
                            <div className="flex-1 bg-obsidian-800 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-jade-500 rounded-full"
                                style={{
                                  width: `${Math.min((item.target_weight || 0) * 100, 100)}%`,
                                }}
                              />
                            </div>
                            <span className="font-mono text-slate-300 w-12 text-right">
                              {((item.target_weight || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Rebalancing */}
          {tab === "rebalance" && (
            <div className="space-y-6">
              <div className="card p-6">
                <SectionHeader title="Generate Rebalancing Plan" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div
                    className="p-4 rounded-xl border border-obsidian-600 bg-obsidian-900 cursor-pointer hover:border-gold-500/40 transition-all"
                    onClick={() => handleRebalance("threshold", 0.05)}
                  >
                    <p className="font-semibold text-slate-200 mb-1">
                      Threshold Rebalancing
                    </p>
                    <p className="text-xs text-slate-500">
                      Rebalance when any position drifts more than 5% from its
                      target allocation.
                    </p>
                  </div>
                  <div
                    className="p-4 rounded-xl border border-obsidian-600 bg-obsidian-900 cursor-pointer hover:border-gold-500/40 transition-all"
                    onClick={() => handleRebalance("calendar", 0.05)}
                  >
                    <p className="font-semibold text-slate-200 mb-1">
                      Calendar Rebalancing
                    </p>
                    <p className="text-xs text-slate-500">
                      Periodic rebalancing to restore the portfolio to its
                      target weights.
                    </p>
                  </div>
                </div>
              </div>

              {rebalanceResult && (
                <div className="card p-6 border-jade-500/20">
                  <SectionHeader
                    title="Rebalancing Trades"
                    subtitle="Tax-aware sequencing applied"
                    actions={
                      <button
                        onClick={() => setRebalanceResult(null)}
                        className="btn-ghost text-xs"
                      >
                        Clear
                      </button>
                    }
                  />
                  {(rebalanceResult.trades || rebalanceResult || []).length ===
                  0 ? (
                    <p className="text-sm text-slate-400 text-center py-6">
                      ✓ Portfolio is within drift thresholds. No trades needed.
                    </p>
                  ) : (
                    <div className="table-container">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Ticker</th>
                            <th>Action</th>
                            <th className="text-right">Shares</th>
                            <th className="text-right">Value</th>
                            <th>Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(rebalanceResult.trades || rebalanceResult).map(
                            (t, i) => (
                              <tr key={i}>
                                <td>
                                  <span className="font-mono font-semibold text-gold-400">
                                    {t.ticker}
                                  </span>
                                </td>
                                <td>
                                  <span
                                    className={`badge ${t.action === "BUY" ? "badge-jade" : "badge-crimson"}`}
                                  >
                                    {t.action}
                                  </span>
                                </td>
                                <td className="text-right font-mono">
                                  {parseFloat(t.suggested_shares || 0).toFixed(
                                    2,
                                  )}
                                </td>
                                <td className="text-right font-mono">
                                  $
                                  {parseFloat(
                                    t.estimated_value || 0,
                                  ).toLocaleString()}
                                </td>
                                <td className="text-xs text-slate-500">
                                  {t.reason || "—"}
                                </td>
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}

      <GoalPlannerModal
        open={showGoalPlan}
        onClose={() => setShowGoalPlan(false)}
        onResult={(r) => {
          setGoalPlan(r);
          setShowGoalPlan(false);
        }}
      />

      {goalPlan && (
        <div className="card p-6 border-gold-500/20">
          <SectionHeader
            title="Goal Attainment Plan"
            actions={
              <button
                onClick={() => setGoalPlan(null)}
                className="btn-ghost text-xs"
              >
                Clear
              </button>
            }
          />
          <div className="grid lg:grid-cols-3 gap-4 mb-6">
            {[
              {
                label: "Goal Status",
                value: goalPlan.gap_analysis
                  ? goalPlan.gap_analysis.on_track
                    ? "On Track"
                    : "Behind Pace"
                  : "—",
                accent: goalPlan.gap_analysis?.on_track ? "jade" : "crimson",
              },
              {
                label: "Projected Value",
                value: goalPlan.projected_value
                  ? `$${parseFloat(goalPlan.projected_value).toLocaleString()}`
                  : "—",
                accent: "gold",
              },
              {
                label: "Probability of Success",
                value:
                  goalPlan.probability_of_success != null
                    ? `${(goalPlan.probability_of_success * 100).toFixed(0)}%`
                    : "—",
                accent: "jade",
              },
            ].map((m) => (
              <div
                key={m.label}
                className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700 text-center"
              >
                <p className="text-xs text-slate-500 mb-2">{m.label}</p>
                <p
                  className={`font-mono font-bold text-xl ${m.accent === "gold" ? "text-gold-400" : m.accent === "jade" ? "text-jade-500" : "text-crimson-400"}`}
                >
                  {m.value}
                </p>
              </div>
            ))}
          </div>
          {goalPlan.gap_analysis && (
            <p className="text-sm text-slate-300 bg-obsidian-900 rounded-xl p-4 border border-obsidian-700 leading-relaxed">
              {goalPlan.gap_analysis.on_track
                ? `You're on track to reach this goal. Your current monthly contribution of $${parseFloat(goalPlan.current_monthly_contribution || 0).toLocaleString()} is projected to meet your inflation-adjusted target.`
                : `You're behind pace by $${Math.abs(goalPlan.gap_analysis.gap_amount || 0).toLocaleString()}. Consider raising your monthly contribution to $${parseFloat(goalPlan.recommended_monthly_contribution || 0).toLocaleString()} (a gap of $${parseFloat(goalPlan.contribution_gap || 0).toLocaleString()}/month) to stay on track.`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function GoalPlannerModal({ open, onClose, onResult }) {
  const [form, setForm] = useState({
    goal_type: "retirement",
    target_amount: "",
    current_savings: "",
    monthly_contribution: "",
    target_date: "",
    expected_return: "0.075",
    inflation_rate: "0.03",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await advisor.plan({
        ...form,
        target_amount: parseFloat(form.target_amount),
        current_savings: parseFloat(form.current_savings),
        monthly_contribution: parseFloat(form.monthly_contribution),
        expected_return: parseFloat(form.expected_return),
        inflation_rate: parseFloat(form.inflation_rate),
      });
      onResult(res);
    } catch (err) {
      setError(err.data?.detail || "Failed to generate plan.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="AI Goal Planner"
      maxWidth="max-w-xl"
    >
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Goal Type</label>
            <select
              className="select"
              value={form.goal_type}
              onChange={(e) => set("goal_type", e.target.value)}
            >
              {GOAL_TYPES.map((g) => (
                <option key={g} value={g}>
                  {g.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Target Amount ($)</label>
            <input
              type="number"
              className="input"
              placeholder="500000"
              value={form.target_amount}
              onChange={(e) => set("target_amount", e.target.value)}
              required
              min={0}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Current Savings ($)</label>
            <input
              type="number"
              className="input"
              placeholder="50000"
              value={form.current_savings}
              onChange={(e) => set("current_savings", e.target.value)}
              required
              min={0}
            />
          </div>
          <div>
            <label className="label">Monthly Contribution ($)</label>
            <input
              type="number"
              className="input"
              placeholder="2000"
              value={form.monthly_contribution}
              onChange={(e) => set("monthly_contribution", e.target.value)}
              required
              min={0}
            />
          </div>
        </div>
        <div>
          <label className="label">Target Date</label>
          <input
            type="date"
            className="input"
            value={form.target_date}
            onChange={(e) => set("target_date", e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Expected Annual Return</label>
            <input
              type="number"
              className="input"
              step="0.001"
              value={form.expected_return}
              onChange={(e) => set("expected_return", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Inflation Rate</label>
            <input
              type="number"
              className="input"
              step="0.001"
              value={form.inflation_rate}
              onChange={(e) => set("inflation_rate", e.target.value)}
            />
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary flex-1"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Spinner size={14} className="text-obsidian-950" />{" "}
                Generating...
              </>
            ) : (
              <>
                <Lightbulb size={14} /> Generate Plan
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
