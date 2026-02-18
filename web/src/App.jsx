import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function statusBadge(status) {
  if (status === "complete" || status === "done") return "ok";
  if (status === "failed") return "fail";
  if (status === "running") return "warn";
  return "";
}

function prettyJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : JSON.stringify(body)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json().catch(() => ({}));
}

export default function App() {
  const [photos, setPhotos] = useState([]);
  const [selectedPhotoId, setSelectedPhotoId] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [run, setRun] = useState(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const fileRef = useRef(null);
  const pollRef = useRef(null);

  const selectedRun = useMemo(() => runs.find(r => r.id === selectedRunId) || null, [runs, selectedRunId]);

  async function refreshPhotos() {
    const data = await apiGet("/photos");
    setPhotos(data);
    if (!selectedPhotoId && data.length) setSelectedPhotoId(data[0].id);
  }

  async function refreshPhotoAndRuns(photoId) {
    const [p, r] = await Promise.all([
      apiGet(`/photos/${photoId}`),
      apiGet(`/photos/${photoId}/runs`).catch(() => []) // in case you haven't added it yet
    ]);
    setSelectedPhoto(p);
    setRuns(r);
    // pick latest run if exists
    if (r.length) setSelectedRunId(r[0].id);
    else setSelectedRunId(null);
  }

  async function refreshRun(runId) {
    const data = await apiGet(`/runs/${runId}`);
    setRun(data);
  }

  useEffect(() => {
    (async () => {
      try {
        setError("");
        await refreshPhotos();
      } catch (e) {
        setError(String(e.message || e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedPhotoId) return;
    (async () => {
      try {
        setError("");
        await refreshPhotoAndRuns(selectedPhotoId);
      } catch (e) {
        setError(String(e.message || e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPhotoId]);

  useEffect(() => {
    // stop previous polling
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setRun(null);

    if (!selectedRunId) return;

    // initial fetch
    refreshRun(selectedRunId).catch(e => setError(String(e.message || e)));

    // poll every 1s
    pollRef.current = setInterval(() => {
      refreshRun(selectedRunId).catch(() => {});
    }, 1000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRunId]);

  async function onUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    try {
      setBusy(true);
      setError("");
      const fd = new FormData();
      fd.append("file", file);

      const created = await apiPost("/photos/upload", fd);
      await refreshPhotos();
      setSelectedPhotoId(created.id);
      // clear input
      fileRef.current.value = "";
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  async function onStartRun() {
    if (!selectedPhotoId) return;
    try {
      setBusy(true);
      setError("");
      const createdRun = await apiPost(`/photos/${selectedPhotoId}/run`, {});
      // createdRun has run id; select it
      await refreshPhotoAndRuns(selectedPhotoId);
      setSelectedRunId(createdRun.id);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  async function submitFeedback(correct) {
    if (!selectedPhotoId || !run?.id) return;
    const reasons = correct ? [] : ["missed_object", "wrong_class"]; // starter defaults
    const notes = correct ? "Looks good." : "Explain what was wrong (edit me in code / next iteration we make a dialog).";
    try {
      setBusy(true);
      setError("");
      await apiPost(`/photos/${selectedPhotoId}/feedback`, {
        run_id: run.id,
        correct,
        reasons,
        notes
      });
      // refresh run to see feedback embedded in summary details (MVP behavior)
      await refreshRun(run.id);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container">
      <div className="sidebar">
        <div className="h1">Asset Identification</div>

        <div className="card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div style={{ fontWeight: 700 }}>Upload</div>
            <button className="btn" onClick={refreshPhotos} disabled={busy}>Refresh</button>
          </div>
          <div style={{ height: 8 }} />
          <input ref={fileRef} className="input" type="file" accept="image/*" />
          <div style={{ height: 8 }} />
          <button className="btn primary" onClick={onUpload} disabled={busy}>Upload Photo</button>
          <div style={{ height: 8 }} />
          <div className="small">API: <span className="mono">{API_BASE}</span></div>
        </div>

        {error ? (
          <div className="card" style={{ borderColor: "#ffb8b8", background: "#fff0f0" }}>
            <div style={{ fontWeight: 800 }}>Error</div>
            <div className="small mono" style={{ whiteSpace: "pre-wrap" }}>{error}</div>
          </div>
        ) : null}

        <div className="card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div style={{ fontWeight: 700 }}>Photos</div>
            <div className="badge">{photos.length} total</div>
          </div>
          <div style={{ height: 8 }} />
          {photos.length === 0 ? (
            <div className="small">No photos yet. Upload one.</div>
          ) : (
            photos.map(p => (
              <div
                key={p.id}
                className={`listItem ${p.id === selectedPhotoId ? "active" : ""}`}
                onClick={() => setSelectedPhotoId(p.id)}
              >
                <div style={{ fontWeight: 700 }}>{p.filename}</div>
                <div className="small">ID: <span className="mono">{p.id}</span></div>
                <div className="small">{new Date(p.uploaded_at).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="main">
        {!selectedPhoto ? (
          <div className="card">
            <div className="h1">Select a photo</div>
            <div className="small">Upload or click a photo in the left panel.</div>
          </div>
        ) : (
          <>
            <div className="card">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <div className="h1" style={{ marginBottom: 6 }}>{selectedPhoto.filename}</div>
                  <div className="small">Photo ID: <span className="mono">{selectedPhoto.id}</span></div>
                  <div className="small">Stored: <span className="mono">{selectedPhoto.stored_path}</span></div>
                </div>
                <div className="row">
                  <button className="btn primary" onClick={onStartRun} disabled={busy}>
                    Start Run
                  </button>
                </div>
              </div>

              <hr />

              <div className="row" style={{ justifyContent: "space-between" }}>
                <div style={{ fontWeight: 800 }}>Runs</div>
                <div className="small">Click a run to view live steps.</div>
              </div>

              <div style={{ height: 8 }} />

              {runs.length === 0 ? (
                <div className="small">No runs yet. Click “Start Run”.</div>
              ) : (
                <div className="row" style={{ flexWrap: "wrap" }}>
                  {runs.map(r => (
                    <button
                      key={r.id}
                      className="btn"
                      style={{
                        borderColor: r.id === selectedRunId ? "#111" : undefined
                      }}
                      onClick={() => setSelectedRunId(r.id)}
                    >
                      Run <span className="mono">#{r.id}</span>{" "}
                      <span className={`badge ${statusBadge(r.status)}`}>{r.status}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {run ? (
              <>
                <div className="grid2">
                  <div className="card">
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <div style={{ fontWeight: 800 }}>Run</div>
                      <div className={`badge ${statusBadge(run.status)}`}>
                        <span className="mono">#{run.id}</span> {run.status}
                      </div>
                    </div>
                    <div className="small">Created: {new Date(run.created_at).toLocaleString()}</div>
                    <div style={{ height: 10 }} />
                    <div className="row">
                      <button className="btn" onClick={() => submitFeedback(true)} disabled={busy}>? Correct</button>
                      <button className="btn" onClick={() => submitFeedback(false)} disabled={busy}>? Incorrect</button>
                    </div>
                    <div className="small" style={{ marginTop: 8 }}>
                      (Next iteration: feedback dialog + reason checkboxes.)
                    </div>
                  </div>

                  <div className="card">
                    <div style={{ fontWeight: 800, marginBottom: 8 }}>Live Steps</div>
                    <div className="small">
                      This polls <span className="mono">/runs/{run.id}</span> every 1s.
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div style={{ fontWeight: 800, marginBottom: 10 }}>Pipeline</div>
                  {run.steps.map(step => (
                    <div key={step.id} className="card" style={{ marginBottom: 10 }}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <div className="stepTitle">{step.name}</div>
                        <div className={`badge ${statusBadge(step.status)}`}>{step.status}</div>
                      </div>
                      <div className="small">Updated: {step.updated_at ? new Date(step.updated_at).toLocaleString() : "—"}</div>
                      <div style={{ height: 8 }} />
                      <div className="stepDetails">
                        <pre style={{ margin: 0 }}>{prettyJson(step.details)}</pre>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="card">
                <div style={{ fontWeight: 800 }}>No run selected</div>
                <div className="small">Start a run or select one from the Runs buttons above.</div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
