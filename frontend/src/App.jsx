// src/App.jsx

import { useState } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import UploadZone from "./components/UploadZone";

const API = "http://localhost:8000";

export default function App() {
  const [messages,      setMessages]      = useState([]);
  const [isLoading,     setIsLoading]     = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [activeDoc,     setActiveDoc]     = useState(null);
  const [searchMode,    setSearchMode]    = useState("single");

  const handleUploadSuccess = (fileNames) => {
    setUploadedFiles(prev => [...new Set([...prev, ...fileNames])]);
    if (fileNames.length > 0) {
      setActiveDoc(fileNames[fileNames.length - 1]);
    }
    setMessages([]);
  };

  const selectDoc = (name) => {
    setActiveDoc(name);
    setSearchMode("single");
    setMessages([]);
  };

  // Delete a document from UI + ChromaDB
  const deleteDoc = async (name, e) => {
    e.stopPropagation(); // don't trigger selectDoc

    try {
      await axios.delete(`${API}/document/${encodeURIComponent(name)}`);
    } catch (err) {
      console.error("Delete error:", err);
      // Still remove from UI even if backend call fails
    }

    const remaining = uploadedFiles.filter(f => f !== name);
    setUploadedFiles(remaining);

    if (activeDoc === name) {
      setActiveDoc(remaining.length > 0 ? remaining[remaining.length - 1] : null);
      setMessages([]);
    }
  };

  const handleSend = async (question) => {
    if (!uploadedFiles.length) return;
    if (searchMode === "single" && !activeDoc) return;

    setMessages(prev => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    try {
      const { data } = await axios.post(`${API}/query`, {
        question,
        document_name: searchMode === "single" ? activeDoc : null,
      });

      setMessages(prev => [
        ...prev,
        {
          role:    "assistant",
          content: data.answer,
          sources: data.sources ?? [],
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again.", sources: [] },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const canSend = uploadedFiles.length > 0 &&
    (searchMode === "all" || (searchMode === "single" && activeDoc));

  return (
    <div style={{
      display: "flex", height: "100vh",
      background: "#0f0f0f", color: "#e5e5e5",
      fontFamily: "Inter, system-ui, sans-serif"
    }}>

      {/* ── SIDEBAR ── */}
      <div style={{
        width: "260px", borderRight: "1px solid #1f1f1f",
        display: "flex", flexDirection: "column",
        background: "#0a0a0a", flexShrink: 0, overflowY: "auto"
      }}>

        {/* Logo */}
        <div style={{ padding: "16px", borderBottom: "1px solid #1f1f1f" }}>
          <h1 style={{ fontSize: "15px", fontWeight: 600, color: "#e5e5e5" }}>
             DocMind
          </h1>
          <p style={{ fontSize: "11px", color: "#444", marginTop: "2px" }}>
            AI Document Q&A
          </p>
        </div>

        {/* Upload */}
        <UploadZone onUploadSuccess={handleUploadSuccess} />

        {/* Search Mode Toggle */}
        {uploadedFiles.length > 0 && (
          <div style={{
            margin: "12px", padding: "12px",
            background: "#111", borderRadius: "8px",
            border: "1px solid #1f1f1f"
          }}>
            <p style={{
              fontSize: "10px", color: "#444",
              textTransform: "uppercase", letterSpacing: "0.06em",
              marginBottom: "10px"
            }}>
              🔍 Search Mode
            </p>

            {/* Single doc */}
            <div
              onClick={() => setSearchMode("single")}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                padding: "7px 10px", borderRadius: "6px", cursor: "pointer",
                marginBottom: "6px",
                background: searchMode === "single" ? "#1a1a2e" : "transparent",
                border: searchMode === "single" ? "1px solid #2d2d5e" : "1px solid transparent",
              }}
            >
              <div style={{
                width: "14px", height: "14px", borderRadius: "50%",
                border: `2px solid ${searchMode === "single" ? "#6366f1" : "#333"}`,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
              }}>
                {searchMode === "single" && (
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#6366f1" }} />
                )}
              </div>
              <div>
                <div style={{ fontSize: "12px", color: searchMode === "single" ? "#a0a0ff" : "#666" }}>
                  Selected doc only
                </div>
                <div style={{ fontSize: "10px", color: "#333", marginTop: "1px" }}>Precise, isolated answers</div>
              </div>
            </div>

            {/* All docs */}
            <div
              onClick={() => setSearchMode("all")}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                padding: "7px 10px", borderRadius: "6px", cursor: "pointer",
                background: searchMode === "all" ? "#1a2a1a" : "transparent",
                border: searchMode === "all" ? "1px solid #2d5e2d" : "1px solid transparent",
              }}
            >
              <div style={{
                width: "14px", height: "14px", borderRadius: "50%",
                border: `2px solid ${searchMode === "all" ? "#22c55e" : "#333"}`,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
              }}>
                {searchMode === "all" && (
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#22c55e" }} />
                )}
              </div>
              <div>
                <div style={{ fontSize: "12px", color: searchMode === "all" ? "#86efac" : "#666" }}>
                  All uploaded docs
                </div>
                <div style={{ fontSize: "10px", color: "#333", marginTop: "1px" }}>Cross-document search</div>
              </div>
            </div>
          </div>
        )}

        {/* Documents list with delete buttons */}
        {uploadedFiles.length > 0 && (
          <div style={{ padding: "0 12px 12px" }}>
            <p style={{
              fontSize: "10px", color: "#444",
              textTransform: "uppercase", letterSpacing: "0.06em",
              margin: "4px 4px 8px"
            }}>
              Documents ({uploadedFiles.length})
            </p>

            {uploadedFiles.map((name, i) => {
              const isActive = name === activeDoc && searchMode === "single";
              return (
                <div
                  key={i}
                  onClick={() => selectDoc(name)}
                  style={{
                    display: "flex", alignItems: "center", gap: "6px",
                    padding: "7px 8px 7px 10px",
                    borderRadius: "6px", marginBottom: "4px", cursor: "pointer",
                    background: isActive ? "#1a1a2e" : "transparent",
                    border: isActive ? "1px solid #2d2d5e" : "1px solid #1a1a1a",
                    transition: "all 0.15s",
                  }}
                >
                  {/* File icon + name */}
                  <span style={{ fontSize: "13px", flexShrink: 0 }}> </span>
                  <span style={{
                    flex: 1, fontSize: "11.5px", wordBreak: "break-all",
                    color: isActive ? "#a0a0ff" : "#555",
                  }}>
                    {name}
                  </span>

                  {/* DELETE button */}
                  <button
                    onClick={(e) => deleteDoc(name, e)}
                    title="Delete document"
                    style={{
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      padding: "2px 4px",
                      borderRadius: "4px",
                      color: "#333",
                      fontSize: "13px",
                      flexShrink: 0,
                      lineHeight: 1,
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = "#f87171"; e.currentTarget.style.background = "#2a1a1a"; }}
                    onMouseLeave={e => { e.currentTarget.style.color = "#333";    e.currentTarget.style.background = "transparent"; }}
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Active indicator */}
        {uploadedFiles.length > 0 && (
          <div style={{
            margin: "auto 12px 12px", padding: "8px 10px",
            background: "#0d1117", border: "1px solid #1f2937",
            borderRadius: "6px", fontSize: "11px",
          }}>
            {searchMode === "all" ? (
              <>
                <span style={{ color: "#22c55e" }}>●</span>
                <span style={{ color: "#444", marginLeft: "6px" }}>
                  Searching <b style={{ color: "#86efac" }}>all {uploadedFiles.length} docs</b>
                </span>
              </>
            ) : activeDoc ? (
              <>
                <span style={{ color: "#6366f1" }}>●</span>
                <span style={{ color: "#444", marginLeft: "6px" }}>Asking about</span>
                <div style={{ color: "#a0a0ff", fontWeight: 600, marginTop: "3px", wordBreak: "break-all" }}>
                  {activeDoc}
                </div>
              </>
            ) : (
              <span style={{ color: "#333" }}>Select a document above</span>
            )}
          </div>
        )}

      </div>

      {/* ── CHAT ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <ChatWindow messages={messages} isLoading={isLoading} />
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading || !canSend}
          placeholder={
            !uploadedFiles.length ? "Upload a document first..." :
            searchMode === "all"  ? "Ask across all documents..." :
            !activeDoc            ? "Select a document from the sidebar..." :
                                    `Ask about ${activeDoc}...`
          }
        />
      </div>

    </div>
  );
}