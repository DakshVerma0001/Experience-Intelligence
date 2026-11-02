import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../services/api";
import type { ImportBatch } from "../types";
import Badge from "../components/Badge";

const ACTIVE_STATES = new Set(["UPLOADED", "PROCESSING"]);

export default function ImportHistory() {
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [stoppingId, setStoppingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    return api.get<ImportBatch[]>("/imports/batches").then(setBatches);
  }

  useEffect(() => {
    load().finally(() => setLoading(false));
    const interval = setInterval(() => {
      load().catch(() => undefined);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  async function stopBatch(batch: ImportBatch) {
    if (!window.confirm(`Stop processing batch #${String(batch.batch_number).padStart(5, "0")}? Projects already processed are kept as-is.`)) {
      return;
    }
    setError(null);
    setStoppingId(batch.id);
    try {
      const updated = await api.post<ImportBatch>(`/imports/batches/${batch.id}/stop`);
      setBatches((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to stop processing");
    } finally {
      setStoppingId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Import History</h1>
          <p>Every uploaded document and its processing outcome.</p>
        </div>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        {loading && <p>Loading...</p>}
        {!loading && batches.length === 0 && <div className="empty-state">No import batches yet.</div>}
        {batches.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Status</th>
                <th>Projects</th>
                <th>Imported</th>
                <th>Review Required</th>
                <th>Duplicates</th>
                <th>Failed</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => {
                const active = ACTIVE_STATES.has(b.status);
                return (
                  <tr key={b.id}>
                    <td>
                      <Link to={`/imports/${b.id}`}>#{String(b.batch_number).padStart(5, "0")}</Link>
                    </td>
                    <td>
                      <Badge text={b.status} />
                      {b.cancel_requested && active && " (stopping...)"}
                    </td>
                    <td>{b.projects_detected}</td>
                    <td>{b.projects_auto_imported}</td>
                    <td>{b.projects_review_required}</td>
                    <td>{b.projects_duplicate}</td>
                    <td>{b.projects_failed}</td>
                    <td>{new Date(b.created_at).toLocaleString()}</td>
                    <td>
                      {active && (
                        <button
                          className="btn btn-danger"
                          disabled={b.cancel_requested || stoppingId === b.id}
                          onClick={() => stopBatch(b)}
                        >
                          {b.cancel_requested ? "Stopping..." : "Stop"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
