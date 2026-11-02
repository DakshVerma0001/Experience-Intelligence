import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../services/api";
import { setSession } from "../services/auth";

interface LoginResponse {
  access_token: string;
  role: "CONTRIBUTOR" | "REVIEWER" | "ADMIN";
  full_name: string;
  email: string;
}

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.post<LoginResponse>("/auth/login", { email, password });
      setSession(data.access_token, { email: data.email, full_name: data.full_name, role: data.role });
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Experience Intelligence</h1>
        <p className="subtitle">Sign in with your Experience Intelligence account (not your Knowledge Repository portal password).</p>
        {error && <div className="error-banner">{error}</div>}
        <div className="field-group">
          <label>Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field-group">
          <label>Password</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
        <p style={{ fontSize: 12, color: "#667085", marginTop: 16 }}>
          Default admin: admin@experience-intelligence.example / ChangeMe123!
        </p>
      </form>
    </div>
  );
}
