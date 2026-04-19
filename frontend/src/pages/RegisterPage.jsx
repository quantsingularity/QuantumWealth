import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { auth } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { Alert } from "../components/ui";

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    password2: "",
    phone_number: "",
    country: "US",
    currency: "USD",
  });
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleNext = (e) => {
    e.preventDefault();
    if (!form.email || !form.full_name) return;
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    if (form.password !== form.password2) {
      setFieldErrors({ password2: "Passwords do not match." });
      return;
    }
    setLoading(true);
    try {
      await auth.register(form);
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      const d = err.data || {};
      if (typeof d === "object" && !d.detail) setFieldErrors(d);
      else setError(d.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-950 flex items-center justify-center p-6">
      <div className="w-full max-w-md animate-slide-up">
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center shadow-gold">
            <Activity size={18} className="text-obsidian-950" />
          </div>
          <span className="font-display font-semibold text-xl text-slate-100">
            QuantumWealth
          </span>
        </div>

        <div className="card p-8">
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              {[1, 2].map((n) => (
                <div
                  key={n}
                  className={`flex items-center gap-2 ${n < 2 ? "flex-1" : ""}`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold border transition-all
                    ${step >= n ? "bg-gold-500 border-gold-500 text-obsidian-950" : "border-obsidian-500 text-slate-600"}`}
                  >
                    {n}
                  </div>
                  {n < 2 && (
                    <div
                      className={`flex-1 h-0.5 transition-all ${step > n ? "bg-gold-500" : "bg-obsidian-600"}`}
                    />
                  )}
                </div>
              ))}
            </div>
            <h1 className="font-display text-2xl font-semibold text-slate-100">
              {step === 1 ? "Create your account" : "Set your password"}
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              {step === 1
                ? "Start with your basic information."
                : "Choose a strong password to secure your account."}
            </p>
          </div>

          {error && (
            <div className="mb-4">
              <Alert
                type="error"
                message={error}
                onClose={() => setError("")}
              />
            </div>
          )}

          {step === 1 && (
            <form onSubmit={handleNext} className="space-y-4">
              <div>
                <label className="label">Full Name</label>
                <input
                  className="input"
                  placeholder="Jane Smith"
                  value={form.full_name}
                  onChange={(e) => set("full_name", e.target.value)}
                  required
                />
                {fieldErrors.full_name && (
                  <p className="text-xs text-crimson-400 mt-1">
                    {fieldErrors.full_name}
                  </p>
                )}
              </div>
              <div>
                <label className="label">Email Address</label>
                <input
                  type="email"
                  className="input"
                  placeholder="jane@example.com"
                  value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  required
                />
                {fieldErrors.email && (
                  <p className="text-xs text-crimson-400 mt-1">
                    {fieldErrors.email}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Country</label>
                  <select
                    className="select"
                    value={form.country}
                    onChange={(e) => set("country", e.target.value)}
                  >
                    <option value="US">United States</option>
                    <option value="GB">United Kingdom</option>
                    <option value="CA">Canada</option>
                    <option value="AU">Australia</option>
                    <option value="SG">Singapore</option>
                  </select>
                </div>
                <div>
                  <label className="label">Currency</label>
                  <select
                    className="select"
                    value={form.currency}
                    onChange={(e) => set("currency", e.target.value)}
                  >
                    <option value="USD">USD</option>
                    <option value="GBP">GBP</option>
                    <option value="EUR">EUR</option>
                    <option value="CAD">CAD</option>
                    <option value="AUD">AUD</option>
                  </select>
                </div>
              </div>
              <button
                type="submit"
                className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
              >
                Continue <ArrowRight size={15} />
              </button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Password</label>
                <div className="relative">
                  <input
                    type={showPass ? "text" : "password"}
                    className="input pr-10"
                    placeholder="Min. 8 characters"
                    value={form.password}
                    onChange={(e) => set("password", e.target.value)}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-crimson-400 mt-1">
                    {fieldErrors.password}
                  </p>
                )}
              </div>
              <div>
                <label className="label">Confirm Password</label>
                <input
                  type="password"
                  className="input"
                  placeholder="Repeat password"
                  value={form.password2}
                  onChange={(e) => set("password2", e.target.value)}
                  required
                />
                {fieldErrors.password2 && (
                  <p className="text-xs text-crimson-400 mt-1">
                    {fieldErrors.password2}
                  </p>
                )}
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="btn-secondary flex-1"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <>
                      <span>Create Account</span>
                      <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          <p className="text-center text-sm text-slate-500 mt-6">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-gold-400 hover:text-gold-300 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-xs text-slate-700 mt-6">
          By registering, you acknowledge this platform is for informational
          purposes only.
        </p>
      </div>
    </div>
  );
}
