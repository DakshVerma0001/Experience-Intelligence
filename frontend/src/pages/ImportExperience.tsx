import { DragEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../services/api";
import type { ImportBatch } from "../types";

export default function ImportExperience() {
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  function addFiles(list: FileList | null) {
    if (!list) return;
    const accepted = Array.from(list).filter((f) => /\.(docx|pdf)$/i.test(f.name));
    setFiles((prev) => [...prev, ...accepted]);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    addFiles(e.dataTransfer.files);
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function startProcessing() {
    if (files.length === 0) return;
    setError(null);
    setUploading(true);
    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const batch = await api.postForm<ImportBatch>("/imports/batches", form);
      navigate(`/imports/${batch.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>AI Experience Import</h1>
          <p>Upload company experience documents. Text extraction and AI processing run entirely locally.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div
          className={`dropzone${dragActive ? " active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>Drag & Drop DOCX/PDF</p>
          <p style={{ margin: "0 0 16px" }}>or</p>
          <button className="btn" type="button" onClick={() => inputRef.current?.click()}>
            Choose Files
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".docx,.pdf"
            multiple
            style={{ display: "none" }}
            onChange={(e) => addFiles(e.target.files)}
          />
          <p style={{ marginTop: 16, fontSize: 12 }}>Supported: DOCX, PDF</p>
        </div>

        {files.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <h2>Selected files ({files.length})</h2>
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Size</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.map((f, idx) => (
                  <tr key={idx}>
                    <td>{f.name}</td>
                    <td>{(f.size / 1024).toFixed(0)} KB</td>
                    <td>
                      <button className="btn" onClick={() => removeFile(idx)}>
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="btn-row" style={{ marginTop: 20 }}>
          <button className="btn btn-primary" disabled={files.length === 0 || uploading} onClick={startProcessing}>
            {uploading ? "Uploading..." : "Start Processing"}
          </button>
        </div>
      </div>
    </div>
  );
}
