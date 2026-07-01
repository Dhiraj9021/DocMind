// src/components/ChatInput.jsx

import { useState } from "react";
import { Send } from "lucide-react";

export default function ChatInput({ onSend, isLoading }) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (!value.trim() || isLoading) return;
    onSend(value.trim());
    setValue("");
  };

  const handleKey = (e) => {
    // Send on Enter, new line on Shift+Enter
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      padding: "12px 16px",
      borderTop: "1px solid #1f1f1f",
      background: "#0f0f0f"
    }}>
      <div style={{
        display: "flex", gap: "8px", alignItems: "flex-end",
        background: "#1a1a1a", border: "1px solid #2a2a2a",
        borderRadius: "12px", padding: "8px 8px 8px 16px"
      }}>
        <textarea
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask anything about your documents..."
          rows={1}
          disabled={isLoading}
          style={{
            flex: 1, background: "transparent", border: "none",
            outline: "none", color: "#e5e5e5", fontSize: "14px",
            resize: "none", fontFamily: "inherit", lineHeight: "1.5",
            maxHeight: "120px", overflowY: "auto"
          }}
        />
        <button
          onClick={handleSend}
          disabled={!value.trim() || isLoading}
          style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: value.trim() && !isLoading ? "#6366f1" : "#222",
            border: "none", cursor: value.trim() ? "pointer" : "default",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "background 0.2s", flexShrink: 0
          }}
        >
          <Send size={14} color={value.trim() && !isLoading ? "#fff" : "#444"} />
        </button>
      </div>
      <p style={{
        fontSize: "10px", color: "#333", textAlign: "center", marginTop: "6px"
      }}>
        Answers are based only on your uploaded documents
      </p>
    </div>
  );
}