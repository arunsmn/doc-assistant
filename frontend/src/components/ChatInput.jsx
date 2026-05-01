import { useState } from "react";
import { SendHorizonal } from "lucide-react";

export default function ChatInput({ onSend, isThinking, disabled }) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (!value.trim() || isThinking || disabled) return;
    onSend(value.trim());
    setValue("");
  };

  const handleKeyDown = (e) => {
    // Send on Enter, new line on Shift+Enter
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.inputRow}>
        <textarea
          style={styles.textarea}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? "Upload a document to start chatting..."
              : "Ask anything about your document..."
          }
          disabled={disabled || isThinking}
          rows={1}
        />
        <button
          style={{
            ...styles.sendButton,
            opacity: !value.trim() || isThinking || disabled ? 0.4 : 1,
          }}
          onClick={handleSubmit}
          disabled={!value.trim() || isThinking || disabled}
        >
          <SendHorizonal size={18} />
        </button>
      </div>
      <p style={styles.hint}>Enter to send · Shift+Enter for new line</p>
    </div>
  );
}

const styles = {
  container: {
    padding: "16px 24px 20px",
    borderTop: "1px solid var(--border)",
    background: "var(--bg-surface)",
  },
  inputRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: "10px",
    background: "var(--bg-raised)",
    border: "1px solid var(--border-mid)",
    borderRadius: "var(--radius-lg)",
    padding: "10px 12px",
    transition: "border-color 0.2s",
  },
  textarea: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    color: "var(--text-primary)",
    fontSize: "14px",
    lineHeight: 1.6,
    resize: "none",
    maxHeight: "120px",
    overflowY: "auto",
  },
  sendButton: {
    background: "var(--accent)",
    color: "#000",
    border: "none",
    borderRadius: "8px",
    width: "34px",
    height: "34px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    flexShrink: 0,
    transition: "opacity 0.2s",
  },
  hint: {
    marginTop: "8px",
    fontSize: "11px",
    color: "var(--text-tertiary)",
    textAlign: "center",
  },
};
