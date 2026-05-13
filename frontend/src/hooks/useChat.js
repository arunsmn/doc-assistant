import { useState, useCallback, useRef, useEffect } from "react";
import { uploadDocument, sendMessageStream } from "../api/client";

export function useChat() {
  const [documents, setDocuments] = useState([]);
  const [activeDocument, setActiveDocument] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState(null);

  const tokenQueue = useRef([]);
  const isProcessing = useRef(false);
  const assistantIdRef = useRef(null);
  const assistantAddedRef = useRef(false);
  const pendingSourcesRef = useRef([]);
  const processQueueRef = useRef(null);

  useEffect(() => {
    processQueueRef.current = () => {
      if (tokenQueue.current.length === 0) {
        isProcessing.current = false;
        return;
      }

      const token = tokenQueue.current.shift();
      const id = assistantIdRef.current;

      if (!assistantAddedRef.current) {
        assistantAddedRef.current = true;
        setIsThinking(false);
        setMessages((prev) => [
          ...prev,
          {
            id,
            role: "assistant",
            content: token,
            sources: [],
            route: null,
            timestamp: new Date(),
          },
        ]);
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === id ? { ...msg, content: msg.content + token } : msg,
          ),
        );
      }

      setTimeout(() => processQueueRef.current?.(), 30);
    };
  });

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
      setMessages([]);
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

      const userMessage = {
        id: Date.now(),
        role: "user",
        content: question,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsThinking(true);
      setError(null);

      const assistantId = Date.now() + 1;
      assistantIdRef.current = assistantId;
      assistantAddedRef.current = false;
      tokenQueue.current = [];
      isProcessing.current = false;
      pendingSourcesRef.current = [];

      sendMessageStream(
        question,
        activeDocument.collectionName,
        messages,

        // onToken
        (token) => {
          tokenQueue.current.push(token);
          if (!isProcessing.current) {
            isProcessing.current = true;
            processQueueRef.current?.();
          }
        },

        // onSources — just store, apply in onDone
        (sources) => {
          pendingSourcesRef.current = sources;
        },

        // onDone — drain queue, apply sources and route together
        (route) => {
          const id = assistantIdRef.current;
          const remaining = tokenQueue.current.join("");
          tokenQueue.current = [];
          isProcessing.current = false;

          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== id) return msg;
              return {
                ...msg,
                content: msg.content + remaining,
                sources: pendingSourcesRef.current,
                route: route || msg.route,
              };
            }),
          );

          setIsThinking(false);
        },

        // onError
        () => {
          setIsThinking(false);
          tokenQueue.current = [];
          isProcessing.current = false;
          setError("Something went wrong. Please try again.");
        },
      );
    },
    [activeDocument, messages],
  );

  const switchDocument = useCallback((doc) => {
    setActiveDocument(doc);
    setMessages([]);
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
