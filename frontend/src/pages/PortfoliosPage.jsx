import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  Plus,
  ArrowRight,
  Trash2,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { portfolio as portfolioApi } from "../api/client";
import {
  SectionHeader,
  Modal,
  EmptyState,
  Alert,
  Spinner,
} from "../components/ui";

export default function PortfoliosPage() {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const data = await portfolioApi.list();
      setPortfolios(data?.results || data || []);
    } catch {
      setError("Failed to load portfolios.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm("Delete this portfolio? This cannot be undone.")) return;
    await portfolioApi.delete(id);
    setPortfolios((ps) => ps.filter((p) => p.id !== id));
  };

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="page-header">
        <div>
          <h1 className="section-title text-3xl">Portfolios</h1>
          <p className="text-slate-500 text-sm mt-1">
            Manage your investment portfolios.
          </p>
          <div className="accent-line mt-2" />
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} /> New Portfolio
        </button>
      </div>

      {error && <Alert type="error" message={error} />}

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size={28} />
        </div>
      ) : portfolios.length === 0 ? (
        <div className="card p-12">
          <EmptyState
            icon={Briefcase}
            title="No portfolios yet"
            description="Create your first portfolio to begin tracking and optimizing your investments."
            action={
              <button
                onClick={() => setShowCreate(true)}
                className="btn-primary"
              >
                Create Portfolio
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolios.map((p) => {
            const value = parseFloat(p.total_value || p.cash_balance || 0);
            const cash = parseFloat(p.cash_balance || 0);
            const pnl = parseFloat(p.total_gain_loss || 0);
            const pnlPct = parseFloat(p.total_gain_loss_pct || 0);
            return (
              <div
                key={p.id}
                onClick={() => navigate(`/portfolios/${p.id}`)}
                className="card-hover p-6 cursor-pointer group relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-gold-500/3 -translate-x-8 -translate-y-16 group-hover:bg-gold-500/6 transition-all" />
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center">
                    <Briefcase size={18} className="text-gold-400" />
                  </div>
                  <button
                    onClick={(e) => handleDelete(p.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-crimson-400 transition-all p-1"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <h3 className="font-semibold text-slate-100 mb-1 truncate">
                  {p.name}
                </h3>
                {p.description && (
                  <p className="text-xs text-slate-500 mb-4 line-clamp-2">
                    {p.description}
                  </p>
                )}
                <div className="space-y-3 mt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Total Value</span>
                    <span className="font-mono font-semibold text-slate-100">
                      ${value.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">Cash Balance</span>
                    <span className="font-mono text-sm text-slate-300">
                      ${cash.toLocaleString()}
                    </span>
                  </div>
                  {pnl !== 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-slate-500">Total P&L</span>
                      <div className="flex items-center gap-1">
                        {pnl >= 0 ? (
                          <TrendingUp size={12} className="text-jade-500" />
                        ) : (
                          <TrendingDown
                            size={12}
                            className="text-crimson-400"
                          />
                        )}
                        <span
                          className={`font-mono text-sm ${pnl >= 0 ? "text-jade-500" : "text-crimson-400"}`}
                        >
                          {pnl >= 0 ? "+" : ""}${pnl.toLocaleString()} (
                          {pnlPct >= 0 ? "+" : ""}
                          {pnlPct.toFixed(1)}%)
                        </span>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between items-center pt-2 border-t border-obsidian-700">
                    <span className="text-xs text-slate-500">
                      {p.holdings_count || 0} holdings
                    </span>
                    <span className="text-xs text-slate-500">
                      {p.benchmark_ticker || "SPY"}
                    </span>
                    <ArrowRight
                      size={14}
                      className="text-slate-600 group-hover:text-gold-400 transition-colors"
                    />
                  </div>
                </div>
              </div>
            );
          })}

          {/* Add new card */}
          <button
            onClick={() => setShowCreate(true)}
            className="card border-dashed border-obsidian-500 hover:border-gold-500/40 hover:bg-gold-500/3
                       p-6 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all group min-h-[200px]"
          >
            <div className="w-12 h-12 rounded-full border-2 border-dashed border-obsidian-500 group-hover:border-gold-500/50 flex items-center justify-center transition-all">
              <Plus
                size={20}
                className="text-slate-600 group-hover:text-gold-400 transition-colors"
              />
            </div>
            <p className="text-sm text-slate-500 group-hover:text-slate-300 transition-colors">
              New Portfolio
            </p>
          </button>
        </div>
      )}

      <CreatePortfolioModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(p) => {
          setPortfolios((ps) => [...ps, p]);
          setShowCreate(false);
          navigate(`/portfolios/${p.id}`);
        }}
      />
    </div>
  );
}

function CreatePortfolioModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    cash_balance: "",
    benchmark_ticker: "SPY",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const p = await portfolioApi.create({
        ...form,
        cash_balance: parseFloat(form.cash_balance || 0),
      });
      onCreated(p);
      setForm({
        name: "",
        description: "",
        cash_balance: "",
        benchmark_ticker: "SPY",
      });
    } catch (err) {
      setError(
        err.data?.detail ||
          err.data?.name?.[0] ||
          "Failed to create portfolio.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Portfolio">
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="label">Portfolio Name *</label>
          <input
            className="input"
            placeholder="e.g. Growth Portfolio"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea
            className="input resize-none"
            rows={2}
            placeholder="Optional notes..."
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Starting Cash ($)</label>
            <input
              type="number"
              className="input"
              placeholder="10000"
              value={form.cash_balance}
              onChange={(e) => set("cash_balance", e.target.value)}
              min={0}
            />
          </div>
          <div>
            <label className="label">Benchmark Ticker</label>
            <input
              className="input"
              placeholder="SPY"
              value={form.benchmark_ticker}
              onChange={(e) =>
                set("benchmark_ticker", e.target.value.toUpperCase())
              }
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
              <Spinner size={15} className="text-obsidian-950" />
            ) : (
              "Create Portfolio"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
