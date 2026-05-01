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
