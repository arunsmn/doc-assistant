import { useRef } from "react";
import { Upload, FileText, Loader2, Clock } from "lucide-react";

export default function Sidebar({
  documents,
  activeDocument,
  onUpload,
  onSwitch,
  isUploading,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) onUpload(file);
    // Reset so the same file can be re-uploaded if needed
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".pdf")) onUpload(file);
  };

  const handleDragOver = (e) => e.preventDefault();

  return (
    <aside style={styles.sidebar}>
      {/* Logo / Title */}
      <div style={styles.header}>
        <span style={styles.logoIcon}>⬡</span>
        <div>
          <div style={styles.logoTitle}>DocMind</div>
          <div style={styles.logoSub}>Document Intelligence</div>
        </div>
      </div>

      <div style={styles.divider} />

      {/* Upload zone */}
      <div
        style={styles.uploadZone}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        {isUploading ? (
          <>
            <Loader2 size={18} style={styles.spinIcon} />
            <span style={styles.uploadText}>Processing...</span>
          </>
        ) : (
          <>
            <Upload size={18} color="var(--accent)" />
            <span style={styles.uploadText}>Upload PDF</span>
            <span style={styles.uploadHint}>or drag and drop</span>
          </>
        )}
      </div>

      <div style={styles.divider} />

      {/* Document list */}
      <div style={styles.docListHeader}>Documents</div>
      <div style={styles.docList}>
        {documents.length === 0 ? (
          <div style={styles.emptyDocs}>No documents yet</div>
        ) : (
          documents.map((doc) => (
            <button
              key={doc.id}
              style={{
                ...styles.docItem,
                ...(activeDocument?.id === doc.id ? styles.docItemActive : {}),
              }}
              onClick={() => onSwitch(doc)}
            >
              <FileText
                size={14}
                color={
                  activeDocument?.id === doc.id
                    ? "var(--accent)"
                    : "var(--text-tertiary)"
                }
              />
              <div style={styles.docInfo}>
                <span style={styles.docName}>{doc.filename}</span>
                <span style={styles.docMeta}>
                  {doc.pages}p · {doc.chunks} chunks
                </span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Footer */}
      <div style={styles.sidebarFooter}>
        <Clock size={12} color="var(--text-tertiary)" />
        <span style={styles.footerText}>
          {documents.length} document{documents.length !== 1 ? "s" : ""} loaded
        </span>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: "var(--sidebar-width)",
    minWidth: "var(--sidebar-width)",
    height: "100vh",
    background: "var(--bg-surface)",
    borderRight: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  header: {
    padding: "20px 20px 16px",
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  logoIcon: {
    fontSize: "24px",
    color: "var(--accent)",
    lineHeight: 1,
  },
  logoTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: "18px",
    color: "var(--text-primary)",
    letterSpacing: "-0.02em",
  },
  logoSub: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
    letterSpacing: "0.05em",
    textTransform: "uppercase",
  },
  divider: {
    height: "1px",
    background: "var(--border)",
    margin: "0",
  },
  uploadZone: {
    margin: "12px",
    padding: "14px",
    border: "1px dashed var(--accent-border)",
    borderRadius: "var(--radius-md)",
    background: "var(--accent-dim)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "6px",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  uploadText: {
    fontSize: "13px",
    color: "var(--accent)",
    fontWeight: 500,
  },
  uploadHint: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
  spinIcon: {
    color: "var(--accent)",
    animation: "spin 1s linear infinite",
  },
  docListHeader: {
    padding: "12px 20px 8px",
    fontSize: "11px",
    color: "var(--text-tertiary)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    fontWeight: 500,
  },
  docList: {
    flex: 1,
    overflowY: "auto",
    padding: "0 8px",
  },
  emptyDocs: {
    padding: "12px",
    fontSize: "13px",
    color: "var(--text-tertiary)",
    textAlign: "center",
  },
  docItem: {
    width: "100%",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    padding: "10px 12px",
    borderRadius: "var(--radius-sm)",
    cursor: "pointer",
    transition: "background 0.15s",
    background: "transparent",
    color: "inherit",
    textAlign: "left",
    marginBottom: "2px",
  },
  docItemActive: {
    background: "var(--accent-dim)",
    border: "1px solid var(--accent-border)",
  },
  docInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    minWidth: 0,
  },
  docName: {
    fontSize: "13px",
    color: "var(--text-primary)",
    fontFamily: "var(--font-mono)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: "180px",
  },
  docMeta: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
  sidebarFooter: {
    padding: "12px 20px",
    borderTop: "1px solid var(--border)",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  footerText: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
};
