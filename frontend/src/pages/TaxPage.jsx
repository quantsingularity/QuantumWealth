import { useState, useEffect } from "react";
import {
  Receipt,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Search,
} from "lucide-react";
import { portfolio as portfolioApi, tax } from "../api/client";
import {
  SectionHeader,
  Spinner,
  Alert,
  Select,
  TabBar,
  EmptyState,
  MetricRow,
} from "../components/ui";

export default function TaxPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [tab, setTab] = useState("harvest");
  const [harvestData, setHarvestData] = useState(null);
  const [gainLoss, setGainLoss] = useState(null);
  const [assetLocation, setAssetLocation] = useState(null);
  const [washSaleResult, setWashSaleResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [taxYear, setTaxYear] = useState(new Date().getFullYear());
  const [washForm, setWashForm] = useState({ ticker: "", sell_date: "" });

  useEffect(() => {
    portfolioApi.list().then((d) => {
      const list = d?.results || d || [];
      setPortfolios(list);
      if (list.length > 0) setSelectedId(list[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadAll();
  }, [selectedId]);

  const loadAll = async () => {
    setLoading(true);
    setError("");
    try {
      const [harv, gl, al] = await Promise.allSettled([
        tax.harvest(selectedId, {}),
        tax.gainLoss(selectedId, { tax_year: taxYear }),
        tax.assetLocation(selectedId),
      ]);
      setHarvestData(harv.value);
      setGainLoss(gl.value);
      setAssetLocation(al.value);
    } catch (e) {
      setError("Failed to load tax data.");
    } finally {
      setLoading(false);
    }
  };

  const checkWashSale = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await tax.washSaleCheck(selectedId, {
        ticker: washForm.ticker.toUpperCase(),
        sell_date: washForm.sell_date,
      });
      setWashSaleResult(res);
    } catch {
      setError("Wash-sale check failed.");
    } finally {
      setLoading(false);
    }
  };

  const harvestOpps = harvestData?.opportunities || harvestData || [];
  const totalST = parseFloat(gainLoss?.short_term_gain_loss || 0);
  const totalLT = parseFloat(gainLoss?.long_term_gain_loss || 0);
  const totalTaxable = parseFloat(
    gainLoss?.total_taxable_gain_loss || totalST + totalLT || 0,
  );

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="section-title text-3xl">Tax Center</h1>
          <p className="text-slate-500 text-sm mt-1">
            Tax-loss harvesting, gain/loss reporting, and wash-sale compliance.
          </p>
          <div className="accent-line mt-2" />
        </div>
        <Select
          value={selectedId}
          onChange={setSelectedId}
          options={portfolios.map((p) => ({ value: p.id, label: p.name }))}
          className="w-48"
        />
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}

      {/* Tax year summary */}
      {gainLoss && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              label: `${taxYear} Short-Term G/L`,
              value: totalST,
              isCurrency: true,
            },
            {
              label: `${taxYear} Long-Term G/L`,
              value: totalLT,
              isCurrency: true,
            },
            {
              label: "Total Taxable G/L",
              value: totalTaxable,
              isCurrency: true,
            },
          ].map((m) => (
            <div key={m.label} className="card p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                {m.label}
              </p>
              <p
                className={`text-xl font-mono font-bold ${m.value >= 0 ? "text-jade-500" : "text-crimson-400"}`}
              >
                {m.value >= 0 ? "+" : "-"}${Math.abs(m.value).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      <TabBar
        tabs={[
          { label: "Harvest Opportunities", value: "harvest" },
          { label: "Gain / Loss Report", value: "gainloss" },
          { label: "Asset Location", value: "location" },
          { label: "Wash-Sale Check", value: "washsale" },
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
          {/* Harvest */}
          {tab === "harvest" &&
            (harvestOpps.length === 0 ? (
              <div className="card p-12">
                <EmptyState
                  icon={CheckCircle2}
                  title="No harvest opportunities"
                  description="No tax-loss harvesting opportunities identified at this time."
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="card p-4 border-gold-500/15">
                  <p className="text-sm text-gold-400 font-medium flex items-center gap-2">
                    <Receipt size={14} />
                    {harvestOpps.length} tax-loss harvesting{" "}
                    {harvestOpps.length === 1 ? "opportunity" : "opportunities"}{" "}
                    identified
                  </p>
                </div>
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Name</th>
                        <th className="text-right">Unrealized Loss</th>
                        <th className="text-right">Shares</th>
                        <th>Substitute</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {harvestOpps.map((h, i) => (
                        <tr key={i}>
                          <td>
                            <span className="font-mono font-semibold text-gold-400">
                              {h.ticker}
                            </span>
                          </td>
                          <td className="text-slate-300">{h.name || "—"}</td>
                          <td className="text-right font-mono text-crimson-400">
                            -$
                            {Math.abs(
                              parseFloat(h.unrealized_loss || h.loss || 0),
                            ).toLocaleString()}
                          </td>
                          <td className="text-right font-mono">
                            {h.shares || h.quantity || "—"}
                          </td>
                          <td className="font-mono text-jade-500">
                            {h.substitute || "—"}
                          </td>
                          <td className="text-xs text-slate-500 max-w-xs truncate">
                            {h.notes || h.reason || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}

          {/* Gain/Loss */}
          {tab === "gainloss" && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <label className="label">Tax Year</label>
                <input
                  type="number"
                  className="input w-28"
                  value={taxYear}
                  onChange={(e) => setTaxYear(parseInt(e.target.value))}
                  onBlur={loadAll}
                  min={2020}
                  max={new Date().getFullYear()}
                />
              </div>
              {gainLoss?.transactions?.length > 0 ? (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Ticker</th>
                        <th>Type</th>
                        <th className="text-right">Proceeds</th>
                        <th className="text-right">Cost Basis</th>
                        <th className="text-right">G/L</th>
                        <th>Holding Period</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gainLoss.transactions.map((tx, i) => {
                        const gl = parseFloat(tx.realized_gain_loss || 0);
                        return (
                          <tr key={i}>
                            <td className="font-mono text-xs text-slate-400">
                              {tx.date || tx.transaction_date?.slice(0, 10)}
                            </td>
                            <td>
                              <span className="font-mono font-semibold text-gold-400">
                                {tx.ticker}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`badge ${tx.term === "long" ? "badge-jade" : "badge-gold"}`}
                              >
                                {tx.term || "short"}-term
                              </span>
                            </td>
                            <td className="text-right font-mono">
                              $
                              {parseFloat(
                                tx.proceeds || tx.amount || 0,
                              ).toLocaleString()}
                            </td>
                            <td className="text-right font-mono">
                              ${parseFloat(tx.cost_basis || 0).toLocaleString()}
                            </td>
                            <td
                              className={`text-right font-mono font-medium ${gl >= 0 ? "text-jade-500" : "text-crimson-400"}`}
                            >
                              {gl >= 0 ? "+" : "-"}$
                              {Math.abs(gl).toLocaleString()}
                            </td>
                            <td className="text-xs text-slate-500">
                              {tx.holding_period_days
                                ? `${tx.holding_period_days}d`
                                : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="card p-12">
                  <EmptyState
                    icon={Receipt}
                    title="No realized transactions"
                    description={`No sell transactions found for ${taxYear}.`}
                  />
                </div>
              )}
            </div>
          )}

          {/* Asset Location */}
          {tab === "location" &&
            (assetLocation ? (
              <div className="space-y-4">
                {assetLocation.recommendations?.map((rec, i) => (
                  <div key={i} className="card-hover p-5">
                    <div className="flex items-start gap-4">
                      <div className="w-8 h-8 rounded-lg bg-gold-500/10 flex items-center justify-center shrink-0">
                        <Building2 size={14} className="text-gold-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono font-semibold text-gold-400">
                            {rec.ticker}
                          </span>
                          <span className="badge-slate">
                            {rec.current_account || "—"}
                          </span>
                          {rec.recommended_account && (
                            <>
                              <span className="text-slate-600">→</span>
                              <span className="badge-jade">
                                {rec.recommended_account}
                              </span>
                            </>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {rec.reason || rec.rationale || "—"}
                        </p>
                        {rec.potential_tax_savings && (
                          <p className="text-xs text-jade-500 mt-1 font-medium">
                            Potential savings: $
                            {parseFloat(
                              rec.potential_tax_savings,
                            ).toLocaleString()}
                            /yr
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )) || (
                  <EmptyState
                    icon={Building2}
                    title="No location recommendations"
                    description="Asset location optimization data is not available."
                  />
                )}
              </div>
            ) : (
              <div className="card p-12">
                <EmptyState
                  icon={Building2}
                  title="Asset location analysis unavailable"
                />
              </div>
            ))}

          {/* Wash-Sale Check */}
          {tab === "washsale" && (
            <div className="space-y-5">
              <div className="card p-6">
                <SectionHeader
                  title="Wash-Sale Rule Checker"
                  subtitle="IRS 30-day buy/sell window compliance"
                />
                <form
                  onSubmit={checkWashSale}
                  className="flex items-end gap-4 flex-wrap"
                >
                  <div className="flex-1 min-w-[140px]">
                    <label className="label">Ticker</label>
                    <input
                      className="input font-mono"
                      placeholder="AAPL"
                      value={washForm.ticker}
                      onChange={(e) =>
                        setWashForm((f) => ({ ...f, ticker: e.target.value }))
                      }
                      required
                    />
                  </div>
                  <div className="flex-1 min-w-[160px]">
                    <label className="label">Proposed Sell Date</label>
                    <input
                      type="date"
                      className="input"
                      value={washForm.sell_date}
                      onChange={(e) =>
                        setWashForm((f) => ({
                          ...f,
                          sell_date: e.target.value,
                        }))
                      }
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary flex items-center gap-2"
                  >
                    {loading ? (
                      <Spinner size={14} className="text-obsidian-950" />
                    ) : (
                      <Search size={14} />
                    )}
                    Check
                  </button>
                </form>
              </div>

              {washSaleResult && (
                <div
                  className={`card p-6 ${washSaleResult.is_wash_sale ? "border-crimson-500/30" : "border-jade-500/30"}`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    {washSaleResult.is_wash_sale ? (
                      <AlertTriangle size={20} className="text-crimson-400" />
                    ) : (
                      <CheckCircle2 size={20} className="text-jade-500" />
                    )}
                    <h3
                      className={`font-semibold text-lg ${washSaleResult.is_wash_sale ? "text-crimson-400" : "text-jade-500"}`}
                    >
                      {washSaleResult.is_wash_sale
                        ? "Wash-Sale Violation Detected"
                        : "No Wash-Sale Violation"}
                    </h3>
                  </div>
                  <p className="text-sm text-slate-300 mb-4">
                    {washSaleResult.explanation || washSaleResult.detail}
                  </p>
                  {washSaleResult.conflicting_transactions?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                        Conflicting Transactions
                      </p>
                      {washSaleResult.conflicting_transactions.map((tx, i) => (
                        <div
                          key={i}
                          className="text-xs font-mono text-slate-400 py-1"
                        >
                          {tx.date}: {tx.type} {tx.quantity} shares @ $
                          {tx.price}
                        </div>
                      ))}
                    </div>
                  )}
                  {washSaleResult.safe_sell_date && (
                    <p className="text-sm text-jade-400 mt-3">
                      ✓ Earliest safe sell date:{" "}
                      <span className="font-mono font-semibold">
                        {washSaleResult.safe_sell_date}
                      </span>
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
