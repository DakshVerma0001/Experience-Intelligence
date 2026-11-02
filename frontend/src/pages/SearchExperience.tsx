import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { SearchResultItem } from "../types";

export default function SearchExperience() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [results, setResults] = useState<SearchResultItem[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const resp = await api.post<{ results: SearchResultItem[] }>("/search", { query, mode, limit: 20 });
      setResults(resp.results);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Experience Search</h1>
          <p>Search previously imported company experience using keyword, semantic, or hybrid search.</p>
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleSearch} className="btn-row" style={{ alignItems: "stretch" }}>
          <input
            type="text"
            placeholder='e.g. "government ERP project involving financial management and dashboards"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <select value={mode} onChange={(e) => setMode(e.target.value)} style={{ width: 160 }}>
            <option value="hybrid">Hybrid</option>
            <option value="keyword">Keyword</option>
            <option value="semantic">Semantic</option>
            <option value="fulltext">Full-text</option>
          </select>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
      </div>

      {results !== null && (
        <div className="card">
          <h2>{results.length} result{results.length !== 1 ? "s" : ""}</h2>
          {results.length === 0 && <div className="empty-state">No matching experience found.</div>}
          {results.map((r) => (
            <div key={r.project_id} className="card" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <Link to={`/projects/${r.project_id}`}>
                    <strong>{r.project_name || "Untitled Project"}</strong>
                  </Link>
                  <p style={{ margin: "4px 0", color: "#667085", fontSize: 13 }}>
                    {r.client_name} {r.state_ut ? `· ${r.state_ut}` : ""} {r.country ? `· ${r.country}` : ""}
                  </p>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{Math.round(r.score * 100)}% match</div>
              </div>
              {r.ai_search_summary && <p style={{ fontSize: 13 }}>{r.ai_search_summary}</p>}
              {r.match_reasons.length > 0 && (
                <div>
                  <span style={{ fontSize: 12, color: "#667085" }}>Matched because: </span>
                  <div className="tag-list" style={{ marginTop: 4 }}>
                    {r.match_reasons.map((reason) => (
                      <span className="tag" key={reason}>
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
