// src/components/UploadZone.jsx

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { Upload, FileText, CheckCircle, Loader } from "lucide-react";

export default function UploadZone({ onUploadSuccess }) {
  const [status, setStatus]   = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const [files, setFiles]     = useState([]);

  const onDrop = useCallback(async (acceptedFiles) => {
    const pdfFiles = acceptedFiles.filter(f => f.name.endsWith(".pdf"));

    if (pdfFiles.length === 0) {
      setStatus("error");
      setMessage("Please upload PDF files only.");
      return;
    }

    setStatus("uploading");
    setFiles(pdfFiles.map(f => f.name));

    let successCount = 0;

    for (const file of pdfFiles) {
      try {
        const formData = new FormData();
        formData.append("file", file);

        await axios.post("http://localhost:8000/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });

        successCount++;
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err);
      }
    }

    if (successCount === pdfFiles.length) {
      setStatus("done");
      setMessage(`${successCount} file(s) uploaded and indexed successfully!`);
      onUploadSuccess(pdfFiles.map(f => f.name));
    } else {
      setStatus("error");
      setMessage(`${successCount}/${pdfFiles.length} files uploaded.`);
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true
  });

  return (
    <div style={{ padding: "16px" }}>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        style={{
          border: `2px dashed ${isDragActive ? "#6366f1" : "#333"}`,
          borderRadius: "12px",
          padding: "28px 20px",
          textAlign: "center",
          cursor: "pointer",
          background: isDragActive ? "#1e1b4b" : "#1a1a1a",
          transition: "all 0.2s"
        }}
      >
        <input {...getInputProps()} />
        <Upload size={28} color={isDragActive ? "#6366f1" : "#555"}
          style={{ margin: "0 auto 10px" }} />
        <p style={{ color: "#aaa", fontSize: "13px" }}>
          {isDragActive
            ? "Drop your PDFs here..."
            : "Drag & drop PDFs or click to browse"}
        </p>
      </div>

      {/* Status message */}
      {status === "uploading" && (
        <div style={{ display: "flex", alignItems: "center",
          gap: "8px", marginTop: "12px", color: "#6366f1" }}>
          <Loader size={14} className="spin" />
          <span style={{ fontSize: "13px" }}>
            Indexing {files.join(", ")}...
          </span>
        </div>
      )}

      {status === "done" && (
        <div style={{ display: "flex", alignItems: "center",
          gap: "8px", marginTop: "12px", color: "#22c55e" }}>
          <CheckCircle size={14} />
          <span style={{ fontSize: "13px" }}>{message}</span>
        </div>
      )}

      {status === "error" && (
        <p style={{ color: "#ef4444", fontSize: "13px", marginTop: "12px" }}>
          {message}
        </p>
      )}

      {/* Uploaded files list */}
      {files.length > 0 && status === "done" && (
        <div style={{ marginTop: "12px" }}>
          {files.map((name, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: "8px",
              padding: "6px 10px", background: "#1a1a1a",
              borderRadius: "8px", marginBottom: "4px"
            }}>
              <FileText size={13} color="#6366f1" />
              <span style={{ fontSize: "12px", color: "#aaa" }}>{name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}