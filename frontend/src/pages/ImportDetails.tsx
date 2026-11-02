import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../services/api";
import type { ImportBatch, ProcessingProgress, ProjectSummary } from "../types";
import Badge from "../components/Badge";
import { hasRole } from "../services/auth";

const ACTIVE_STATES = new Set(["UPLOADED", "PROCESSING"]);

export default function ImportDetails() {
  const { batchId } = useParams<{ batchId: string }>();
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);

  async function refresh() {
    if (!batchId) return;
    const [b, p, projs] = await Promise.all([
      api.get<ImportBatch>(`/imports/batches/${batchId}`),
      api.get<ProcessingProgress>(`/imports/batches/${batchId}/progress`),
      api.get<ProjectSummary[]>(`/imports/batches/${batchId}/projects`),
    ]);
    setBatch(b);
    setProgress(p);
    setProjects(projs);
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(() => {
      refresh();
    }, 2000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  async function approveAllValid() {
    if (!batchId) return;
    setBulkMessage(null);
    const result = await api.post<{
      approved_count: number;
      imported_count: number;
      skipped_review_required: number;
      skipped_duplicate: number;
    }>(`/review/batches/${batchId}/approve-all-valid`);
    setBulkMessage(
      `Approved & imported ${result.imported_count} of ${result.approved_count} ready projects. ` +
        `${result.skipped_review_required} still require review, ${result.skipped_duplicate} flagged as duplicates.`
    );
    refresh();
  }

  async function stopProcessing() {
    if (!batchId) return;
    if (!window.confirm("Stop processing this batch? Projects already processed are kept as-is; remaining documents/projects will not be started.")) {
      return;
    }
    setStopping(true);
    setStopError(null);
    try {
      const updated = await api.post<ImportBatch>(`/imports/batches/${batchId}/stop`);
      setBatch(updated);
    } catch (err) {
      setStopError(err instanceof ApiError ? err.message : "Failed to stop processing");
    } finally {
      setStopping(false);
    }
  }

  if (!batch || !progress) {
    return <p>Loading...</p>;
  }

  const isActive = ACTIVE_STATES.has(batch.status);
  const readyCount = projects.filter((p) => p.workflow_state === "READY").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Import Batch #{String(batch.batch_number).padStart(5, "0")}</h1>
          <p>
            Status: <Badge text={batch.status} />
            {batch.cancel_requested && isActive && " (stopping...)"}
          </p>
        </div>
        <div className="btn-row">
          {isActive && (
            <button className="btn btn-danger" onClick={stopProcessing} disabled={stopping || batch.cancel_requested}>
              {batch.cancel_requested ? "Stopping..." : "Stop Processing"}
            </button>
          )}
          {hasRole("REVIEWER", "ADMIN") && readyCount > 0 && (
            <button className="btn btn-success" onClick={approveAllValid}>
              Approve &amp; Import {readyCount} Valid Projects
            </button>
          )}
        </div>
      </div>

      {stopError && <div className="error-banner">{stopError}</div>}
      {bulkMessage && <div className="card">{bulkMessage}</div>}

      {isActive && (
        <div className="card">
          <h2>Processing</h2>
          <ul className="progress-list">
            <li>✓ Documents uploaded: {progress.documents_uploaded}</li>
            <li>{progress.documents_processed >= progress.documents_uploaded ? "✓" : "●"} Documents processed: {progress.documents_processed}</li>
            <li>{progress.projects_detected > 0 ? "✓" : "○"} Projects detected: {progress.projects_detected}</li>
            <li>
              {progress.projects_processed >= progress.projects_detected && progress.projects_detected > 0 ? "✓" : "●"} Projects
              processed: {progress.projects_processed} / {progress.projects_detected}
            </li>
            {progress.current_step && <li>● Currently: {progress.current_step}</li>}
          </ul>
          {progress.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <strong>Warnings:</strong>
              <ul>
                {progress.warnings.slice(0, 10).map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {progress.failures.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <strong>Failures:</strong>
              <ul>
                {progress.failures.slice(0, 10).map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{batch.projects_detected}</div>
          <div className="stat-label">Projects Detected</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{batch.projects_auto_imported}</div>
          <div className="stat-label">Auto-Imported</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{batch.projects_review_required}</div>
          <div className="stat-label">Review Required</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{batch.projects_duplicate}</div>
          <div className="stat-label">Duplicates</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{batch.projects_failed}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      <div className="card">
        <h2>Projects</h2>
        {projects.length === 0 && <div className="empty-state">No projects detected yet.</div>}
        {projects.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>Assignment</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Duplicate</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>{p.project_name || <em>Untitled</em>}</td>
                  <td>{p.client_name || "-"}</td>
                  <td>{p.source_assignment_number || "-"}</td>
                  <td>
                    <Badge text={p.workflow_state} />
                  </td>
                  <td>{p.extraction_confidence != null ? `${Math.round(p.extraction_confidence * 100)}%` : "-"}</td>
                  <td>
                    <Badge text={p.duplicate_status} />
                  </td>
                  <td>
                    <Link className="btn" to={`/projects/${p.id}`}>
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
