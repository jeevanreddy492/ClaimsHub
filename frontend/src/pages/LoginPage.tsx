import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Alert, Field, errorText } from "../components/ui";

export default function LoginPage() {
  const { session, login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [username, setUsername] = useState("adjuster1");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <div className="brand big">
          <img src="/favicon.svg" alt="" width={36} height={36} />
          <span>ClaimsHub</span>
        </div>
        <p className="muted">Claims for Short-Term Disability, Life and employee leave.</p>
        <Alert>{error}</Alert>
        <Field label="Username">
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </Field>
        <Field label="Password">
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </Field>
        <button className="btn btn-primary full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="muted small">Demo users: adjuster1, supervisor1, viewer1. All data is fake.</p>
      </form>
    </div>
  );
}
