import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import ChatInput from "./components/ChatInput";
import { useChat } from "./hooks/useChat";

export default function App() {
  const {
    documents,
    activeDocument,
    messages,
    isUploading,
    isThinking,
    isAgentMode,
    setIsAgentMode,
    error,
    handleUpload,
    handleSend,
    handleAgentSend,
    switchDocument,
  } = useChat();

  return (
    <div style={styles.app}>
      <style>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      <Sidebar
        documents={documents}
        activeDocument={activeDocument}
        onUpload={handleUpload}
        onSwitch={switchDocument}
        isUploading={isUploading}
      />

      <div style={styles.main}>
        <div style={styles.header}>
          <div style={styles.headerTitle}>
            {activeDocument ? activeDocument.filename : "DocMind"}
          </div>
          {activeDocument && (
            <div style={styles.headerMeta}>
              {activeDocument.pages} pages · {activeDocument.chunks} chunks
              indexed
            </div>
          )}
        </div>

        {error && <div style={styles.errorBanner}>⚠ {error}</div>}

        <ChatArea
          messages={messages}
          isThinking={isThinking}
          activeDocument={activeDocument}
        />

        <ChatInput
          onSend={handleSend}
          onAgentSend={handleAgentSend}
          isThinking={isThinking}
          disabled={!activeDocument}
          isAgentMode={isAgentMode}
          onToggleAgentMode={() => setIsAgentMode((prev) => !prev)}
        />
      </div>
    </div>
  );
}

const styles = {
  app: {
    display: "flex",
    height: "100vh",
    overflow: "hidden",
    background: "var(--bg-base)",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    minWidth: 0,
  },
  header: {
    padding: "16px 24px",
    borderBottom: "1px solid var(--border)",
    background: "var(--bg-surface)",
    display: "flex",
    alignItems: "baseline",
    gap: "12px",
  },
  headerTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: "17px",
    color: "var(--text-primary)",
    letterSpacing: "-0.01em",
  },
  headerMeta: {
    fontSize: "12px",
    fontFamily: "var(--font-mono)",
    color: "var(--text-tertiary)",
  },
  errorBanner: {
    padding: "10px 24px",
    background: "rgba(232, 85, 85, 0.1)",
    borderBottom: "1px solid rgba(232, 85, 85, 0.2)",
    color: "var(--reject-color)",
    fontSize: "13px",
  },
};
