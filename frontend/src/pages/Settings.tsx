import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { HealthStatus } from "../types";

interface ImportPolicy {
  auto_import_enabled: boolean;
  confidence_threshold: number;
  duplicate_likely_threshold: number;
  duplicate_possible_threshold: number;
}

interface AISettings {
  ollama_base_url: string;
  ollama_model: string;
  embedding_model: string;
  max_upload_mb: number;
}

export default function Settings() {
  const [policy, setPolicy] = useState<ImportPolicy | null>(null);
  const [ai, setAi] = useState<AISettings | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [ollamaTest, setOllamaTest] = useState<string | null>(null);
  const [portalTest, setPortalTest] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function refresh() {
    api.get<ImportPolicy>("/settings/import-policy").then(setPolicy);
    api.get<AISettings>("/settings/ai").then(setAi);
    api.get<HealthStatus>("/health").then(setHealth);
  }

  useEffect(refresh, []);

  async function savePolicy() {
    if (!policy) return;
    setSaving(true);
    try {
      const updated = await api.put<ImportPolicy>("/settings/import-policy", policy);
      setPolicy(updated);
    } finally {
      setSaving(false);
    }
  }

  async function testOllama() {
    const result = await api.post<{ ok: boolean; message: string }>("/settings/test-ollama");
    setOllamaTest(result.message);
  }

  async function testPortal() {
    const result = await api.post<{ ok: boolean; message: string }>("/settings/test-portal");
    setPortalTest(result.message);
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>AI, import policy, and integration configuration (Admin only).</p>
        </div>
      </div>

      <div className="card">
        <h2>System Health</h2>
        {health && (
          <table>
            <tbody>
              <tr>
                <td>Database</td>
                <td>{health.database ? "OK" : "Unavailable"}</td>
              </tr>
              <tr>
                <td>Ollama (Local LLM)</td>
                <td>{health.ollama_message}</td>
              </tr>
              <tr>
                <td>Embedding Model</td>
                <td>{health.embedding_message}</td>
              </tr>
              <tr>
                <td>Portal Import Gateway</td>
                <td>{health.portal_message}</td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {policy && (
        <div className="card">
          <h2>Import Policy</h2>
          <div className="form-grid">
            <div className="form-field">
              <label>
                <input
                  type="checkbox"
                  checked={policy.auto_import_enabled}
                  onChange={(e) => setPolicy({ ...policy, auto_import_enabled: e.target.checked })}
                  style={{ width: "auto", marginRight: 6 }}
                />
                Enable AUTO_IMPORT_HIGH_CONFIDENCE
              </label>
            </div>
            <div className="form-field">
              <label>Confidence Threshold ({Math.round(policy.confidence_threshold * 100)}%)</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={policy.confidence_threshold}
                onChange={(e) => setPolicy({ ...policy, confidence_threshold: Number(e.target.value) })}
              />
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <button className="btn btn-primary" onClick={savePolicy} disabled={saving}>
              Save Policy
            </button>
          </div>
        </div>
      )}

      {ai && (
        <div className="card">
          <h2>AI Configuration</h2>
          <table>
            <tbody>
              <tr>
                <td>Ollama URL</td>
                <td>{ai.ollama_base_url}</td>
              </tr>
              <tr>
                <td>LLM Model</td>
                <td>{ai.ollama_model}</td>
              </tr>
              <tr>
                <td>Embedding Model</td>
                <td>{ai.embedding_model}</td>
              </tr>
              <tr>
                <td>Max Upload Size</td>
                <td>{ai.max_upload_mb} MB</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>Connections</h2>
        <div className="btn-row">
          <button className="btn" onClick={testOllama}>
            Test Ollama Connection
          </button>
          <button className="btn" onClick={testPortal}>
            Test Portal Connection
          </button>
        </div>
        {ollamaTest && <p style={{ marginTop: 10 }}>Ollama: {ollamaTest}</p>}
        {portalTest && <p>Portal: {portalTest}</p>}
      </div>
    </div>
  );
}
