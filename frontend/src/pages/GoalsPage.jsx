import { useState, useEffect } from "react";
import {
  Target,
  Plus,
  Trash2,
  TrendingUp,
  Calendar,
  DollarSign,
} from "lucide-react";
import { portfolio as portfolioApi } from "../api/client";
import {
  SectionHeader,
  Modal,
  Alert,
  Spinner,
  EmptyState,
} from "../components/ui";

const GOAL_TYPE_CONFIG = {
  retirement: { icon: "🏖️", color: "gold" },
  education: { icon: "🎓", color: "jade" },
  house: { icon: "🏠", color: "jade" },
  emergency_fund: { icon: "🛡️", color: "crimson" },
  vacation: { icon: "✈️", color: "jade" },
  custom: { icon: "🎯", color: "slate" },
};

export default function GoalsPage() {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [goalPlan, setGoalPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const data = await portfolioApi.goals();
      setGoals(data?.results || data || []);
    } catch {
      setError("Failed to load goals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("Delete this goal?")) return;
    await portfolioApi.deleteGoal(id);
    setGoals((gs) => gs.filter((g) => g.id !== id));
    if (selectedGoal?.id === id) {
      setSelectedGoal(null);
      setGoalPlan(null);
    }
  };

  const selectGoal = (goal) => {
    setSelectedGoal(goal);
    setGoalPlan(null);
  };

  const generatePlan = async () => {
    if (!selectedGoal) return;
    setPlanLoading(true);
    try {
      const plan = await portfolioApi.planGoal(selectedGoal.id, {
        goal_type: selectedGoal.goal_type,
        target_amount: parseFloat(selectedGoal.target_amount),
        current_amount: parseFloat(selectedGoal.current_amount || 0),
        monthly_contribution: parseFloat(
          selectedGoal.monthly_contribution || 0,
        ),
        target_date: selectedGoal.target_date,
      });
      setGoalPlan(plan);
    } catch {
      setError("Failed to generate plan.");
    } finally {
      setPlanLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="page-header">
        <div>
          <h1 className="section-title text-3xl">Financial Goals</h1>
          <p className="text-slate-500 text-sm mt-1">
            Track and plan your financial objectives.
          </p>
          <div className="accent-line mt-2" />
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} /> New Goal
        </button>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size={28} />
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Goals list */}
          <div className="lg:col-span-1 space-y-3">
            {goals.length === 0 ? (
              <div className="card p-8">
                <EmptyState
                  icon={Target}
                  title="No goals yet"
                  action={
                    <button
                      onClick={() => setShowCreate(true)}
                      className="btn-primary text-sm"
                    >
                      Create Goal
                    </button>
                  }
                />
              </div>
            ) : (
              goals.map((g) => {
                const cfg =
                  GOAL_TYPE_CONFIG[g.goal_type] || GOAL_TYPE_CONFIG.custom;
                const progress =
                  g.current_amount && g.target_amount
                    ? Math.min(
                        100,
                        (parseFloat(g.current_amount) /
                          parseFloat(g.target_amount)) *
                          100,
                      )
                    : 0;
                const isSelected = selectedGoal?.id === g.id;
                return (
                  <div
                    key={g.id}
                    onClick={() => selectGoal(g)}
                    className={`card-hover p-4 cursor-pointer transition-all group ${isSelected ? "border-gold-500/40 bg-gold-500/5" : ""}`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-xl">{cfg.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-200 truncate">
                          {g.name || g.goal_type}
                        </p>
                        <p className="text-xs text-slate-500 capitalize">
                          {g.goal_type?.replace("_", " ")}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(g.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-crimson-400 transition-all"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">
                          ${parseFloat(g.current_amount || 0).toLocaleString()}{" "}
                          saved
                        </span>
                        <span className="font-mono text-slate-300">
                          ${parseFloat(g.target_amount || 0).toLocaleString()}
                        </span>
                      </div>
                      <div className="h-1.5 bg-obsidian-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gold-500 rounded-full transition-all"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 text-right">
                        {progress.toFixed(0)}% complete
                      </p>
                    </div>
                    {g.target_date && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                        <Calendar size={11} />
                        <span>
                          Target: {new Date(g.target_date).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {goals.length > 0 && (
              <button
                onClick={() => setShowCreate(true)}
                className="w-full card border-dashed p-4 text-sm text-slate-500 hover:text-slate-300 hover:border-obsidian-500 flex items-center justify-center gap-2 transition-all"
              >
                <Plus size={14} /> Add Goal
              </button>
            )}
          </div>

          {/* Goal detail */}
          <div className="lg:col-span-2">
            {!selectedGoal ? (
              <div className="card p-12 h-full">
                <EmptyState
                  icon={Target}
                  title="Select a goal"
                  description="Click on a goal to view details and generate an AI attainment plan."
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="card p-6">
                  <div className="flex items-start justify-between mb-6">
                    <div>
                      <h2 className="font-display text-2xl font-semibold text-slate-100">
                        {selectedGoal.name || selectedGoal.goal_type}
                      </h2>
                      <p className="text-slate-500 text-sm capitalize">
                        {selectedGoal.goal_type?.replace("_", " ")}
                      </p>
                    </div>
                    <button
                      onClick={generatePlan}
                      disabled={planLoading}
                      className="btn-primary flex items-center gap-2 text-sm"
                    >
                      {planLoading ? (
                        <Spinner size={14} className="text-obsidian-950" />
                      ) : (
                        <TrendingUp size={14} />
                      )}
                      Generate Plan
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {[
                      {
                        label: "Target Amount",
                        value: `$${parseFloat(selectedGoal.target_amount || 0).toLocaleString()}`,
                        icon: DollarSign,
                      },
                      {
                        label: "Current Savings",
                        value: `$${parseFloat(selectedGoal.current_amount || 0).toLocaleString()}`,
                        icon: TrendingUp,
                      },
                      {
                        label: "Monthly Contribution",
                        value: `$${parseFloat(selectedGoal.monthly_contribution || 0).toLocaleString()}/mo`,
                        icon: Calendar,
                      },
                      {
                        label: "Target Date",
                        value: selectedGoal.target_date
                          ? new Date(
                              selectedGoal.target_date,
                            ).toLocaleDateString()
                          : "—",
                        icon: Calendar,
                      },
                    ].map((m) => (
                      <div
                        key={m.label}
                        className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700"
                      >
                        <p className="text-xs text-slate-500 mb-1">{m.label}</p>
                        <p className="font-mono font-semibold text-slate-100">
                          {m.value}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Progress bar */}
                  {selectedGoal.target_amount && (
                    <div className="mt-6">
                      <div className="flex justify-between text-xs mb-2">
                        <span className="text-slate-500">Progress to goal</span>
                        <span className="font-mono text-gold-400">
                          {Math.min(
                            100,
                            (parseFloat(selectedGoal.current_amount || 0) /
                              parseFloat(selectedGoal.target_amount)) *
                              100,
                          ).toFixed(1)}
                          %
                        </span>
                      </div>
                      <div className="h-3 bg-obsidian-900 rounded-full overflow-hidden border border-obsidian-700">
                        <div
                          className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all"
                          style={{
                            width: `${Math.min(100, (parseFloat(selectedGoal.current_amount || 0) / parseFloat(selectedGoal.target_amount)) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Plan result */}
                {goalPlan && (
                  <div className="card p-6 border-gold-500/20">
                    <SectionHeader title="AI Attainment Plan" />
                    <div className="grid grid-cols-3 gap-4 mb-5">
                      {[
                        {
                          label: "Status",
                          value: goalPlan.gap_analysis
                            ? goalPlan.gap_analysis.on_track
                              ? "on track"
                              : "behind pace"
                            : "—",
                          accent: goalPlan.gap_analysis?.on_track
                            ? "jade"
                            : "crimson",
                        },
                        {
                          label: "Projected Value",
                          value: goalPlan.projected_value
                            ? `$${parseFloat(goalPlan.projected_value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                            : "—",
                          accent: "gold",
                        },
                        {
                          label: "Success Probability",
                          value:
                            goalPlan.probability_of_success != null
                              ? `${(goalPlan.probability_of_success * 100).toFixed(0)}%`
                              : "—",
                          accent: "jade",
                        },
                      ].map((m) => (
                        <div
                          key={m.label}
                          className="p-3 rounded-xl bg-obsidian-900 border border-obsidian-700 text-center"
                        >
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
                            {m.label}
                          </p>
                          <p
                            className={`font-mono font-bold text-base capitalize ${m.accent === "gold" ? "text-gold-400" : m.accent === "jade" ? "text-jade-500" : "text-crimson-400"}`}
                          >
                            {m.value}
                          </p>
                        </div>
                      ))}
                    </div>
                    {goalPlan.gap_analysis && (
                      <p className="text-sm text-slate-300 bg-obsidian-900 rounded-xl p-4 border border-obsidian-700 leading-relaxed">
                        {goalPlan.gap_analysis.on_track
                          ? "You're on track to reach this goal at your current contribution rate."
                          : `You're behind pace by $${Math.abs(goalPlan.gap_analysis.gap_amount || 0).toLocaleString()}. Increasing your monthly contribution would help close the gap.`}
                      </p>
                    )}
                    {goalPlan.recommended_monthly_contribution != null && (
                      <div className="mt-4 p-4 rounded-xl bg-gold-500/5 border border-gold-500/20">
                        <p className="text-xs text-slate-500 mb-1">
                          Recommended Monthly Contribution
                        </p>
                        <p className="font-mono font-bold text-xl text-gold-400">
                          $
                          {parseFloat(
                            goalPlan.recommended_monthly_contribution,
                          ).toLocaleString()}
                          /mo
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <CreateGoalModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(g) => {
          setGoals((gs) => [...gs, g]);
          setShowCreate(false);
          setSelectedGoal(g);
        }}
      />
    </div>
  );
}

function CreateGoalModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "",
    goal_type: "retirement",
    target_amount: "",
    current_savings: "0",
    monthly_contribution: "",
    target_date: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const g = await portfolioApi.createGoal({
        ...form,
        target_amount: parseFloat(form.target_amount),
        current_amount: parseFloat(form.current_savings || 0),
        monthly_contribution: parseFloat(form.monthly_contribution || 0),
      });
      onCreated(g);
      setForm({
        name: "",
        goal_type: "retirement",
        target_amount: "",
        current_savings: "0",
        monthly_contribution: "",
        target_date: "",
      });
    } catch (err) {
      setError(err.data?.detail || "Failed to create goal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Financial Goal">
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="label">Goal Name</label>
          <input
            className="input"
            placeholder="e.g. Retirement at 65"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Goal Type</label>
            <select
              className="select"
              value={form.goal_type}
              onChange={(e) => set("goal_type", e.target.value)}
            >
              {Object.keys(GOAL_TYPE_CONFIG).map((t) => (
                <option key={t} value={t}>
                  {GOAL_TYPE_CONFIG[t].icon} {t.replace("_", " ")}
                </option>
              ))}
            </select>
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
        </div>
        <div className="grid grid-cols-2 gap-3">
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
          <div>
            <label className="label">Current Savings ($)</label>
            <input
              type="number"
              className="input"
              placeholder="10000"
              value={form.current_savings}
              onChange={(e) => set("current_savings", e.target.value)}
              min={0}
            />
          </div>
        </div>
        <div>
          <label className="label">Monthly Contribution ($)</label>
          <input
            type="number"
            className="input"
            placeholder="2000"
            value={form.monthly_contribution}
            onChange={(e) => set("monthly_contribution", e.target.value)}
            min={0}
          />
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
            className="btn-primary flex-1 flex items-center justify-center"
          >
            {loading ? (
              <Spinner size={15} className="text-obsidian-950" />
            ) : (
              "Create Goal"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
