// src/components/SourceCard.jsx
// Shows citation cards below each answer

import { FileText, ExternalLink } from "lucide-react";

export default function SourceCard({ source }) {
  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "6px",
      padding: "4px 10px",
      background: "#1e1b4b",
      border: "1px solid #312e81",
      borderRadius: "20px",
      marginRight: "6px",
      marginTop: "6px",
      cursor: "default"
    }}>
      <FileText size={11} color="#818cf8" />
      <span style={{ fontSize: "11px", color: "#a5b4fc" }}>
        {source.file}
      </span>
      <span style={{
        fontSize: "10px",
        color: "#6366f1",
        background: "#312e81",
        padding: "1px 6px",
        borderRadius: "10px"
      }}>
        p.{source.page}
      </span>
      <span style={{ fontSize: "10px", color: "#4f46e5" }}>
        {Math.round(source.similarity * 100)}%
      </span>
    </div>
  );
}