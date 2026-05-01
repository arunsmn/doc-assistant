import { useState, useCallback } from "react";
import { uploadDocument, sendMessage } from "../api/client";

export function useChat() {
  // All uploaded documents: [{ id, filename, collectionName, uploadedAt }]
  const [documents, setDocuments] = useState([]);

  // The active document the user is chatting with
  const [activeDocument, setActiveDocument] = useState(null);

  // All messages: [{ id, role, content, sources, route, timestamp }]
  const [messages, setMessages] = useState([]);

  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = useCallback(async (file) => {
    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadDocument(file);

      const newDoc = {
        id: result.collection_name,
        filename: result.filename,
        collectionName: result.collection_name,
        pages: result.pages_loaded,
        chunks: result.chunks_created,
        uploadedAt: new Date(),
      };

      setDocuments((prev) => [newDoc, ...prev]);
      setActiveDocument(newDoc);
      setMessages([]); // fresh chat for new document

      return newDoc;
    } catch (err) {
      setError(
        err.response?.data?.detail || "Upload failed. Please try again.",
      );
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleSend = useCallback(
    async (question) => {
      if (!question.trim()) return;
      if (!activeDocument) {
        setError("Please upload a document first.");
        return;
      }

      // Add user message immediately — don't wait for the API
      const userMessage = {
        id: Date.now(),
        role: "user",
        content: question,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsThinking(true);
      setError(null);

      try {
        const result = await sendMessage(
          question,
          activeDocument.collectionName,
          messages,
        );

        const assistantMessage = {
          id: Date.now() + 1,
          role: "assistant",
          content: result.answer,
          sources: result.sources || [],
          route: result.route, // 'rag', 'llm', or 'reject'
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        setError(
          err.response?.data?.detail ||
            "Something went wrong. Please try again.",
        );
      } finally {
        setIsThinking(false);
      }
    },
    [activeDocument, messages],
  );

  const switchDocument = useCallback((doc) => {
    setActiveDocument(doc);
    setMessages([]); // each document gets its own clean history
    setError(null);
  }, []);

  return {
    documents,
    activeDocument,
    messages,
    isUploading,
    isThinking,
    error,
    handleUpload,
    handleSend,
    switchDocument,
  };
}
