export default function SourceCards({ sources }) {
  if (!sources?.length) return null;

  return (
    <div style={styles.container}>
      <div style={styles.label}>Sources</div>
      <div style={styles.cards}>
        {sources.map((source, i) => (
          <div key={i} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.pageTag}>p.{source.page + 1}</span>
              <span style={styles.filename}>{source.source_file}</span>
            </div>
            <p style={styles.snippet}>{source.snippet}…</p>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  container: { marginTop: "12px" },
  label: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    marginBottom: "8px",
    fontWeight: 500,
  },
  cards: { display: "flex", flexDirection: "column", gap: "6px" },
  card: {
    background: "var(--bg-raised)",
    border: "1px solid var(--border)",
    borderLeft: "2px solid var(--accent)",
    borderRadius: "var(--radius-sm)",
    padding: "10px 12px",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "6px",
  },
  pageTag: {
    fontSize: "11px",
    fontFamily: "var(--font-mono)",
    color: "var(--accent)",
    background: "var(--accent-dim)",
    padding: "2px 6px",
    borderRadius: "4px",
    fontWeight: 500,
  },
  filename: {
    fontSize: "11px",
    fontFamily: "var(--font-mono)",
    color: "var(--text-tertiary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  snippet: {
    fontSize: "12px",
    color: "var(--text-secondary)",
    lineHeight: 1.5,
    margin: 0,
  },
};
