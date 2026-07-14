// src/components/UploadZone.jsx

import { useState, useRef } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function UploadZone({ onUploadSuccess }) {
  const [status,    setStatus]    = useState(""); // loading / ok / error message
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef();

  const uploadFiles = async (files) => {
    const pdfs = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) {
      setStatus(" Please select PDF files only.");
      return;
    }

    setStatus("Uploading...");
    const uploadedNames = [];

    for (const file of pdfs) {
      try {
        const fd = new FormData();
        fd.append("file", file);

        const { data } = await axios.post(`${API}/upload`, fd);

        // Backend returns: { message, details: { file, chunks_created, characters } }
        const name = data.details?.file || file.name;
        uploadedNames.push(name);

      } catch (err) {
        console.error("Upload error:", err);
        setStatus(`❌ Failed to upload ${file.name}`);
        return;
      }
    }

    setStatus(`✅ ${uploadedNames.length} file(s) uploaded and indexed successfully!`);
    onUploadSuccess(uploadedNames); // pass filenames up to App.jsx
    if (inputRef.current) inputRef.current.value = "";
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    uploadFiles(e.dataTransfer.files);
  };

  return (
    <div style={{ padding: "16px", borderBottom: "1px solid #1f1f1f" }}>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        style={{
          border:       `1.5px dashed ${isDragging ? "#6366f1" : "#2a2a2a"}`,
          borderRadius: "8px",
          padding:      "20px 12px",
          textAlign:    "center",
          cursor:       "pointer",
          background:   isDragging ? "#12122a" : "#111",
          transition:   "all 0.2s",
        }}
      >
        <div style={{ fontSize: "22px", marginBottom: "6px" }}>📂</div>
        <div style={{ fontSize: "12px", color: "#555" }}>
          Drag & drop PDFs or <span style={{ color: "#6366f1", textDecoration: "underline" }}>click to browse</span>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple
        style={{ display: "none" }}
        onChange={(e) => uploadFiles(e.target.files)}
      />

 

    </div>
  );
}