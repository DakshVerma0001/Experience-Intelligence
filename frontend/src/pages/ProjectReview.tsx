import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../services/api";
import type { ProjectDetail } from "../types";
import Badge from "../components/Badge";
import { hasRole } from "../services/auth";

const EDITABLE_FIELDS: { key: keyof ProjectDetail; label: string }[] = [
  { key: "project_name", label: "Project Name" },
  { key: "short_form", label: "Short Form" },
  { key: "client_name", label: "Client Name" },
  { key: "client_type", label: "Client Type" },
  { key: "project_status", label: "Project Status" },
  { key: "country", label: "Country" },
  { key: "state_ut", label: "State / UT" },
  { key: "contract_value_crore", label: "Contract Value (Crore)" },
  { key: "client_address", label: "Client Address" },
  { key: "contact_person", label: "Contact Person" },
  { key: "designation", label: "Designation" },
  { key: "telephone", label: "Telephone" },
  { key: "email", label: "Email" },
  { key: "start_date", label: "Start Date" },
  { key: "completion_date", label: "Completion Date" },
  { key: "total_staff_months", label: "Total Staff-Months" },
  { key: "associated_consultants", label: "Associated Consultants" },
  { key: "senior_professional_staff", label: "Senior Professional Staff" },
];

export default function ProjectReview() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [showSource, setShowSource] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!projectId) return;
    const data = await api.get<ProjectDetail>(`/projects/${projectId}`);
    setProject(data);
    const initial: Record<string, string> = {};
    EDITABLE_FIELDS.forEach(({ key }) => {
      const v = data[key];
      initial[key as string] = v == null ? "" : String(v);
    });
    setDrafts(initial);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function saveEdits() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const edits = EDITABLE_FIELDS.map(({ key }) => ({
        field: key as string,
        value: drafts[key as string] === "" ? null : drafts[key as string],
      }));
      const updated = await api.patch<ProjectDetail>(`/projects/${project.id}`, { edits });
      setProject(updated);
      setEditMode(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save edits");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${project.id}/approve`, {});
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!project) return;
    const reason = window.prompt("Reason for rejecting this project:");
    if (!reason) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${project.id}/reject`, { reason });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<{ id: string }>(`/review/${project.id}/retry`);
      navigate(`/projects/${result.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Retry failed");
    } finally {
      setBusy(false);
    }
  }

  async function resolveDuplicate(action: "import_anyway" | "mark_duplicate") {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/review/${project.id}/resolve-duplicate`, { action });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to resolve duplicate");
    } finally {
      setBusy(false);
    }
  }

  if (!project) return <p>Loading...</p>;

  const canReview = hasRole("REVIEWER", "ADMIN");

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{project.project_name || "Untitled Project"}</h1>
          <p>
            Status: <Badge text={project.workflow_state} /> &nbsp; Confidence:{" "}
            {project.extraction_confidence != null ? `${Math.round(project.extraction_confidence * 100)}%` : "n/a"}
          </p>
        </div>
        <div className="btn-row">
          <button className="btn" onClick={() => setEditMode((v) => !v)}>
            {editMode ? "Cancel Edit" : "Edit"}
          </button>
          <button className="btn" onClick={() => setShowSource((v) => !v)}>
            View Source
          </button>
          {canReview && project.workflow_state === "FAILED" && (
            <button className="btn" onClick={retry} disabled={busy}>
              Retry
            </button>
          )}
          {canReview && !["IMPORTED", "IMPORTING", "REJECTED"].includes(project.workflow_state) && (
            <>
              <button className="btn btn-success" onClick={approve} disabled={busy}>
                Approve
              </button>
              <button className="btn btn-danger" onClick={reject} disabled={busy}>
                Reject
              </button>
            </>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {project.workflow_state === "DUPLICATE_REVIEW" && (
        <div className="card">
          <h2>Possible Duplicate</h2>
          <p>
            Similarity: <strong>{Math.round((project.duplicate_similarity || 0) * 100)}%</strong> with an existing project
            (ID: {project.duplicate_of_project_id}).
          </p>
          {canReview && (
            <div className="btn-row">
              <button className="btn" onClick={() => project.duplicate_of_project_id && navigate(`/projects/${project.duplicate_of_project_id}`)}>
                Compare / View Existing Project
              </button>
              <button className="btn btn-success" onClick={() => resolveDuplicate("import_anyway")} disabled={busy}>
                Import Anyway
              </button>
              <button className="btn btn-danger" onClick={() => resolveDuplicate("mark_duplicate")} disabled={busy}>
                Mark as Duplicate
              </button>
            </div>
          )}
        </div>
      )}

      {project.validation_warnings.length > 0 && (
        <div className="card">
          <h2>Warnings</h2>
          <ul>
            {project.validation_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {project.failure_reason && (
        <div className="card">
          <h2>Failure Reason</h2>
          <p>{project.failure_reason}</p>
        </div>
      )}

      {showSource && (
        <div className="card">
          <h2>Source Evidence</h2>
          <p className="fp-meta">
            {project.source_filename} &middot; {project.source_assignment_number || "no assignment marker"} &middot;{" "}
            {project.source_location}
            {project.source_page ? ` (page ${project.source_page})` : ""}
          </p>
          <div className="source-panel">{project.source_text}</div>
        </div>
      )}

      <div className="card">
        <h2>Project Information</h2>
        {editMode ? (
          <div className="form-grid">
            {EDITABLE_FIELDS.map(({ key, label }) => (
              <div className="form-field" key={key as string}>
                <label>{label}</label>
                <input
                  type="text"
                  value={drafts[key as string] ?? ""}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [key as string]: e.target.value }))}
                />
              </div>
            ))}
            <div className="form-field" style={{ gridColumn: "1 / -1" }}>
              <label>Project Description</label>
              <textarea
                rows={3}
                value={drafts["project_description"] ?? ""}
                onChange={(e) => setDrafts((prev) => ({ ...prev, project_description: e.target.value }))}
              />
            </div>
            <div className="form-field" style={{ gridColumn: "1 / -1" }}>
              <label>Actual Services</label>
              <textarea
                rows={3}
                value={drafts["actual_services"] ?? ""}
                onChange={(e) => setDrafts((prev) => ({ ...prev, actual_services: e.target.value }))}
              />
            </div>
            <div className="form-field" style={{ gridColumn: "1 / -1" }}>
              <label>AI Search Summary</label>
              <textarea
                rows={2}
                value={drafts["ai_search_summary"] ?? ""}
                onChange={(e) => setDrafts((prev) => ({ ...prev, ai_search_summary: e.target.value }))}
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <button className="btn btn-primary" onClick={saveEdits} disabled={busy}>
                Save Changes
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="form-grid">
              {EDITABLE_FIELDS.map(({ key, label }) => (
                <div className="form-field" key={key as string}>
                  <label>{label}</label>
                  <div>{(project[key] as string) ?? <em>Not extracted</em>}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16 }}>
              <label style={{ fontWeight: 600, fontSize: 12, color: "#667085" }}>Project Description</label>
              <p>{project.project_description || <em>Not extracted</em>}</p>
            </div>
            <div>
              <label style={{ fontWeight: 600, fontSize: 12, color: "#667085" }}>Actual Services</label>
              <p>{project.actual_services || <em>Not extracted</em>}</p>
            </div>
          </>
        )}
      </div>

      <div className="card">
        <h2>AI Search Summary</h2>
        <p>{project.ai_search_summary || <em>Not generated (LLM may have been unavailable during processing)</em>}</p>
      </div>

      <div className="card">
        <h2>Keywords ({project.keywords.length})</h2>
        {project.keywords.length === 0 && <p>No keywords generated.</p>}
        {project.keywords.map((k) => (
          <div className="keyword-card" key={k.id}>
            <div className="keyword-title">{k.keyword}</div>
            <div className="keyword-category">{k.category}</div>
            <p>{k.description}</p>
            {k.aliases.length > 0 && (
              <div className="tag-list" style={{ marginTop: 6 }}>
                {k.aliases.map((a) => (
                  <span className="tag" key={a}>
                    {a}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Field Provenance</h2>
        {project.field_provenance.length === 0 && <p>No field-level provenance recorded.</p>}
        {project.field_provenance.map((fp, i) => (
          <div className="field-provenance-row" key={i}>
            <div className="fp-label">{fp.field}</div>
            <div>
              <div>{fp.value ?? <em>null</em>}</div>
              <div className="fp-meta">
                {fp.extraction_type} {fp.edited_by_human ? "· edited by human" : ""}
                {fp.source_text ? ` · source: "${fp.source_text.slice(0, 80)}"` : ""}
              </div>
            </div>
            <div className="fp-meta">{fp.confidence != null ? `${Math.round(fp.confidence * 100)}% confidence` : "-"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
