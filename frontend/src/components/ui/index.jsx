import { useState } from "react";
import {
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  Info,
  X,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

// ── Stat Card ──────────────────────────────────────────────────────────────────
export function StatCard({
  label,
  value,
  change,
  changeLabel,
  icon: Icon,
  accent = "gold",
  prefix = "",
  suffix = "",
}) {
  const isPositive = typeof change === "number" ? change >= 0 : null;
  return (
    <div className="card p-5 relative overflow-hidden group hover:border-obsidian-500 transition-all duration-200">
      <div
        className={clsx(
          "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300",
          accent === "gold" &&
            "bg-gradient-radial from-gold-500/5 via-transparent to-transparent",
          accent === "jade" &&
            "bg-gradient-radial from-jade-500/5 via-transparent to-transparent",
        )}
      />
      <div className="relative">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            {label}
          </span>
          {Icon && (
            <div
              className={clsx(
                "w-8 h-8 rounded-lg flex items-center justify-center",
                accent === "gold" && "bg-gold-500/10 text-gold-500",
                accent === "jade" && "bg-jade-500/10 text-jade-500",
                accent === "crimson" && "bg-crimson-500/10 text-crimson-400",
                accent === "slate" && "bg-obsidian-700 text-slate-400",
              )}
            >
              <Icon size={16} />
            </div>
          )}
        </div>
        <div className="flex items-end justify-between">
          <p className="text-2xl font-semibold text-slate-100 font-mono tracking-tight">
            {prefix}
            {typeof value === "number"
              ? value.toLocaleString("en-US", { maximumFractionDigits: 2 })
              : value}
            {suffix}
          </p>
          {change !== undefined && isPositive !== null && (
            <span
              className={clsx(
                "text-xs font-medium font-mono",
                isPositive ? "text-jade-500" : "text-crimson-400",
              )}
            >
              {isPositive ? "+" : ""}
              {typeof change === "number" ? change.toFixed(2) : change}
              {changeLabel}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Section Header ─────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
        <div className="accent-line mt-2" />
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ── Modal ──────────────────────────────────────────────────────────────────────
export function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = "max-w-lg",
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={clsx(
          "relative w-full bg-obsidian-800 rounded-2xl border border-obsidian-600 shadow-2xl animate-slide-up",
          maxWidth,
        )}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-obsidian-700">
          <h3 className="font-display font-semibold text-slate-100 text-lg">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ── Alert ──────────────────────────────────────────────────────────────────────
export function Alert({ type = "info", message, onClose }) {
  const config = {
    error: {
      icon: AlertCircle,
      cls: "bg-crimson-500/10 border-crimson-500/30 text-crimson-400",
    },
    success: {
      icon: CheckCircle2,
      cls: "bg-jade-500/10 border-jade-500/30 text-jade-500",
    },
    info: {
      icon: Info,
      cls: "bg-gold-500/10 border-gold-500/30 text-gold-400",
    },
  };
  const { icon: Icon, cls } = config[type] || config.info;
  return (
    <div
      className={clsx(
        "flex items-start gap-3 px-4 py-3 rounded-lg border text-sm",
        cls,
      )}
    >
      <Icon size={16} className="shrink-0 mt-0.5" />
      <span className="flex-1">{message}</span>
      {onClose && (
        <button onClick={onClose} className="opacity-70 hover:opacity-100">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ── Badge ──────────────────────────────────────────────────────────────────────
export function Badge({ children, variant = "slate" }) {
  return <span className={`badge-${variant}`}>{children}</span>;
}

// ── Loading Spinner ────────────────────────────────────────────────────────────
export function Spinner({ size = 20, className = "" }) {
  return (
    <Loader2
      size={size}
      className={clsx("animate-spin text-gold-500", className)}
    />
  );
}

// ── Empty State ────────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-obsidian-800 border border-obsidian-600 flex items-center justify-center mb-4">
          <Icon size={28} className="text-slate-600" />
        </div>
      )}
      <h3 className="text-base font-semibold text-slate-300 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-slate-500 max-w-xs">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

// ── Select ─────────────────────────────────────────────────────────────────────
export function Select({
  label: lbl,
  value,
  onChange,
  options,
  className = "",
}) {
  return (
    <div className={className}>
      {lbl && <label className="label">{lbl}</label>}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="select pr-8"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={14}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
        />
      </div>
    </div>
  );
}

// ── Tab Bar ────────────────────────────────────────────────────────────────────
export function TabBar({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 p-1 bg-obsidian-950 rounded-xl border border-obsidian-700 w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={clsx(
            "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
            active === tab.value
              ? "bg-gold-500/15 text-gold-400 border border-gold-500/25 shadow-sm"
              : "text-slate-500 hover:text-slate-300 hover:bg-obsidian-800",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ── Form Field ─────────────────────────────────────────────────────────────────
export function FormField({ label: lbl, error, children }) {
  return (
    <div>
      {lbl && <label className="label">{lbl}</label>}
      {children}
      {error && <p className="text-xs text-crimson-400 mt-1">{error}</p>}
    </div>
  );
}

// ── Metric Row ─────────────────────────────────────────────────────────────────
export function MetricRow({ label, value, highlight = false }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-obsidian-700/50 last:border-b-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span
        className={clsx(
          "text-sm font-mono font-medium",
          highlight ? "text-gold-400" : "text-slate-200",
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ── Gauge ──────────────────────────────────────────────────────────────────────
export function RiskGauge({ score, profile }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct < 30 ? "#3dffc8" : pct < 60 ? "#e8b320" : "#ff4459";
  const deg = -135 + (pct / 100) * 270;

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 140 100" className="w-40">
        <path
          d="M 20 90 A 60 60 0 1 1 120 90"
          fill="none"
          stroke="#1a2840"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M 20 90 A 60 60 0 1 1 120 90"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * 188.5} 188.5`}
        />
        <line
          x1="70"
          y1="90"
          x2={70 + 40 * Math.cos((deg * Math.PI) / 180)}
          y2={90 + 40 * Math.sin((deg * Math.PI) / 180)}
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="70" cy="90" r="4" fill={color} />
        <text
          x="70"
          y="72"
          textAnchor="middle"
          fill={color}
          fontSize="20"
          fontFamily="JetBrains Mono"
          fontWeight="600"
        >
          {score}
        </text>
      </svg>
      <span className="text-xs font-medium text-slate-400 capitalize mt-1">
        {profile?.replace("_", " ")}
      </span>
    </div>
  );
}
