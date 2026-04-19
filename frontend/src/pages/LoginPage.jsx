import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, Eye, EyeOff, ArrowRight, Lock, Mail } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Alert, Spinner } from "../components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(
        err.data?.detail ||
          err.data?.non_field_errors?.[0] ||
          "Invalid credentials.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-950 flex">
      {/* Left — branding */}
      <div className="hidden lg:flex flex-1 flex-col justify-between p-12 bg-gradient-to-br from-obsidian-950 via-obsidian-900 to-obsidian-800 border-r border-obsidian-700 relative overflow-hidden">
        {/* Decorative grid */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(#e8b320 1px, transparent 1px), linear-gradient(90deg, #e8b320 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        {/* Radial glow */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-gold-500/5 blur-3xl" />

        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center shadow-gold">
              <Activity
                size={20}
                className="text-obsidian-950"
                strokeWidth={2.5}
              />
            </div>
            <span className="font-display font-semibold text-xl text-slate-100">
              QuantumWealth
            </span>
          </div>
        </div>

        <div className="relative space-y-6">
          <div className="accent-line w-12" />
          <h2 className="font-display text-4xl font-semibold text-slate-100 leading-tight">
            Institutional-grade
            <br />
            <span className="gradient-text-gold">wealth intelligence</span>
            <br />
            for every investor.
          </h2>
          <p className="text-slate-500 text-base leading-relaxed max-w-sm">
            AI-powered portfolio optimization, real-time risk analytics, and
            automated tax-loss harvesting — all in one platform.
          </p>

          <div className="grid grid-cols-3 gap-4 pt-4">
            {[
              { label: "Optimization Strategies", value: "4" },
              { label: "Risk Models", value: "8+" },
              { label: "Tax Scenarios", value: "6" },
            ].map((s) => (
              <div
                key={s.label}
                className="p-4 rounded-xl bg-obsidian-800/60 border border-obsidian-600"
              >
                <p className="font-mono text-2xl font-semibold text-gold-400">
                  {s.value}
                </p>
                <p className="text-xs text-slate-500 mt-1 leading-tight">
                  {s.label}
                </p>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-slate-700">
          © {new Date().getFullYear()} QuantumWealth. For informational purposes
          only.
        </p>
      </div>

      {/* Right — form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md animate-slide-up">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center">
              <Activity size={16} className="text-obsidian-950" />
            </div>
            <span className="font-display font-semibold text-slate-100">
              QuantumWealth
            </span>
          </div>

          <div className="mb-8">
            <h1 className="font-display text-3xl font-semibold text-slate-100 mb-2">
              Sign in
            </h1>
            <p className="text-slate-500 text-sm">
              Access your wealth management platform.
            </p>
          </div>

          {error && (
            <div className="mb-5">
              <Alert
                type="error"
                message={error}
                onClose={() => setError("")}
              />
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email Address</label>
              <div className="relative">
                <Mail
                  size={15}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  type="email"
                  className="input pl-10"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, email: e.target.value }))
                  }
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock
                  size={15}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  type={showPass ? "text" : "password"}
                  className="input pl-10 pr-10"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, password: e.target.value }))
                  }
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <Spinner size={16} className="text-obsidian-950" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-gold-400 hover:text-gold-300 font-medium transition-colors"
            >
              Create one
            </Link>
          </p>

          {/* Demo note */}
          <div className="mt-8 p-4 rounded-xl bg-obsidian-800/50 border border-obsidian-600">
            <p className="text-xs text-slate-500 text-center">
              <span className="text-gold-500 font-medium">Demo:</span> Run{" "}
              <code className="font-mono text-slate-400">
                python manage.py seed_demo_data
              </code>{" "}
              to generate test credentials.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
