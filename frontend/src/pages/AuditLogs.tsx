import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { AuditLogEntry } from "../types";

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<AuditLogEntry[]>("/audit/logs")
      .then(setLogs)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Audit Logs</h1>
          <p>Complete audit trail of imports, approvals, rejections, and production imports.</p>
        </div>
      </div>
      <div className="card">
        {loading && <p>Loading...</p>}
        {!loading && logs.length === 0 && <div className="empty-state">No audit records yet.</div>}
        {logs.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Batch</th>
                <th>Project</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td>{new Date(l.created_at).toLocaleString()}</td>
                  <td>{l.action}</td>
                  <td>{l.actor_label || "System"}</td>
                  <td>{l.import_batch_id ? l.import_batch_id.slice(0, 8) : "-"}</td>
                  <td>{l.project_id ? l.project_id.slice(0, 8) : "-"}</td>
                  <td>{l.result || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
