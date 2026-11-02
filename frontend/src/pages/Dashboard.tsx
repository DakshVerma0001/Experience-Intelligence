import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { ImportBatch } from "../types";
import Badge from "../components/Badge";

export default function Dashboard() {
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<ImportBatch[]>("/imports/batches")
      .then(setBatches)
      .finally(() => setLoading(false));
  }, []);

  const totals = batches.reduce(
    (acc, b) => {
      acc.detected += b.projects_detected;
      acc.imported += b.projects_auto_imported;
      acc.review += b.projects_review_required;
      acc.duplicates += b.projects_duplicate;
      acc.failed += b.projects_failed;
      return acc;
    },
    { detected: 0, imported: 0, review: 0, duplicates: 0, failed: 0 }
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview of AI-driven experience import activity.</p>
        </div>
        <Link className="btn btn-primary" to="/import">
          + Import Experience
        </Link>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{totals.detected}</div>
          <div className="stat-label">Total Projects Processed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totals.imported}</div>
          <div className="stat-label">Total Projects Imported</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totals.review}</div>
          <div className="stat-label">Requiring Review</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totals.duplicates}</div>
          <div className="stat-label">Potential Duplicates</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totals.failed}</div>
          <div className="stat-label">Failed Imports</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{batches.length}</div>
          <div className="stat-label">Documents Processed</div>
        </div>
      </div>

      <div className="card">
        <h2>Recent Import Batches</h2>
        {loading && <p>Loading...</p>}
        {!loading && batches.length === 0 && (
          <div className="empty-state">No import batches yet. Upload a document to get started.</div>
        )}
        {batches.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Batch</th>
                <th>Status</th>
                <th>Detected</th>
                <th>Imported</th>
                <th>Review</th>
                <th>Duplicates</th>
                <th>Failed</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {batches.slice(0, 10).map((b) => (
                <tr key={b.id}>
                  <td>
                    <Link to={`/imports/${b.id}`}>#{String(b.batch_number).padStart(5, "0")}</Link>
                  </td>
                  <td>
                    <Badge text={b.status} />
                  </td>
                  <td>{b.projects_detected}</td>
                  <td>{b.projects_auto_imported}</td>
                  <td>{b.projects_review_required}</td>
                  <td>{b.projects_duplicate}</td>
                  <td>{b.projects_failed}</td>
                  <td>{new Date(b.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
