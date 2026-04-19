import { useState, useEffect } from "react";
import {
  User,
  Lock,
  Bell,
  ClipboardList,
  CheckCircle2,
  ChevronRight,
  Save,
} from "lucide-react";
import { auth } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import {
  SectionHeader,
  Alert,
  Spinner,
  TabBar,
  RiskGauge,
} from "../components/ui";

const RISK_QUESTIONS = [
  {
    id: 1,
    text: "How would you describe your investment experience?",
    answers: [
      "No experience",
      "Limited experience",
      "Moderate experience",
      "Significant experience",
      "Expert investor",
    ],
  },
  {
    id: 2,
    text: "What is your primary investment objective?",
    answers: [
      "Capital preservation",
      "Income generation",
      "Balanced growth",
      "Long-term growth",
      "Maximum growth",
    ],
  },
  {
    id: 3,
    text: "What is your investment time horizon?",
    answers: [
      "Less than 1 year",
      "1-3 years",
      "3-5 years",
      "5-10 years",
      "More than 10 years",
    ],
  },
  {
    id: 4,
    text: "If your portfolio dropped 20% in one month, you would:",
    answers: [
      "Sell everything",
      "Sell some holdings",
      "Hold and wait",
      "Buy a little more",
      "Significantly increase position",
    ],
  },
  {
    id: 5,
    text: "What percentage of your monthly income can you invest?",
    answers: ["Less than 5%", "5-10%", "10-20%", "20-30%", "More than 30%"],
  },
  {
    id: 6,
    text: "What is your current employment status?",
    answers: [
      "Unemployed",
      "Part-time employed",
      "Fully employed",
      "Self-employed",
      "Retired with pension",
    ],
  },
  {
    id: 7,
    text: "Do you have an emergency fund covering 6+ months of expenses?",
    answers: [
      "No emergency fund",
      "Less than 1 month",
      "1-3 months",
      "3-6 months",
      "More than 6 months",
    ],
  },
  {
    id: 8,
    text: "How important is liquidity to your portfolio?",
    answers: [
      "Very important",
      "Important",
      "Neutral",
      "Not very important",
      "Not important",
    ],
  },
  {
    id: 9,
    text: "What is your annual household income range?",
    answers: [
      "Under $30k",
      "$30k-$60k",
      "$60k-$100k",
      "$100k-$200k",
      "Over $200k",
    ],
  },
  {
    id: 10,
    text: "How do you feel about taking risks to potentially earn higher returns?",
    answers: [
      "Very uncomfortable",
      "Somewhat uncomfortable",
      "Neutral",
      "Comfortable",
      "Very comfortable",
    ],
  },
];

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState({
    full_name: "",
    phone_number: "",
    country: "US",
    currency: "USD",
  });
  const [passwords, setPasswords] = useState({
    old_password: "",
    new_password: "",
    new_password2: "",
  });
  const [notifications, setNotifications] = useState([]);
  const [answers, setAnswers] = useState({});
  const [riskResult, setRiskResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) {
      setProfile({
        full_name: user.full_name || "",
        phone_number: user.phone_number || "",
        country: user.country || "US",
        currency: user.currency || "USD",
      });
    }
    auth
      .notifications()
      .then((d) => setNotifications(d?.results || d || []))
      .catch(() => {});
  }, [user]);

  const saveProfile = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const updated = await auth.updateMe(profile);
      setUser((u) => ({ ...u, ...updated }));
      setSuccess("Profile updated successfully.");
    } catch (err) {
      setError(err.data?.detail || "Failed to update profile.");
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    if (passwords.new_password !== passwords.new_password2) {
      setError("New passwords do not match.");
      setLoading(false);
      return;
    }
    try {
      await auth.changePassword({
        old_password: passwords.old_password,
        new_password: passwords.new_password,
        new_password2: passwords.new_password2,
      });
      setSuccess("Password changed successfully.");
      setPasswords({ old_password: "", new_password: "", new_password2: "" });
    } catch (err) {
      setError(
        err.data?.old_password?.[0] ||
          err.data?.detail ||
          "Failed to change password.",
      );
    } finally {
      setLoading(false);
    }
  };

  const submitQuestionnaire = async () => {
    const answerArr = RISK_QUESTIONS.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] || 3,
    }));
    setLoading(true);
    setError("");
    try {
      const res = await auth.riskQuestionnaire(answerArr);
      setRiskResult(res);
      setUser((u) => ({
        ...u,
        risk_score: res.risk_score,
        risk_profile: res.risk_profile,
      }));
      setSuccess("Risk profile updated!");
    } catch (err) {
      setError(err.data?.detail || "Failed to submit questionnaire.");
    } finally {
      setLoading(false);
    }
  };

  const markAllRead = async () => {
    await auth.markAllRead();
    setNotifications((ns) => ns.map((n) => ({ ...n, is_read: true })));
  };

  const initials =
    user?.full_name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "QW";

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="section-title text-3xl">Settings</h1>
        <p className="text-slate-500 text-sm mt-1">
          Manage your account, preferences, and risk profile.
        </p>
        <div className="accent-line mt-2" />
      </div>

      {/* User card */}
      <div className="card p-5 flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-gold-500/30 to-gold-600/10 border border-gold-500/30 flex items-center justify-center">
          <span className="font-display text-xl font-semibold text-gold-400">
            {initials}
          </span>
        </div>
        <div>
          <h2 className="font-semibold text-slate-100">{user?.full_name}</h2>
          <p className="text-sm text-slate-500">{user?.email}</p>
          <div className="flex items-center gap-2 mt-1">
            {user?.risk_profile && (
              <span className="badge-gold capitalize">
                {user.risk_profile?.replace("_", " ")}
              </span>
            )}
            {user?.is_email_verified && (
              <span className="badge-jade">
                <CheckCircle2 size={10} /> Verified
              </span>
            )}
          </div>
        </div>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError("")} />
      )}
      {success && (
        <Alert
          type="success"
          message={success}
          onClose={() => setSuccess("")}
        />
      )}

      <TabBar
        tabs={[
          { label: "Profile", value: "profile" },
          { label: "Password", value: "password" },
          { label: "Risk Profile", value: "risk" },
          { label: "Notifications", value: "notifications" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {/* Profile */}
      {tab === "profile" && (
        <div className="card p-6 max-w-lg">
          <SectionHeader title="Personal Information" />
          <form onSubmit={saveProfile} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <input
                className="input"
                value={profile.full_name}
                onChange={(e) =>
                  setProfile((p) => ({ ...p, full_name: e.target.value }))
                }
                required
              />
            </div>
            <div>
              <label className="label">Phone Number</label>
              <input
                className="input"
                placeholder="+1234567890"
                value={profile.phone_number}
                onChange={(e) =>
                  setProfile((p) => ({ ...p, phone_number: e.target.value }))
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Country</label>
                <select
                  className="select"
                  value={profile.country}
                  onChange={(e) =>
                    setProfile((p) => ({ ...p, country: e.target.value }))
                  }
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
                  value={profile.currency}
                  onChange={(e) =>
                    setProfile((p) => ({ ...p, currency: e.target.value }))
                  }
                >
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                  <option value="CAD">CAD</option>
                </select>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? (
                <Spinner size={14} className="text-obsidian-950" />
              ) : (
                <Save size={14} />
              )}{" "}
              Save Changes
            </button>
          </form>
        </div>
      )}

      {/* Password */}
      {tab === "password" && (
        <div className="card p-6 max-w-lg">
          <SectionHeader title="Change Password" />
          <form onSubmit={changePassword} className="space-y-4">
            {["old_password", "new_password", "new_password2"].map(
              (field, i) => (
                <div key={field}>
                  <label className="label">
                    {
                      [
                        "Current Password",
                        "New Password",
                        "Confirm New Password",
                      ][i]
                    }
                  </label>
                  <input
                    type="password"
                    className="input"
                    value={passwords[field]}
                    onChange={(e) =>
                      setPasswords((p) => ({ ...p, [field]: e.target.value }))
                    }
                    required
                    minLength={field !== "old_password" ? 8 : undefined}
                  />
                </div>
              ),
            )}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? (
                <Spinner size={14} className="text-obsidian-950" />
              ) : (
                <Lock size={14} />
              )}{" "}
              Update Password
            </button>
          </form>
        </div>
      )}

      {/* Risk Questionnaire */}
      {tab === "risk" && (
        <div className="space-y-5">
          <div className="card p-6">
            <SectionHeader
              title="Risk Tolerance Questionnaire"
              subtitle="Answer all 10 questions to calibrate your investment profile"
            />

            {user?.risk_score && !riskResult && (
              <div className="flex items-center gap-6 mb-6 p-4 rounded-xl bg-obsidian-900 border border-obsidian-700">
                <RiskGauge
                  score={user.risk_score}
                  profile={user.risk_profile}
                />
                <div>
                  <p className="text-sm font-semibold text-slate-200 mb-1">
                    Current Profile
                  </p>
                  <p className="text-xs text-slate-500 capitalize">
                    {user.risk_profile?.replace("_", " ")}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Score: {user.risk_score}/100
                  </p>
                </div>
              </div>
            )}

            {riskResult && (
              <div className="flex items-center gap-6 mb-6 p-4 rounded-xl bg-jade-500/5 border border-jade-500/20">
                <RiskGauge
                  score={riskResult.risk_score}
                  profile={riskResult.risk_profile}
                />
                <div>
                  <p className="text-sm font-semibold text-jade-500 mb-1">
                    ✓ Profile Updated
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed max-w-xs">
                    {riskResult.description}
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-6">
              {RISK_QUESTIONS.map((q) => (
                <div key={q.id}>
                  <p className="text-sm text-slate-300 font-medium mb-3">
                    <span className="font-mono text-gold-500 mr-2">
                      {q.id}.
                    </span>
                    {q.text}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                    {q.answers.map((a, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() =>
                          setAnswers((prev) => ({ ...prev, [q.id]: idx + 1 }))
                        }
                        className={`p-2.5 rounded-lg text-xs text-center border transition-all leading-tight
                          ${
                            answers[q.id] === idx + 1
                              ? "bg-gold-500/15 border-gold-500/40 text-gold-400"
                              : "bg-obsidian-900 border-obsidian-600 text-slate-500 hover:border-obsidian-500 hover:text-slate-300"
                          }`}
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between mt-8 pt-6 border-t border-obsidian-700">
              <p className="text-xs text-slate-500">
                {Object.keys(answers).length}/10 questions answered
              </p>
              <button
                onClick={submitQuestionnaire}
                disabled={loading || Object.keys(answers).length < 10}
                className="btn-primary flex items-center gap-2"
              >
                {loading ? (
                  <Spinner size={14} className="text-obsidian-950" />
                ) : (
                  <ClipboardList size={14} />
                )}
                Submit Assessment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Notifications */}
      {tab === "notifications" && (
        <div className="card p-6">
          <SectionHeader
            title="Notifications"
            actions={
              <button onClick={markAllRead} className="btn-ghost text-xs">
                Mark All Read
              </button>
            }
          />
          {notifications.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-8">
              No notifications yet.
            </p>
          ) : (
            <div className="space-y-2">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={`p-4 rounded-xl border transition-all ${n.is_read ? "bg-obsidian-900 border-obsidian-700" : "bg-gold-500/5 border-gold-500/20"}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p
                        className={`text-sm font-medium ${n.is_read ? "text-slate-400" : "text-slate-200"}`}
                      >
                        {n.title || n.message}
                      </p>
                      {n.body && (
                        <p className="text-xs text-slate-500 mt-1">{n.body}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      {!n.is_read && (
                        <div className="w-2 h-2 rounded-full bg-gold-400 mb-1 ml-auto" />
                      )}
                      <p className="text-[10px] font-mono text-slate-600">
                        {n.created_at?.slice(0, 10)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
