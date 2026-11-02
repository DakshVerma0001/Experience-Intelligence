import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { ProjectSummary } from "../types";
import Badge from "../components/Badge";

export default function ReviewQueue() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<ProjectSummary[]>("/review/queue")
      .then(setProjects)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Review Queue</h1>
          <p>Projects requiring human review: low confidence, missing fields, possible duplicates, or failures.</p>
        </div>
      </div>
      <div className="card">
        {loading && <p>Loading...</p>}
        {!loading && projects.length === 0 && <div className="empty-state">Nothing pending review. 🎉</div>}
        {projects.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>State</th>
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
