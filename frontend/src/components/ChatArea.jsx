import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";

export default function ChatArea({ messages, isThinking, activeDocument }) {
  const bottomRef = useRef(null);
  const containerRef = useRef(null);

  const isNearBottom = () => {
    const container = containerRef.current;
    if (!container) return true;
    // Consider "near bottom" if within 150px of the bottom
    return (
      container.scrollHeight - container.scrollTop - container.clientHeight <
      150
    );
  };

  useEffect(() => {
    // Only auto-scroll if user is already near the bottom
    // This lets them scroll up to read without being dragged back down
    if (isNearBottom()) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isThinking]);

  const lastMessage = messages[messages.length - 1];
  const showTyping = isThinking && lastMessage?.role === "user";

  return (
    <div ref={containerRef} className="chat-area" style={styles.container}>
      {messages.length === 0 ? (
        <div style={styles.empty}>
          {activeDocument ? (
            <>
              <div style={styles.emptyIcon}>⬡</div>
              <div style={styles.emptyTitle}>
                Ready to analyse{" "}
                <em style={{ fontFamily: "var(--font-serif)" }}>
                  {activeDocument.filename}
                </em>
              </div>
              <div style={styles.emptyHint}>
                Ask anything — summaries, specific facts, follow-ups
              </div>
            </>
          ) : (
            <>
              <div style={styles.emptyIcon}>⬡</div>
              <div style={styles.emptyTitle}>Upload a document to begin</div>
              <div style={styles.emptyHint}>
                Supports PDF files up to any size
              </div>
              <div className="mobile-upload-hint" style={styles.emptyHint}>
                Tap the menu icon (☰) in the top-left to upload a PDF or
                browse your chat history
              </div>
            </>
          )}
        </div>
      ) : (
        <div style={styles.messages}>
          {messages.map((msg) => (
            <Message key={msg.id} message={msg} />
          ))}
          {showTyping && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    flex: 1,
    overflowY: "auto",
    padding: "24px",
  },
  empty: {
    height: "100%",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: "48px",
    color: "var(--accent)",
    opacity: 0.4,
    marginBottom: "8px",
  },
  emptyTitle: {
    fontSize: "18px",
    color: "var(--text-secondary)",
    fontWeight: 400,
  },
  emptyHint: {
    fontSize: "13px",
    color: "var(--text-tertiary)",
  },
  messages: {
    display: "flex",
    flexDirection: "column",
  },
};
