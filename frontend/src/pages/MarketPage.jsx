import { useState, useEffect } from "react";
import {
  Search,
  TrendingUp,
  TrendingDown,
  Plus,
  Star,
  BarChart3,
  Brain,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { market } from "../api/client";
import {
  SectionHeader,
  Spinner,
  Alert,
  Modal,
  TabBar,
  EmptyState,
} from "../components/ui";

export default function MarketPage() {
  const [tab, setTab] = useState("quote");
  const [ticker, setTicker] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [quoteData, setQuoteData] = useState(null);
  const [histData, setHistData] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [predLoading, setPredLoading] = useState(false);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState("1y");

  useEffect(() => {
    market
      .sectors()
      .then((d) => setSectors(d || []))
      .catch(() => {});
  }, []);

  const handleSearch = async (q) => {
    setSearchQ(q);
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await market.search(q);
      setSearchResults(res?.results || res || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const loadQuote = async (t) => {
    if (!t) return;
    setLoading(true);
    setError("");
    setQuoteData(null);
    setHistData([]);
    setPrediction(null);
    try {
      const [q, h] = await Promise.all([
        market.quote(t),
        market.history(t, { period }),
      ]);
      setQuoteData(q);
      const bars = h?.data || h || [];
      setHistData(
        bars.map((b) => ({
          date: b.date?.slice(5),
          close: parseFloat(b.close || 0),
          volume: b.volume,
        })),
      );
    } catch (e) {
      setError(`Could not fetch data for ${t}. Check the ticker symbol.`);
    } finally {
      setLoading(false);
    }
  };

  const loadPrediction = async () => {
    if (!ticker) return;
    setPredLoading(true);
    try {
      const res = await market.predict(ticker, { horizon_days: 30 });
      setPrediction(res);
    } catch {
      setError("Prediction failed.");
    } finally {
      setPredLoading(false);
    }
  };

  const selectResult = (r) => {
    setTicker(r.symbol || r.ticker);
    setSearchResults([]);
    setSearchQ("");
    loadQuote(r.symbol || r.ticker);
  };

  const change = quoteData
    ? parseFloat(quoteData.change || quoteData.regularMarketChange || 0)
    : 0;
  const changePct = quoteData
    ? parseFloat(
        quoteData.change_pct || quoteData.regularMarketChangePercent || 0,
      )
    : 0;
  const isUp = change >= 0;

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="section-title text-3xl">Markets</h1>
        <p className="text-slate-500 text-sm mt-1">
          Live quotes, historical data, and AI predictions.
        </p>
        <div className="accent-line mt-2" />
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {/* Search */}
      <div className="card p-5">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              className="input pl-10"
              placeholder="Search ticker or company name (e.g. AAPL, Apple)..."
              value={searchQ || ticker}
              onChange={(e) => {
                setTicker(e.target.value.toUpperCase());
                handleSearch(e.target.value);
              }}
              onKeyDown={(e) => e.key === "Enter" && loadQuote(ticker)}
            />
            {searchResults.length > 0 && (
              <div className="absolute top-full mt-1 w-full bg-obsidian-800 border border-obsidian-600 rounded-xl shadow-2xl z-10 overflow-hidden">
                {searchResults.slice(0, 8).map((r) => (
                  <button
                    key={r.symbol || r.ticker}
                    onClick={() => selectResult(r)}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-obsidian-700 transition-colors text-left border-b border-obsidian-700 last:border-0"
                  >
                    <span className="font-mono text-sm font-semibold text-gold-400 w-16 shrink-0">
                      {r.symbol || r.ticker}
                    </span>
                    <span className="text-sm text-slate-300 truncate">
                      {r.name || r.longname}
                    </span>
                    <span className="text-xs text-slate-500 ml-auto shrink-0">
                      {r.exchange || r.type_disp}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => loadQuote(ticker)}
            disabled={loading || !ticker}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <Spinner size={15} className="text-obsidian-950" />
            ) : (
              <>
                <Search size={14} /> Look up
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quote result */}
      {quoteData && (
        <div className="grid lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3 card p-6">
            <div className="flex items-start justify-between mb-4 flex-wrap gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="font-mono text-3xl font-bold text-slate-100">
                    {quoteData.symbol || ticker}
                  </h2>
                  <span
                    className={`badge ${isUp ? "badge-jade" : "badge-crimson"}`}
                  >
                    {isUp ? "+" : ""}
                    {change.toFixed(2)} ({isUp ? "+" : ""}
                    {changePct.toFixed(2)}%)
                  </span>
                </div>
                <p className="text-slate-400 text-sm mt-1">
                  {quoteData.shortName || quoteData.longName || quoteData.name}
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-4xl font-bold text-slate-100">
                  $
                  {parseFloat(
                    quoteData.price || quoteData.regularMarketPrice || 0,
                  ).toFixed(2)}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {quoteData.exchange || quoteData.fullExchangeName} ·{" "}
                  {quoteData.currency || "USD"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-4 flex-wrap">
              {["1mo", "3mo", "6mo", "1y", "2y", "5y"].map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setPeriod(p);
                    loadQuote(ticker);
                  }}
                  className={`text-xs font-mono px-3 py-1 rounded-full border transition-all ${period === p ? "bg-gold-500/15 border-gold-500/30 text-gold-400" : "border-obsidian-600 text-slate-500 hover:border-obsidian-500"}`}
                >
                  {p}
                </button>
              ))}
            </div>

            {histData.length > 1 ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={histData}>
                  <defs>
                    <linearGradient id="qg" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor={isUp ? "#00e5a8" : "#ff4459"}
                        stopOpacity={0.2}
                      />
                      <stop
                        offset="95%"
                        stopColor={isUp ? "#00e5a8" : "#ff4459"}
                        stopOpacity={0}
                      />
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
                    tickFormatter={(v) => `$${v.toFixed(0)}`}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0d1521",
                      border: "1px solid #1a2840",
                      borderRadius: 8,
                      fontSize: 11,
                    }}
                    formatter={(v) => [`$${v.toFixed(2)}`, "Close"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={isUp ? "#00e5a8" : "#ff4459"}
                    strokeWidth={2}
                    fill="url(#qg)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : loading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : null}
          </div>

          <div className="space-y-4">
            <div className="card p-5 space-y-2">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
                Key Stats
              </p>
              {[
                [
                  "Day High",
                  `$${parseFloat(quoteData.dayHigh || quoteData.regularMarketDayHigh || 0).toFixed(2)}`,
                ],
                [
                  "Day Low",
                  `$${parseFloat(quoteData.dayLow || quoteData.regularMarketDayLow || 0).toFixed(2)}`,
                ],
                [
                  "52w High",
                  quoteData.fiftyTwoWeekHigh
                    ? `$${parseFloat(quoteData.fiftyTwoWeekHigh).toFixed(2)}`
                    : "—",
                ],
                [
                  "52w Low",
                  quoteData.fiftyTwoWeekLow
                    ? `$${parseFloat(quoteData.fiftyTwoWeekLow).toFixed(2)}`
                    : "—",
                ],
                [
                  "Volume",
                  quoteData.regularMarketVolume
                    ? Number(quoteData.regularMarketVolume).toLocaleString()
                    : "—",
                ],
                [
                  "Market Cap",
                  quoteData.marketCap
                    ? `$${(quoteData.marketCap / 1e9).toFixed(2)}B`
                    : "—",
                ],
                [
                  "P/E Ratio",
                  quoteData.trailingPE
                    ? parseFloat(quoteData.trailingPE).toFixed(2)
                    : "—",
                ],
                [
                  "Beta",
                  quoteData.beta ? parseFloat(quoteData.beta).toFixed(3) : "—",
                ],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between text-xs">
                  <span className="text-slate-500">{l}</span>
                  <span className="font-mono text-slate-300">{v}</span>
                </div>
              ))}
            </div>

            <button
              onClick={loadPrediction}
              disabled={predLoading}
              className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
            >
              {predLoading ? (
                <Spinner size={14} />
              ) : (
                <>
                  <Brain size={14} /> AI Prediction
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Prediction result */}
      {prediction && (
        <div className="card p-6 border-jade-500/20">
          <SectionHeader
            title="AI Price Prediction"
            subtitle={`${ticker} — 30-day horizon`}
            actions={
              <button
                onClick={() => setPrediction(null)}
                className="btn-ghost text-xs"
              >
                Dismiss
              </button>
            }
          />
          <div className="grid lg:grid-cols-3 gap-4">
            {[
              {
                label: "Predicted Price",
                value: `$${parseFloat(prediction.predicted_price || 0).toFixed(2)}`,
                accent: "gold",
              },
              {
                label: "Expected Return",
                value: `${((prediction.expected_return || 0) * 100).toFixed(2)}%`,
                accent:
                  parseFloat(prediction.expected_return) >= 0
                    ? "jade"
                    : "crimson",
              },
              {
                label: "Market Regime",
                value: prediction.regime || "—",
                accent: "slate",
              },
            ].map((m) => (
              <div
                key={m.label}
                className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700 text-center"
              >
                <p className="text-xs text-slate-500 mb-2">{m.label}</p>
                <p
                  className={`font-mono font-bold text-xl ${m.accent === "gold" ? "text-gold-400" : m.accent === "jade" ? "text-jade-500" : m.accent === "crimson" ? "text-crimson-400" : "text-slate-300"}`}
                >
                  {m.value}
                </p>
              </div>
            ))}
          </div>
          {prediction.confidence && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-slate-500">Prediction Confidence</span>
                <span className="font-mono text-gold-400">
                  {(parseFloat(prediction.confidence) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 bg-obsidian-900 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all"
                  style={{
                    width: `${parseFloat(prediction.confidence) * 100}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sector heatmap */}
      {sectors.length > 0 && (
        <div className="card p-6">
          <SectionHeader
            title="Sector Performance"
            subtitle="Year-to-date returns"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {sectors.map((s) => {
              const r = parseFloat(s.ytd_return || s.change || 0) * 100;
              const intensity = Math.min(Math.abs(r) / 30, 1);
              return (
                <div
                  key={s.sector || s.name}
                  className="p-4 rounded-xl border transition-all"
                  style={{
                    background:
                      r >= 0
                        ? `rgba(0, 229, 168, ${0.03 + intensity * 0.1})`
                        : `rgba(255, 68, 89, ${0.03 + intensity * 0.1})`,
                    borderColor:
                      r >= 0
                        ? `rgba(0, 229, 168, ${0.1 + intensity * 0.2})`
                        : `rgba(255, 68, 89, ${0.1 + intensity * 0.2})`,
                  }}
                >
                  <p className="text-xs text-slate-400 mb-2 leading-tight">
                    {s.sector || s.name}
                  </p>
                  <p
                    className={`font-mono font-bold text-lg ${r >= 0 ? "text-jade-500" : "text-crimson-400"}`}
                  >
                    {r >= 0 ? "+" : ""}
                    {r.toFixed(2)}%
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
