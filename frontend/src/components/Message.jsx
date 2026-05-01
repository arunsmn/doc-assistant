import SourceCards from "./SourceCards";

const ROUTE_LABELS = {
  rag: { label: "RAG", color: "var(--rag-color)" },
  llm: { label: "LLM", color: "var(--llm-color)" },
  reject: { label: "Rejected", color: "var(--reject-color)" },
};

export default function Message({ message }) {
  const isUser = message.role === "user";
  const routeInfo = message.route ? ROUTE_LABELS[message.route] : null;

  return (
    <div
      style={{
        ...styles.wrapper,
        justifyContent: isUser ? "flex-end" : "flex-start",
      }}
    >
      <div style={{ maxWidth: "75%" }}>
        {/* Route badge — only on assistant messages */}
        {routeInfo && (
          <div style={styles.badgeRow}>
            <span
              style={{
                ...styles.badge,
                color: routeInfo.color,
                borderColor: routeInfo.color,
              }}
            >
              {routeInfo.label}
            </span>
          </div>
        )}

        {/* Message bubble */}
        <div style={isUser ? styles.userBubble : styles.assistantBubble}>
          <p style={styles.text}>{message.content}</p>
        </div>

        {/* Source citations — only for RAG answers */}
        {message.route === "rag" && message.sources?.length > 0 && (
          <SourceCards sources={message.sources} />
        )}

        {/* Timestamp */}
        <div
          style={{ ...styles.timestamp, textAlign: isUser ? "right" : "left" }}
        >
          {message.timestamp?.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    marginBottom: "20px",
    animation: "fadeSlideUp 0.2s ease-out",
  },
  badgeRow: {
    marginBottom: "4px",
    display: "flex",
  },
  badge: {
    fontSize: "10px",
    fontFamily: "var(--font-mono)",
    fontWeight: 500,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    padding: "2px 7px",
    borderRadius: "4px",
    border: "1px solid",
    opacity: 0.85,
  },
  userBubble: {
    background: "var(--accent)",
    borderRadius: "16px 16px 4px 16px",
    padding: "12px 16px",
  },
  assistantBubble: {
    background: "var(--bg-raised)",
    border: "1px solid var(--border)",
    borderRadius: "16px 16px 16px 4px",
    padding: "12px 16px",
  },
  text: {
    margin: 0,
    fontSize: "14px",
    lineHeight: 1.65,
    whiteSpace: "pre-wrap",
    color: "var(--text-primary)",
  },
  timestamp: {
    marginTop: "5px",
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
};
