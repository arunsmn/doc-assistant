export default function TypingIndicator() {
  return (
    <div style={styles.wrapper}>
      <div style={styles.bubble}>
        <span style={{ ...styles.dot, animationDelay: "0ms" }} />
        <span style={{ ...styles.dot, animationDelay: "160ms" }} />
        <span style={{ ...styles.dot, animationDelay: "320ms" }} />
      </div>
      <style>{`
        @keyframes pulse {
          0%, 60%, 100% { opacity: 0.2; transform: scale(0.8); }
          30% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

const styles = {
  wrapper: { display: "flex", padding: "4px 0" },
  bubble: {
    background: "var(--bg-raised)",
    border: "1px solid var(--border)",
    borderRadius: "16px 16px 16px 4px",
    padding: "12px 16px",
    display: "flex",
    alignItems: "center",
    gap: "5px",
  },
  dot: {
    display: "inline-block",
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: "var(--accent)",
    animation: "pulse 1.2s ease-in-out infinite",
  },
};
