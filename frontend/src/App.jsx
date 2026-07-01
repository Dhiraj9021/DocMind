// src/App.jsx
// Generates a unique session_id on mount and passes it to all components.
// This ensures uploads and queries are always scoped to THIS browser session.

import { useState, useRef } from "react";
import { v4 as uuidv4 } from "uuid"; // npm install uuid
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import UploadZone from "./components/UploadZone";

export default function App() {
  // ✅ One stable session ID per page load — never changes between re-renders
  const sessionId = useRef(uuidv4()).current;

  const [messages, setMessages]         = useState([]);
  const [isLoading, setIsLoading]       = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  const handleUploadSuccess = (fileNames) => {
    setUploadedFiles(prev => [...new Set([...prev, ...fileNames])]);
    setMessages([]); // clear chat when new docs are loaded
  };

  const handleSend = async (question) => {
    if (!uploadedFiles.length) return;

    setMessages(prev => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    try {
      const { data } = await axios.post("http://localhost:8000/query", {
        question,
        // ✅ Backend uses this to filter chunks — only searches THIS session's docs
        session_id: sessionId,
      });

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources ?? [],
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
          sources: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      display: "flex", height: "100vh",
      background: "#0f0f0f", color: "#e5e5e5",
      fontFamily: "Inter, system-ui, sans-serif"
    }}>

      {/* ── Sidebar ── */}
      <div style={{
        width: "260px", borderRight: "1px solid #1f1f1f",
        display: "flex", flexDirection: "column",
        background: "#0a0a0a", flexShrink: 0
      }}>
        <div style={{
          padding: "16px", borderBottom: "1px solid #1f1f1f"
        }}>
          <h1 style={{ fontSize: "15px", fontWeight: 600, color: "#e5e5e5" }}>
            PaperBrain
          </h1>
          <p style={{ fontSize: "11px", color: "#444", marginTop: "2px" }}>
            Session: {sessionId.slice(0, 8)}…
          </p>
        </div>

        {/* Upload zone receives sessionId */}
        <UploadZone
          onUploadSuccess={handleUploadSuccess}
          sessionId={sessionId}
        />

        {/* Loaded files list */}
        {uploadedFiles.length > 0 && (
          <div style={{ padding: "0 16px 16px" }}>
            <p style={{ fontSize: "10px", color: "#444",
              textTransform: "uppercase", letterSpacing: "0.06em",
              marginBottom: "6px" }}>
              Indexed in this session
            </p>
            {uploadedFiles.map((name, i) => (
              <div key={i} style={{
                fontSize: "12px", color: "#666",
                padding: "4px 0",
                borderBottom: "1px solid #1a1a1a"
              }}>
                📄 {name}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Chat panel ── */}
      <div style={{
        flex: 1, display: "flex",
        flexDirection: "column", minWidth: 0
      }}>
        <ChatWindow messages={messages} isLoading={isLoading} />
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading || uploadedFiles.length === 0}
        />
      </div>
    </div>
  );
}