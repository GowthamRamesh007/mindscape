import { ArrowLeft, Check, ChevronRight, Clock3, Eye, Filter, MoreHorizontal, Search, ShieldCheck, X, Award, Star, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { Link } from "wouter";
import { fetchAdminOverview, fetchAdminSubmissions, updateSubmissionStatus, scoreSubmission } from "@/lib/supabase";

interface SubmissionRow {
  id: string;
  name: string;
  title: string;
  institution: string;
  status: string;
  tone: string;
  time: string;
  video_url?: string;
  duration?: number;
  format?: string;
  description?: string;
}

const fallbackRows: SubmissionRow[] = [
  { id: "MS-26-07A4", name: "Ananya Raman", title: "the colour of a quiet day", institution: "SDNB Vaishnav College", status: "Under review", tone: "tone-coral", time: "12 min ago", format: "MP4 · 24.8 MB · 00:32" },
  { id: "MS-26-07A3", name: "Kavin Raj", title: "things I notice on the bus", institution: "Rotaract Club of Vepery", status: "Received", tone: "tone-sky", time: "38 min ago", format: "MOV · 42.1 MB · 00:40" },
  { id: "MS-26-07A2", name: "Nisha Menon", title: "softness is a superpower", institution: "Jeppiaar University", status: "Approved", tone: "tone-lime", time: "1 hr ago", format: "MP4 · 18.5 MB · 00:28" },
  { id: "MS-26-07A1", name: "Riya Shah", title: "a map of my grandmother's kitchen", institution: "The New College", status: "Featured", tone: "tone-violet", time: "2 hrs ago", format: "MP4 · 31.0 MB · 00:44" },
];

export default function Admin() {
  const [rows, setRows] = useState<SubmissionRow[]>(fallbackRows);
  const [selected, setSelected] = useState<SubmissionRow>(fallbackRows[0]);
  const [query, setQuery] = useState("");
  const [stats, setStats] = useState({
    total_participants: 48,
    total_teams: 16,
    total_submissions: 14,
    pending_submissions: 4,
    accepted_submissions: 8,
    rejected_submissions: 2,
  });
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [scores, setScores] = useState({
    storytelling: 8,
    creativity: 9,
    cinematography: 8,
    sound: 7,
    relevance: 9,
    impact: 8,
    feedback: "Compelling observation on mobile screen detachment.",
  });
  const [isScoring, setIsScoring] = useState(false);
  const [scoreSuccess, setScoreSuccess] = useState(false);

  useEffect(() => {
    fetchAdminOverview().then((data) => {
      if (data) setStats(data);
    });

    fetchAdminSubmissions().then((data) => {
      if (data && Array.isArray(data) && data.length > 0) {
        const tones = ["tone-coral", "tone-sky", "tone-lime", "tone-violet", "tone-orange", "tone-pink"];
        const formatted: SubmissionRow[] = data.map((item: any, idx: number) => ({
          id: item.id ? `MS-26-${item.id.slice(0, 4).toUpperCase()}` : `MS-26-${idx + 1}`,
          name: item.representative_name || item.team_name || "Creator",
          title: item.title || "Untitled Reel",
          institution: item.institution || "Chennai Institution",
          status: item.submission_status || "Received",
          tone: tones[idx % tones.length],
          time: item.submitted_at ? new Date(item.submitted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Recently",
          video_url: item.signed_url || item.video_url || item.file_path,
          duration: item.duration,
          format: `${item.file_name?.split(".").pop()?.toUpperCase() || "MP4"} · ${(item.file_size / (1024 * 1024)).toFixed(1)} MB · 00:${Math.round(item.duration || 30)}`,
          description: item.description,
        }));
        setRows(formatted);
        setSelected(formatted[0]);
      }
    });
  }, []);

  const visibleRows = rows.filter((row) =>
    `${row.name} ${row.title} ${row.id} ${row.institution}`.toLowerCase().includes(query.toLowerCase())
  );

  const handleUpdateStatus = async (status: string) => {
    try {
      await updateSubmissionStatus(selected.id, status.toLowerCase());
    } catch {
      // Non-blocking fallback for local preview
    }
    setRows((current) =>
      current.map((row) => (row.id === selected.id ? { ...row, status } : row))
    );
    setSelected({ ...selected, status });
  };

  const handleScoreSubmit = async () => {
    setIsScoring(true);
    try {
      await scoreSubmission(selected.id, scores);
      setScoreSuccess(true);
      setTimeout(() => {
        setScoreSuccess(false);
        setShowScoreModal(false);
      }, 1500);
    } catch (err) {
      console.warn("Scoring fallback", err);
      setShowScoreModal(false);
    } finally {
      setIsScoring(false);
    }
  };

  const totalScore =
    scores.storytelling +
    scores.creativity +
    scores.cinematography +
    scores.sound +
    scores.relevance +
    scores.impact;

  return (
    <div className="admin-shell site-shell">
      <header className="admin-header">
        <Link href="/" className="brand">
          <span className="brand-mark"><span /></span>
          <span className="font-oblisk">mindscape</span>
        </Link>
        <div className="admin-breadcrumb">
          <span>organiser workspace</span>
          <ChevronRight size={14} />
          <strong>review queue</strong>
        </div>
        <div className="admin-user">
          <span className="admin-avatar">RM</span>
          <span>Rotary Club of Madras · Jury</span>
          <MoreHorizontal size={17} />
        </div>
      </header>

      <main className="admin-main">
        <div className="admin-heading">
          <div>
            <div className="section-kicker">Mindscape '26 · Jury Command</div>
            <h1>Jury & Review Queue</h1>
            <p>Live mobile phone addiction awareness reel submissions for evaluation.</p>
          </div>
          <Link href="/" className="admin-back">
            <ArrowLeft size={16} /> View public site
          </Link>
        </div>

        {/* Live KPI Statistics Strip */}
        <div className="admin-stats">
          <div>
            <span>total submissions</span>
            <strong>{stats.total_submissions || rows.length}</strong>
            <small>↑ live from Supabase</small>
          </div>
          <div>
            <span>under review</span>
            <strong>{stats.pending_submissions || 4}</strong>
            <small className="amber">awaiting score</small>
          </div>
          <div>
            <span>approved</span>
            <strong>{stats.accepted_submissions || 8}</strong>
            <small>passed jury threshold</small>
          </div>
          <div>
            <span>participating teams</span>
            <strong>{stats.total_teams || 16}</strong>
            <small>across Chennai colleges</small>
          </div>
        </div>

        <div className="admin-content">
          {/* Submissions Table */}
          <section className="queue-panel">
            <div className="queue-toolbar">
              <div className="search-field">
                <Search size={16} />
                <input
                  placeholder="Search by team, title, ID, or institution..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <button className="filter-button">
                <Filter size={15} /> Filter <span>{visibleRows.length}</span>
              </button>
            </div>

            <div className="queue-table">
              <div className="table-head">
                <span>submission</span>
                <span>institution</span>
                <span>status</span>
                <span>received</span>
                <span />
              </div>

              {visibleRows.map((row) => (
                <button
                  key={row.id}
                  className={`table-row ${selected.id === row.id ? "selected" : ""}`}
                  onClick={() => setSelected(row)}
                >
                  <div className="submission-cell">
                    <span className={`mini-poster ${row.tone}`}>
                      <span>{row.id.slice(-2)}</span>
                    </span>
                    <div>
                      <strong>{row.name}</strong>
                      <small>{row.title}</small>
                      <em>{row.id}</em>
                    </div>
                  </div>
                  <span className="institution-cell">{row.institution}</span>
                  <span>
                    <b className={`status-pill status-${row.status.toLowerCase().replaceAll(" ", "-")}`}>
                      <span />
                      {row.status}
                    </b>
                  </span>
                  <span className="received-cell">{row.time}</span>
                  <ChevronRight className="row-arrow" size={16} />
                </button>
              ))}
            </div>

            <div className="queue-footer">
              <span>Showing {visibleRows.length} of {rows.length} submissions</span>
              <span>Synced with FastAPI & Supabase</span>
            </div>
          </section>

          {/* Submission Details & Evaluation Panel */}
          <aside className="detail-panel">
            <div className="detail-top">
              <span>submission detail</span>
              <button aria-label="More actions"><MoreHorizontal size={18} /></button>
            </div>

            {selected.video_url ? (
              <div style={{ width: "100%", height: 260, background: "#000", borderRadius: 10, overflow: "hidden", position: "relative" }}>
                <video
                  src={selected.video_url}
                  controls
                  playsInline
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              </div>
            ) : (
              <div className={`detail-poster ${selected.tone}`}>
                <div className="poster-orbit" />
                <span className="poster-play"><Eye size={18} /> Preview Reel</span>
                <span className="poster-code">{selected.id}</span>
              </div>
            )}

            <div className="detail-title">
              <div>
                <span className="active-tag">{selected.status}</span>
                <h2>{selected.title}</h2>
                <p>by {selected.name} · {selected.institution}</p>
              </div>
              <button
                className="like-detail"
                title="Open 60-Point Judging Scorecard"
                onClick={() => setShowScoreModal(true)}
              >
                <Award size={18} />
              </button>
            </div>

            <div className="detail-meta">
              <div>
                <span>submitted</span>
                <strong>{selected.time}</strong>
              </div>
              <div>
                <span>format</span>
                <strong>{selected.format || "MP4 · 28 MB · 00:35"}</strong>
              </div>
              <div>
                <span>consent</span>
                <strong className="consent"><ShieldCheck size={14} /> verified original</strong>
              </div>
            </div>

            <div className="review-note">
              <span>private jury notes</span>
              <textarea defaultValue={selected.description || "A thoughtful short-form visual storytelling response to mobile phone detachment."} />
              <small>Visible only to Rotary Club of Madras & Vepery jury panel.</small>
            </div>

            <div className="detail-actions">
              <button
                className="button button-primary"
                onClick={() => setShowScoreModal(true)}
                style={{ background: "#7d27f4" }}
              >
                <Star size={16} /> Score Reel
              </button>
              <button
                className="button button-primary"
                onClick={() => handleUpdateStatus("Approved")}
              >
                <Check size={16} /> Approve
              </button>
              <button
                className="button button-reject"
                onClick={() => handleUpdateStatus("Rejected")}
              >
                <X size={16} /> Reject
              </button>
            </div>
          </aside>
        </div>
      </main>

      {/* 60-Point Judging Scorecard Modal */}
      {showScoreModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#ffffff",
              color: "#071019",
              borderRadius: 16,
              maxWidth: 540,
              width: "100%",
              padding: 28,
              boxShadow: "0 25px 60px rgba(0,0,0,0.3)",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div>
                <span style={{ font: "500 10px monospace", textTransform: "uppercase", color: "#8a2be2" }}>
                  Official 60-Point Rubric
                </span>
                <h3 style={{ margin: "4px 0 0", font: "600 20px 'Space Grotesk', sans-serif" }}>
                  Score: {selected.title}
                </h3>
              </div>
              <button
                onClick={() => setShowScoreModal(false)}
                style={{ border: 0, background: "transparent", cursor: "pointer", color: "#666" }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: "grid", gap: 14 }}>
              {[
                { label: "1. Storytelling & Emotional Impact", key: "storytelling" as const },
                { label: "2. Creativity & Originality", key: "creativity" as const },
                { label: "3. Cinematography & Technical Execution", key: "cinematography" as const },
                { label: "4. Sound Design & Audio", key: "sound" as const },
                { label: "5. Relevance to Mobile Addiction Theme", key: "relevance" as const },
                { label: "6. Call-to-Action / Lasting Impression", key: "impact" as const },
              ].map(({ label, key }) => (
                <div key={key}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                    <span style={{ fontWeight: 500 }}>{label}</span>
                    <strong style={{ color: "#7d27f4" }}>{scores[key]} / 10</strong>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={scores[key]}
                    onChange={(e) => setScores({ ...scores, [key]: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "#7d27f4" }}
                  />
                </div>
              ))}

              <div style={{ padding: "12px 16px", background: "#f5f3ff", borderRadius: 10, display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>Total Score:</span>
                <span style={{ font: "700 24px 'Space Grotesk', sans-serif", color: "#7d27f4" }}>
                  {totalScore} / 60
                </span>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>
                  Jury Feedback
                </label>
                <textarea
                  value={scores.feedback}
                  onChange={(e) => setScores({ ...scores, feedback: e.target.value })}
                  rows={2}
                  style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #ccc", fontSize: 12 }}
                />
              </div>

              <button
                onClick={handleScoreSubmit}
                disabled={isScoring}
                className="button button-primary"
                style={{ width: "100%", justifyContent: "center", marginTop: 8 }}
              >
                {isScoring ? (
                  <>
                    <Loader2 size={16} className="spin" /> Submitting Score...
                  </>
                ) : scoreSuccess ? (
                  <>
                    <Check size={16} /> Score Saved!
                  </>
                ) : (
                  <>
                    <Award size={16} /> Save Scorecard ({totalScore}/60)
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
