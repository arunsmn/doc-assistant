import axios from "axios";

// Single axios instance for the whole app.
// If the backend URL ever changes, you change it in one place.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 60000,
});

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const sendMessage = async (question, collectionName, chatHistory) => {
  const response = await api.post("/chat/", {
    question,
    collection_name: collectionName,
    // Convert our message array to the tuple format the backend expects
    // [{role, content}] → [["question", "answer"], ...]
    chat_history: chatHistory.reduce((pairs, msg, i, arr) => {
      if (msg.role === "user" && arr[i + 1]?.role === "assistant") {
        pairs.push([msg.content, arr[i + 1].content]);
      }
      return pairs;
    }, []),
  });
  return response.data;
};

export const sendMessageStream = (
  question,
  collectionName,
  chatHistory,
  onToken,
  onSources,
  onDone,
  onError,
) => {
  /**
   * Streaming version of sendMessage.
   * Uses EventSource to receive tokens as they arrive.
   *
   * onToken(text)    — called for each token received
   * onSources(srcs)  — called once with source citations
   * onDone()         — called when stream completes
   * onError(err)     — called if something goes wrong
   */
  const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // We use fetch instead of EventSource because we need POST with a body
  fetch(`${baseURL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      collection_name: collectionName,
      chat_history: chatHistory.reduce((pairs, msg, i, arr) => {
        if (msg.role === "user" && arr[i + 1]?.role === "assistant") {
          pairs.push([msg.content, arr[i + 1].content]);
        }
        return pairs;
      }, []),
    }),
  })
    .then((response) => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      const read = async () => {
        const { done, value } = await reader.read();

        if (done) {
          onDone();
          return;
        }

        const text = decoder.decode(value);
        const lines = text
          .split("\n")
          .filter((line) => line.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.replace("data: ", ""));
            if (data.type === "token") {
              // Gemini sends large chunks — split into words for smooth streaming
              const words = data.content.split(/(\s+)/);
              for (const word of words) {
                if (word) {
                  onToken(word);
                  await new Promise((resolve) => setTimeout(resolve, 20));
                }
              }
            } else if (data.type === "sources") onSources(data.sources);
            else if (data.type === "done") onDone(data.route);
            else if (data.type === "error") onError(data.message);
          } catch {
            // skip malformed chunks
          }
        }

        read();
      };

      read();
    })
    .catch(onError);
};

export const fetchDocuments = async () => {
  const response = await api.get("/documents/");
  return response.data;
};

export const fetchChatHistory = async (collectionName) => {
  const response = await api.get(`/chat/history/${collectionName}`);
  return response.data;
};

export const sendAgentMessage = async (
  question,
  collectionName,
  chatHistory,
) => {
  const response = await api.post("/chat/agent", {
    question,
    collection_name: collectionName,
    chat_history: chatHistory.reduce((pairs, msg, i, arr) => {
      if (
        msg.role === "user" &&
        arr[i + 1]?.role === "assistant" &&
        typeof msg.content === "string" &&
        typeof arr[i + 1]?.content === "string"
      ) {
        pairs.push([msg.content, arr[i + 1].content]);
      }
      return pairs;
    }, []),
  });
  return response.data;
};
