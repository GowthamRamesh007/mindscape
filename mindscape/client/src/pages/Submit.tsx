import { ArrowLeft, ArrowUpRight, Check, CloudUpload, FileVideo, Info, Loader2, ShieldCheck, AlertCircle, Play } from "lucide-react";
import { ChangeEvent, FormEvent, useState, useRef } from "react";
import { Link } from "wouter";
import { uploadReelToSupabase, submitReelToBackend, type VideoMetadata } from "@/lib/supabase";

export default function Submit() {
  const [file, setFile] = useState<File | null>(null);
  const [blobUrl, setBlobUrl] = useState<string>("");
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState(false);
  const [referenceCode, setReferenceCode] = useState("MS-2026-SUBMISSION");
  const [error, setError] = useState("");
  const [copySuccess, setCopySuccess] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (selected: File) => {
    const validExtensions = [".mp4", ".mov", ".m4v", ".webm", ".mkv"];
    const fileName = selected.name.toLowerCase();
    const isValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidExt && !selected.type.startsWith("video/")) {
      setError("Please select an MP4, MOV, or WEBM video file.");
      return;
    }

    if (selected.size > 100 * 1024 * 1024) {
      setError("File exceeds the 100 MB limit. Please compress or re-export your reel.");
      return;
    }

    setError("");
    setFile(selected);
    const url = URL.createObjectURL(selected);
    setBlobUrl(url);

    // HTML5 in-browser video inspection
    const video = document.createElement("video");
    video.preload = "metadata";
    video.src = url;

    video.onloadedmetadata = () => {
      const dur = Math.round(video.duration * 10) / 10;
      const w = video.videoWidth;
      const h = video.videoHeight;
      const isPortrait = h > w;
      const durationOk = dur >= 25.0 && dur <= 45.0;

      const meta: VideoMetadata = {
        duration: dur,
        width: w,
        height: h,
        aspectRatio: `${w}:${h}`,
        isPortrait,
        durationOk,
        isValid: isPortrait && durationOk,
      };

      setMetadata(meta);

      if (!durationOk) {
        setError(`Your reel is ${dur}s. Competition rules require reels between 25 and 45 seconds.`);
      } else if (!isPortrait) {
        setError("Reels must be in vertical portrait mode (9:16 aspect ratio). Horizontal video detected.");
      } else {
        setError("");
      }
    };
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Please choose a reel video file before submitting.");
      return;
    }

    if (metadata && !metadata.isValid) {
      setError("Please ensure your reel meets the 25–45s vertical (9:16) specifications.");
      return;
    }

    const form = event.currentTarget;
    const values = new FormData(form);

    const teamName = String(values.get("teamName") || "").trim();
    const repName = String(values.get("repName") || "").trim();
    const repEmail = String(values.get("repEmail") || "").trim();
    const repPhone = String(values.get("repPhone") || "").trim();
    const institution = String(values.get("institution") || "").trim();
    const city = String(values.get("city") || "Chennai").trim();
    const title = String(values.get("title") || "").trim();
    const language = String(values.get("language") || "Tamil").trim();
    const description = String(values.get("description") || "").trim();

    setError("");
    setIsUploading(true);
    setUploadProgress(10);

    try {
      // 1. Direct Supabase Storage Upload to 'mindscape-reels' bucket
      const { filePath } = await uploadReelToSupabase(teamName, file, (progress) => {
        setUploadProgress(progress);
      });

      // 2. Submit record to backend API
      const result = await submitReelToBackend({
        teamName,
        representativeName: repName,
        representativeEmail: repEmail,
        representativePhone: repPhone,
        institution,
        city,
        title,
        description,
        language,
        filePath,
        fileName: file.name,
        fileSize: file.size,
        duration: metadata?.duration || 30.0,
        width: metadata?.width || 1080,
        height: metadata?.height || 1920,
        originalityConfirmed: true,
        participantConsentConfirmed: true,
        copyrightConfirmed: true,
        rulesConfirmed: true,
        finalLockConfirmed: true,
      });

      const refId = result.submission_id
        ? `MS-26-${result.submission_id.slice(0, 4).toUpperCase()}`
        : `MS-26-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

      setReferenceCode(refId);
      setSubmitted(true);
    } catch (err: any) {
      console.error("[Submission Error]", err);
      setError(err.message || "Failed to upload reel. Please check your connection and try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const copyRefCode = () => {
    navigator.clipboard.writeText(referenceCode);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  if (submitted) {
    return (
      <div className="submit-shell site-shell">
        <header className="submit-topbar">
          <Link href="/" className="brand">
            <span className="brand-mark"><span /></span>
            <span className="font-oblisk">mindscape</span>
          </Link>
          <div className="submit-top-actions">
            <Link href="/" className="text-link"><ArrowLeft size={16} /> Return to contest</Link>
          </div>
        </header>

        <main className="success-panel">
          <div className="success-orbit">
            <div className="success-ring ring-one" />
            <div className="success-ring ring-two" />
            <div className="success-core"><Check size={38} /></div>
          </div>
          <h1>Your reel is in.<br /><span>Locked for judging.</span></h1>
          <p>
            Your video has been securely uploaded to the competition archive. Our jury panel from Rotary Club of Madras and Rotaract Club of Vepery will review your entry according to the official 60-point judging rubric.
          </p>
          <div className="reference-card">
            <span>Official Submission Reference ID</span>
            <strong>{referenceCode}</strong>
            <button onClick={copyRefCode}>
              {copySuccess ? "Copied!" : "Copy ID"}
            </button>
          </div>
          <div className="success-actions">
            <Link href="/" className="button button-primary">
              Back to Home <ArrowUpRight size={16} />
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="submit-shell site-shell">
      <header className="submit-topbar">
        <Link href="/" className="brand">
          <span className="brand-mark"><span /></span>
          <span className="font-oblisk">mindscape</span>
        </Link>
        <div className="submit-top-actions">
          <span className="form-progress">Direct Reel Portal · 2026</span>
          <Link href="/" className="text-link"><ArrowLeft size={16} /> Back to Home</Link>
        </div>
      </header>

      <main className="submit-layout">
        <div className="submit-intro">
          <span className="section-kicker">Digital Reel Upload</span>
          <h1>Turn your perspective<br /><span>into an impact.</span></h1>
          <p>
            Upload your team's 25–45 second vertical reel addressing mobile phone addiction. Entries are inspected in-browser, securely uploaded to Supabase Storage, and locked for jury evaluation.
          </p>

          <div className="submit-rule">
            <ShieldCheck size={18} />
            <span>25–45 seconds · 9:16 vertical orientation · Max 100 MB · MP4 or MOV</span>
          </div>

          <div className="submit-art">
            <span className="submit-art-dot dot-sun" />
            <span className="submit-art-dot dot-sky" />
            <div className="submit-art-card">
              <span>PRIZE POOL</span>
              <em>₹55,000</em>
              <span>GRAND PRIZE ₹25,000</span>
            </div>
          </div>
        </div>

        <section
          className={`form-card ${isDragging ? "drag-active" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="form-card-head">
            <div>
              <span className="form-step">STEP 01 OF 01</span>
              <h2>Team & Video Submission</h2>
            </div>
            <div className="progress-dots">
              <span className="active" /><span className="active" /><span className="active" />
            </div>
          </div>

          {isDragging && (
            <div style={{ padding: 12, marginBottom: 16, background: "rgba(0, 242, 254, 0.1)", border: "1px dashed #00f2fe", borderRadius: 8, textAlign: "center", color: "#00f2fe", fontWeight: 600, fontSize: 13 }}>
              🎬 Drop your reel video anywhere inside this box!
            </div>
          )}

          {error && (
            <div className="form-error" style={{ marginTop: 18, borderRadius: 8 }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Team Info */}
            <div className="field-grid">
              <label>
                <span>Team Name <b>*</b></span>
                <input name="teamName" placeholder="e.g. Visual Mindscapes" required />
              </label>
              <label>
                <span>Team Representative Name <b>*</b></span>
                <input name="repName" placeholder="Lead creator's full name" required />
              </label>
            </div>

            <div className="field-grid">
              <label>
                <span>Representative Email <b>*</b></span>
                <input name="repEmail" type="email" placeholder="lead@institution.edu" required />
              </label>
              <label>
                <span>Contact Phone Number <b>*</b></span>
                <input name="repPhone" type="tel" placeholder="10-digit mobile number" required />
              </label>
            </div>

            <div className="field-grid">
              <label>
                <span>College / Institution / Club <b>*</b></span>
                <input name="institution" placeholder="e.g. Jeppiaar University" required />
              </label>
              <label>
                <span>City <b>*</b></span>
                <input name="city" defaultValue="Chennai" required />
              </label>
            </div>

            {/* Video File Inspector */}
            <div className="form-divider">
              <span>02 · VIDEO FILE & VERIFICATION</span>
              <strong>Inspect and validate your reel</strong>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              accept="video/mp4,video/quicktime,video/webm,video/*,.mp4,.mov,.webm,.mkv,.m4v"
              style={{ display: "none" }}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
              }}
            />

            <div
              className={`upload-zone ${file ? "has-file" : ""} ${isDragging ? "active" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className={`upload-icon ${file ? "uploaded" : ""}`}>
                {file ? <FileVideo size={22} /> : <CloudUpload size={22} />}
              </div>
              <strong>{file ? file.name : "Drag & Drop Reel here or Click to select"}</strong>
              <span>
                {file
                  ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · Click or drop another file to replace`
                  : "MP4, MOV, WEBM (Recommended: 1080×1920 • Max 100 MB • 25–45 seconds)"}
              </span>
            </div>

            {/* Video Preview & Live Inspector Badges */}
            {blobUrl && (
              <div style={{ marginTop: 14, background: "#f1f5f2", borderRadius: 12, padding: 16 }}>
                <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                  <div style={{ width: 90, height: 140, borderRadius: 8, overflow: "hidden", background: "#000", position: "relative" }}>
                    <video
                      src={blobUrl}
                      controls
                      playsInline
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#1a2a22", marginBottom: 6 }}>
                      In-Browser Video Inspector
                    </div>
                    {metadata ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        <span className={`meta-badge ${metadata.durationOk ? "badge-valid" : "badge-invalid"}`}>
                          {metadata.duration}s {metadata.durationOk ? "✓ (25–45s valid)" : "✕ (Must be 25–45s)"}
                        </span>
                        <span className={`meta-badge ${metadata.isPortrait ? "badge-valid" : "badge-invalid"}`}>
                          {metadata.width}×{metadata.height} {metadata.isPortrait ? "✓ (Vertical 9:16)" : "✕ (Not vertical)"}
                        </span>
                        <span className="meta-badge badge-neutral">
                          {(file!.size / (1024 * 1024)).toFixed(1)} MB
                        </span>
                      </div>
                    ) : (
                      <span style={{ fontSize: 11, color: "#6a7b74" }}>Reading video metadata...</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Reel Details */}
            <div className="field-grid" style={{ marginTop: 10 }}>
              <label>
                <span>Reel Title <b>*</b></span>
                <input name="title" placeholder="e.g. Beyond the Screen" required />
              </label>
              <label>
                <span>Primary Language <b>*</b></span>
                <input name="language" defaultValue="Tamil" placeholder="Tamil / English / etc." required />
              </label>
            </div>

            <label>
              <span>Short Description / Message <b>*</b></span>
              <textarea
                name="description"
                rows={2}
                placeholder="Briefly state the perspective or awareness message in your reel..."
                required
              />
            </label>

            {/* Legal and Ethical Consent Confirmations */}
            <div className="form-divider">
              <span>03 · ETHICAL & LEGAL CONFIRMATIONS</span>
              <strong>Mandatory participation declarations</strong>
            </div>

            <label className="checkbox-label">
              <input type="checkbox" required />
              <span>I confirm that this reel is <u>original content</u> created by our team.</span>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" required />
              <span>I confirm that all identifiable individuals in the reel have provided <u>consent</u>.</span>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" required />
              <span>I confirm adherence to the <u>Mindscape ethical guidelines</u> on mental health awareness.</span>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" required />
              <span>I confirm permissions or licenses for any third-party audio or media used.</span>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" required />
              <span>I understand that entries are <u>final and locked</u> once submitted for judging.</span>
            </label>

            {/* Upload Progress Bar */}
            {isUploading && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#4f665a", marginBottom: 6 }}>
                  <span>Uploading reel to Supabase Storage...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div style={{ width: "100%", height: 6, background: "#dbe3de", borderRadius: 4, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${uploadProgress}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, #ff45d3, #7d27f4)",
                      transition: "width 0.2s ease",
                    }}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading}
              className="button button-primary submit-button"
              style={{ marginTop: 14, width: "100%", justifyContent: "center" }}
            >
              {isUploading ? (
                <>
                  <Loader2 className="spin" size={16} /> Uploading & Locking Reel ({uploadProgress}%)...
                </>
              ) : (
                <>
                  Lock & Submit Reel for Judging <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
