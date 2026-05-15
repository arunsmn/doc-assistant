import { useState } from "react";
import { SendHorizonal, Bot, Zap } from "lucide-react";

export default function ChatInput({
  onSend,
  onAgentSend,
  isThinking,
  disabled,
  isAgentMode,
  onToggleAgentMode,
}) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (!value.trim() || isThinking || disabled) return;
    if (isAgentMode) {
      onAgentSend(value.trim());
    } else {
      onSend(value.trim());
    }
    setValue("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={styles.container}>
      {/* Agent mode toggle */}
      <div style={styles.toggleRow}>
        <button
          style={{
            ...styles.toggleBtn,
            ...(isAgentMode ? styles.toggleActive : styles.toggleInactive),
          }}
          onClick={onToggleAgentMode}
          disabled={disabled}
        >
          <Bot size={14} />
          <span>Agent mode</span>
          {isAgentMode && <Zap size={12} />}
        </button>
        {isAgentMode && (
          <span style={styles.agentHint}>
            Uses multiple tools to research your question
          </span>
        )}
      </div>

      <div style={styles.inputRow}>
        <textarea
          style={styles.textarea}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? "Upload a document to start chatting..."
              : isAgentMode
                ? "Ask a complex question — the agent will reason across tools..."
                : "Ask anything about your document..."
          }
          disabled={disabled || isThinking}
          rows={1}
        />
        <button
          style={{
            ...styles.sendButton,
            opacity: !value.trim() || isThinking || disabled ? 0.4 : 1,
            background: isAgentMode ? "var(--llm-color)" : "var(--accent)",
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
  toggleRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "10px",
  },
  toggleBtn: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "4px 12px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: 500,
    cursor: "pointer",
    border: "1px solid",
    transition: "all 0.2s",
    background: "transparent",
  },
  toggleActive: {
    color: "var(--llm-color)",
    borderColor: "var(--llm-color)",
    background: "rgba(52, 201, 138, 0.1)",
  },
  toggleInactive: {
    color: "var(--text-tertiary)",
    borderColor: "var(--border)",
  },
  agentHint: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
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
    transition: "all 0.2s",
  },
  hint: {
    marginTop: "8px",
    fontSize: "11px",
    color: "var(--text-tertiary)",
    textAlign: "center",
  },
};
