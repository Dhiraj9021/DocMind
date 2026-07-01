// src/components/ChatWindow.jsx

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import SourceCard from "./SourceCard";
import { Bot, User, Loader } from "lucide-react";

export default function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        color: "#444", textAlign: "center", padding: "40px"
      }}>
        <Bot size={48} color="#333" style={{ marginBottom: "16px" }} />
        <h2 style={{ fontSize: "20px", color: "#555", fontWeight: 500 }}>
          PaperBrain
        </h2>
        <p style={{ fontSize: "14px", marginTop: "8px", color: "#444" }}>
          Upload a PDF and ask anything about it
        </p>
        <div style={{ marginTop: "24px", display: "flex",
          flexDirection: "column", gap: "8px" }}>
          {[
            "What are the main topics covered?",
            "Summarise the key points",
            "What skills does this person have?"
          ].map((q, i) => (
            <div key={i} style={{
              padding: "8px 16px",
              background: "#1a1a1a",
              borderRadius: "20px",
              fontSize: "13px",
              color: "#555",
              border: "1px solid #222"
            }}>
              {q}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      flex: 1, overflowY: "auto",
      padding: "20px 16px", display: "flex",
      flexDirection: "column", gap: "20px"
    }}>
      {messages.map((msg, i) => (
        <div key={i} style={{
          display: "flex",
          flexDirection: msg.role === "user" ? "row-reverse" : "row",
          gap: "10px", alignItems: "flex-start"
        }}>

          {/* Avatar */}
          <div style={{
            width: "30px", height: "30px",
            borderRadius: "50%", flexShrink: 0,
            background: msg.role === "user" ? "#312e81" : "#1a1a1a",
            border: `1px solid ${msg.role === "user" ? "#4f46e5" : "#333"}`,
            display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            {msg.role === "user"
              ? <User size={14} color="#818cf8" />
              : <Bot size={14} color="#6366f1" />}
          </div>

          {/* Message bubble */}
          <div style={{ maxWidth: "75%", minWidth: "60px" }}>
            <div style={{
              background: msg.role === "user" ? "#1e1b4b" : "#1a1a1a",
              border: `1px solid ${msg.role === "user" ? "#312e81" : "#222"}`,
              borderRadius: msg.role === "user"
                ? "18px 4px 18px 18px"
                : "4px 18px 18px 18px",
              padding: "12px 16px",
              fontSize: "14px",
              lineHeight: "1.6",
              color: "#e5e5e5"
            }}>
              {msg.role === "assistant"
                ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                : msg.content
              }
            </div>

            {/* Source citations below assistant messages */}
            {msg.role === "assistant" && msg.sources?.length > 0 && (
              <div style={{ marginTop: "6px" }}>
                <span style={{
                  fontSize: "10px", color: "#555",
                  marginBottom: "4px", display: "block"
                }}>
                  Sources
                </span>
                {msg.sources.map((s, j) => (
                  <SourceCard key={j} source={s} />
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
          <div style={{
            width: "30px", height: "30px", borderRadius: "50%",
            background: "#1a1a1a", border: "1px solid #333",
            display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <Bot size={14} color="#6366f1" />
          </div>
          <div style={{
            background: "#1a1a1a", border: "1px solid #222",
            borderRadius: "4px 18px 18px 18px",
            padding: "12px 16px", display: "flex",
            alignItems: "center", gap: "8px"
          }}>
            <Loader size={14} color="#6366f1" />
            <span style={{ fontSize: "13px", color: "#555" }}>
              Thinking...
            </span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}