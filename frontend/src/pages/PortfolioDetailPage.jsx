import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Zap,
  TrendingUp,
  BarChart3,
  DollarSign,
  RefreshCw,
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
import { portfolio as portfolioApi } from "../api/client";
import {
  SectionHeader,
  Modal,
  Alert,
  Spinner,
  TabBar,
  EmptyState,
  MetricRow,
} from "../components/ui";

const COLORS = [
  "#e8b320",
  "#00e5a8",
  "#3b82f6",
  "#a855f7",
  "#f97316",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
];
const ASSET_CLASSES = [
  "equity",
  "fixed_income",
  "real_estate",
  "commodity",
  "crypto",
  "cash",
  "alternative",
];
const TX_TYPES = [
  "buy",
  "sell",
  "deposit",
  "withdrawal",
  "dividend",
  "split",
  "transfer_in",
  "transfer_out",
];

export default function PortfolioDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [history, setHistory] = useState([]);
  const [optimizeResult, setOptimizeResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("holdings");
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [showAddTx, setShowAddTx] = useState(false);
  const [showOptimize, setShowOptimize] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [pData, hData, txData, histData] = await Promise.all([
        portfolioApi.get(id),
        portfolioApi.holdings(id),
        portfolioApi.transactions(id),
        portfolioApi.history(id),
      ]);
      setP(pData);
      setHoldings(hData?.results || hData || []);
      setTransactions((txData?.results || txData || []).slice(0, 50));
      const raw = histData?.snapshots || histData || [];
      setHistory(
        raw
          .slice(0, 90)
          .reverse()
          .map((s) => ({
            date: s.date?.slice(5),
            value: parseFloat(s.total_value || 0),
          })),
      );
    } catch {
      setError("Failed to load portfolio.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleOptimize = async (strategy, riskTolerance) => {
    setOptimizing(true);
    try {
      const res = await portfolioApi.optimize(id, {
        strategy,
        risk_tolerance: riskTolerance,
      });
      setOptimizeResult(res);
    } catch {
      setError(
        "Optimization failed. Ensure your portfolio has at least 2 holdings with sufficient history.",
      );
    } finally {
      setOptimizing(false);
      setShowOptimize(false);
    }
  };

  if (loading)
    return (
      <div className="flex justify-center pt-20">
        <Spinner size={28} />
      </div>
    );
  if (!p)
    return (
      <div className="text-center text-slate-500 pt-20">
        Portfolio not found.
      </div>
    );

  const totalValue = parseFloat(p.total_value || p.cash_balance || 0);
  const pieData = holdings
    .map((h) => ({
      name: h.ticker,
      value: parseFloat(h.market_value || h.quantity * h.average_cost || 0),
    }))
    .filter((x) => x.value > 0);

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate("/portfolios")}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 text-sm mb-3 transition-colors"
        >
          <ArrowLeft size={14} /> Back to Portfolios
        </button>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="section-title text-3xl">{p.name}</h1>
            {p.description && (
              <p className="text-slate-500 text-sm mt-1">{p.description}</p>
            )}
            <div className="accent-line mt-2" />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setShowAddTx(true)}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <Plus size={14} /> Transaction
            </button>
            <button
              onClick={() => setShowAddHolding(true)}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <Plus size={14} /> Holding
            </button>
            <button
              onClick={() => setShowOptimize(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Zap size={14} /> Optimize
            </button>
          </div>
        </div>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total Value",
            value: `$${totalValue.toLocaleString()}`,
            accent: "gold",
          },
          {
            label: "Cash Balance",
            value: `$${parseFloat(p.cash_balance || 0).toLocaleString()}`,
            accent: "jade",
          },
          { label: "Holdings", value: holdings.length, accent: "slate" },
          {
            label: "Benchmark",
            value: p.benchmark_ticker || "SPY",
            accent: "slate",
          },
        ].map((s) => (
          <div key={s.label} className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
              {s.label}
            </p>
            <p
              className={`text-xl font-mono font-semibold ${s.accent === "gold" ? "text-gold-400" : s.accent === "jade" ? "text-jade-500" : "text-slate-200"}`}
            >
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 card p-6">
          <SectionHeader title="Value History" subtitle="Last 90 days" />
          {history.length > 1 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="vg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e8b320" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#e8b320" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#475569", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#475569", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0d1521",
                    border: "1px solid #1a2840",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  formatter={(v) => [`$${v.toLocaleString()}`, "Value"]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#e8b320"
                  strokeWidth={2}
                  fill="url(#vg)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-500 text-center py-12">
              Take a portfolio snapshot to start tracking history.
            </p>
          )}
          <div className="flex justify-end mt-2">
            <button
              onClick={() => portfolioApi.snapshot(id).then(load)}
              className="btn-ghost text-xs flex items-center gap-1"
            >
              <RefreshCw size={12} /> Snapshot Now
            </button>
          </div>
        </div>

        {/* Allocation pie */}
        <div className="card p-6">
          <SectionHeader title="Allocation" />
          {pieData.length > 0 ? (
            <div className="flex flex-col items-center gap-3">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={65}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#0d1521",
                      border: "1px solid #1a2840",
                      borderRadius: 8,
                      fontSize: 11,
                    }}
                    formatter={(v) => [`$${v.toLocaleString()}`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="w-full space-y-1.5">
                {pieData.slice(0, 6).map((d, i) => (
                  <div
                    key={d.name}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-1.5">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: COLORS[i % COLORS.length] }}
                      />
                      <span className="text-slate-400 font-mono">{d.name}</span>
                    </div>
                    <span className="text-slate-300 font-mono">
                      {((d.value / totalValue) * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState icon={BarChart3} title="No holdings" />
          )}
        </div>
      </div>

      {/* Optimization result */}
      {optimizeResult && (
        <div className="card p-6 border-gold-500/20">
          <SectionHeader
            title="Optimization Result"
            subtitle={`Strategy: ${optimizeResult.strategy?.replace("_", " ")}`}
            actions={
              <button
                onClick={() => setOptimizeResult(null)}
                className="btn-ghost text-xs"
              >
                Dismiss
              </button>
            }
          />
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-2">
              <MetricRow
                label="Expected Annual Return"
                value={`${((optimizeResult.expected_return || 0) * 100).toFixed(2)}%`}
                highlight
              />
              <MetricRow
                label="Expected Volatility"
                value={`${((optimizeResult.expected_volatility || 0) * 100).toFixed(2)}%`}
              />
              <MetricRow
                label="Sharpe Ratio"
                value={(optimizeResult.sharpe_ratio || 0).toFixed(3)}
                highlight
              />
            </div>
            <div className="lg:col-span-2">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
                Allocation Changes
              </p>
              <div className="space-y-1.5">
                {(optimizeResult.allocations || []).map((a) => (
                  <div
                    key={a.ticker}
                    className="flex items-center gap-3 text-xs"
                  >
                    <span className="font-mono text-slate-400 w-14 shrink-0">
                      {a.ticker}
                    </span>
                    <div className="flex-1 bg-obsidian-900 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full bg-gold-500 rounded-full"
                        style={{ width: `${(a.target_weight || 0) * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-slate-300 w-14 text-right">
                      {((a.target_weight || 0) * 100).toFixed(1)}%
                    </span>
                    <span
                      className={`font-medium w-16 text-right ${a.suggested_action === "BUY" ? "text-jade-500" : a.suggested_action === "SELL" ? "text-crimson-400" : "text-slate-500"}`}
                    >
                      {a.suggested_action || "—"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="card p-6">
        <div className="mb-5">
          <TabBar
            tabs={[
              { label: "Holdings", value: "holdings" },
              { label: "Transactions", value: "transactions" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </div>

        {tab === "holdings" &&
          (holdings.length === 0 ? (
            <EmptyState
              icon={TrendingUp}
              title="No holdings"
              action={
                <button
                  onClick={() => setShowAddHolding(true)}
                  className="btn-primary text-sm"
                >
                  Add Holding
                </button>
              }
            />
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Name</th>
                    <th>Asset Class</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Avg Cost</th>
                    <th className="text-right">Market Value</th>
                    <th className="text-right">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => {
                    const mv = parseFloat(h.market_value || 0);
                    const cost =
                      parseFloat(h.quantity) * parseFloat(h.average_cost);
                    const pnl = mv - cost;
                    return (
                      <tr key={h.id}>
                        <td>
                          <span className="font-mono font-semibold text-gold-400">
                            {h.ticker}
                          </span>
                        </td>
                        <td>
                          <span className="text-slate-300">
                            {h.name || "—"}
                          </span>
                        </td>
                        <td>
                          <span className="badge-slate">
                            {h.asset_class || "equity"}
                          </span>
                        </td>
                        <td className="text-right font-mono">
                          {parseFloat(h.quantity).toFixed(4)}
                        </td>
                        <td className="text-right font-mono">
                          ${parseFloat(h.average_cost).toFixed(2)}
                        </td>
                        <td className="text-right font-mono">
                          {mv > 0 ? `$${mv.toLocaleString()}` : "—"}
                        </td>
                        <td
                          className={`text-right font-mono font-medium ${pnl >= 0 ? "text-jade-500" : "text-crimson-400"}`}
                        >
                          {mv > 0
                            ? `${pnl >= 0 ? "+" : ""}$${pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}

        {tab === "transactions" &&
          (transactions.length === 0 ? (
            <EmptyState
              icon={DollarSign}
              title="No transactions"
              action={
                <button
                  onClick={() => setShowAddTx(true)}
                  className="btn-primary text-sm"
                >
                  Add Transaction
                </button>
              }
            />
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Ticker</th>
                    <th className="text-right">Amount</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Price</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.id}>
                      <td className="font-mono text-xs text-slate-400">
                        {tx.executed_at?.slice(0, 10)}
                      </td>
                      <td>
                        <span
                          className={`badge ${tx.transaction_type === "buy" ? "badge-jade" : tx.transaction_type === "sell" ? "badge-crimson" : "badge-slate"}`}
                        >
                          {tx.transaction_type}
                        </span>
                      </td>
                      <td>
                        <span className="font-mono font-semibold text-gold-400">
                          {tx.ticker || "—"}
                        </span>
                      </td>
                      <td className="text-right font-mono">
                        ${parseFloat(tx.amount || 0).toLocaleString()}
                      </td>
                      <td className="text-right font-mono">
                        {tx.quantity ? parseFloat(tx.quantity).toFixed(4) : "—"}
                      </td>
                      <td className="text-right font-mono">
                        {tx.price ? `$${parseFloat(tx.price).toFixed(2)}` : "—"}
                      </td>
                      <td className="text-xs text-slate-500 max-w-xs truncate">
                        {tx.notes || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>

      {/* Modals */}
      <AddHoldingModal
        open={showAddHolding}
        onClose={() => setShowAddHolding(false)}
        onAdded={() => {
          setShowAddHolding(false);
          load();
        }}
        portfolioId={id}
      />
      <AddTransactionModal
        open={showAddTx}
        onClose={() => setShowAddTx(false)}
        onAdded={() => {
          setShowAddTx(false);
          load();
        }}
        portfolioId={id}
      />
      <OptimizeModal
        open={showOptimize}
        onClose={() => setShowOptimize(false)}
        onSubmit={handleOptimize}
        loading={optimizing}
      />
    </div>
  );
}

function AddHoldingModal({ open, onClose, onAdded, portfolioId }) {
  const [form, setForm] = useState({
    ticker: "",
    quantity: "",
    average_cost: "",
    name: "",
    asset_class: "equity",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await portfolioApi.addHolding(portfolioId, {
        ...form,
        ticker: form.ticker.toUpperCase(),
        quantity: parseFloat(form.quantity),
        average_cost: parseFloat(form.average_cost),
      });
      onAdded();
      setForm({
        ticker: "",
        quantity: "",
        average_cost: "",
        name: "",
        asset_class: "equity",
      });
    } catch (err) {
      setError(err.data?.detail || "Failed to add holding.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Add Holding">
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Ticker *</label>
            <input
              className="input font-mono"
              placeholder="AAPL"
              value={form.ticker}
              onChange={(e) => set("ticker", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Asset Class</label>
            <select
              className="select"
              value={form.asset_class}
              onChange={(e) => set("asset_class", e.target.value)}
            >
              {ASSET_CLASSES.map((c) => (
                <option key={c} value={c}>
                  {c.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Security Name</label>
          <input
            className="input"
            placeholder="Apple Inc."
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Quantity *</label>
            <input
              type="number"
              className="input"
              placeholder="10"
              value={form.quantity}
              onChange={(e) => set("quantity", e.target.value)}
              required
              step="any"
              min={0}
            />
          </div>
          <div>
            <label className="label">Avg Cost per Share *</label>
            <input
              type="number"
              className="input"
              placeholder="150.00"
              value={form.average_cost}
              onChange={(e) => set("average_cost", e.target.value)}
              required
              step="any"
              min={0}
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
            className="btn-primary flex-1 flex items-center justify-center"
          >
            {loading ? (
              <Spinner size={15} className="text-obsidian-950" />
            ) : (
              "Add Holding"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function AddTransactionModal({ open, onClose, onAdded, portfolioId }) {
  const [form, setForm] = useState({
    transaction_type: "buy",
    amount: "",
    ticker: "",
    quantity: "",
    price: "",
    fees: "0",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = {
        ...form,
        amount: parseFloat(form.amount),
        fees: parseFloat(form.fees || 0),
      };
      if (form.quantity) body.quantity = parseFloat(form.quantity);
      if (form.price) body.price = parseFloat(form.price);
      if (form.ticker) body.ticker = form.ticker.toUpperCase();
      await portfolioApi.addTransaction(portfolioId, body);
      onAdded();
      setForm({
        transaction_type: "buy",
        amount: "",
        ticker: "",
        quantity: "",
        price: "",
        fees: "0",
        notes: "",
      });
    } catch (err) {
      setError(err.data?.detail || "Failed to record transaction.");
    } finally {
      setLoading(false);
    }
  };

  const needsTicker = ["buy", "sell"].includes(form.transaction_type);

  return (
    <Modal open={open} onClose={onClose} title="Record Transaction">
      {error && (
        <div className="mb-4">
          <Alert type="error" message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Type *</label>
            <select
              className="select"
              value={form.transaction_type}
              onChange={(e) => set("transaction_type", e.target.value)}
            >
              {TX_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Amount ($) *</label>
            <input
              type="number"
              className="input"
              placeholder="1500.00"
              value={form.amount}
              onChange={(e) => set("amount", e.target.value)}
              required
              step="any"
              min={0}
            />
          </div>
        </div>
        {needsTicker && (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label">Ticker *</label>
              <input
                className="input font-mono"
                placeholder="AAPL"
                value={form.ticker}
                onChange={(e) => set("ticker", e.target.value)}
                required={needsTicker}
              />
            </div>
            <div>
              <label className="label">Quantity</label>
              <input
                type="number"
                className="input"
                placeholder="10"
                value={form.quantity}
                onChange={(e) => set("quantity", e.target.value)}
                step="any"
                min={0}
              />
            </div>
            <div>
              <label className="label">Price/Share</label>
              <input
                type="number"
                className="input"
                placeholder="150.00"
                value={form.price}
                onChange={(e) => set("price", e.target.value)}
                step="any"
                min={0}
              />
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Fees ($)</label>
            <input
              type="number"
              className="input"
              value={form.fees}
              onChange={(e) => set("fees", e.target.value)}
              step="any"
              min={0}
            />
          </div>
        </div>
        <div>
          <label className="label">Notes</label>
          <input
            className="input"
            placeholder="Optional notes..."
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
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
              "Record"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function OptimizeModal({ open, onClose, onSubmit, loading }) {
  const [strategy, setStrategy] = useState("mean_variance");
  const [risk, setRisk] = useState(0.5);
  const strategies = [
    { value: "mean_variance", label: "Mean-Variance" },
    { value: "black_litterman", label: "Black-Litterman" },
    { value: "risk_parity", label: "Risk Parity" },
    { value: "hrp", label: "Hierarchical Risk Parity" },
  ];
  return (
    <Modal open={open} onClose={onClose} title="AI Portfolio Optimization">
      <div className="space-y-5">
        <div>
          <label className="label">Optimization Strategy</label>
          <div className="grid grid-cols-2 gap-2">
            {strategies.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setStrategy(s.value)}
                className={`p-3 rounded-xl text-left border transition-all text-sm ${strategy === s.value ? "bg-gold-500/10 border-gold-500/30 text-gold-400" : "bg-obsidian-900 border-obsidian-600 text-slate-400 hover:border-obsidian-500"}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Risk Tolerance: {risk.toFixed(1)}</label>
          <div className="flex items-center gap-3">
            <span className="text-xs text-jade-500">Conservative</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={risk}
              onChange={(e) => setRisk(parseFloat(e.target.value))}
              className="flex-1 h-1.5 bg-obsidian-700 rounded-full appearance-none cursor-pointer accent-gold-500"
            />
            <span className="text-xs text-crimson-400">Aggressive</span>
          </div>
        </div>
        <p className="text-xs text-slate-500 bg-obsidian-900 rounded-lg p-3 border border-obsidian-700">
          Optimization requires at least 2 holdings with 1+ year of price
          history. Heavy computation may take a few seconds.
        </p>
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-secondary flex-1">
            Cancel
          </button>
          <button
            onClick={() => onSubmit(strategy, risk)}
            disabled={loading}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Spinner size={15} className="text-obsidian-950" /> Running...
              </>
            ) : (
              <>
                <Zap size={15} /> Optimize
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
