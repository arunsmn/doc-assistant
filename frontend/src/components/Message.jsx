import SourceCards from "./SourceCards";

const ROUTE_LABELS = {
  rag: { label: "RAG", color: "var(--rag-color)" },
  llm: { label: "LLM", color: "var(--llm-color)" },
  reject: { label: "Rejected", color: "var(--reject-color)" },
  agent: { label: "Agent", color: "var(--llm-color)" },
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
      <div className="message-content">
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
            {/* Show tool calls for agent responses */}
            {message.route === "agent" && message.toolCalls?.length > 0 && (
              <span style={styles.toolCallsBadge}>
                {message.toolCalls.map((tc) => tc.tool).join(" → ")}
              </span>
            )}
          </div>
        )}

        <div style={isUser ? styles.userBubble : styles.assistantBubble}>
          <p
            style={{
              ...styles.text,
              color: isUser ? "#000" : "var(--text-primary)",
            }}
          >
            {message.content}
          </p>
        </div>

        {message.route === "rag" && message.sources?.length > 0 && (
          <SourceCards sources={message.sources} />
        )}

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
    alignItems: "center",
    gap: "8px",
    flexWrap: "wrap",
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
  toolCallsBadge: {
    fontSize: "10px",
    fontFamily: "var(--font-mono)",
    color: "var(--text-tertiary)",
    background: "var(--bg-raised)",
    border: "1px solid var(--border)",
    padding: "2px 7px",
    borderRadius: "4px",
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
  },
  timestamp: {
    marginTop: "5px",
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
};
