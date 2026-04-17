import { useEffect, useMemo, useRef, useState } from "react";

function createThreadId() {
  const random = Math.random().toString(36).slice(2, 10);
  return `thread-${random}`;
}

function resolveApiBase() {
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase) {
    return envBase.replace(/\/$/, "");
  }

  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
}

function providerNameFromFile(file) {
  const baseName = (file?.name || "").replace(/\.pdf$/i, "").trim();
  return baseName || "proveedor_sin_nombre";
}

function formatUploadResponse(payload) {
  const base = payload?.message || "Archivo cargado correctamente.";
  const providers = Array.isArray(payload?.providers_detected) ? payload.providers_detected : [];
  if (!providers.length) {
    return base;
  }
  return `${base} Proveedores detectados: ${providers.join(", ")}.`;
}

export default function App() {
  const apiBase = useMemo(() => resolveApiBase(), []);
  const threadId = useMemo(() => createThreadId(), []);

  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isSending, setIsSending] = useState(false);

  const fileInputRef = useRef(null);
  const textAreaRef = useRef(null);
  const chatLogRef = useRef(null);

  useEffect(() => {
    if (!textAreaRef.current) {
      return;
    }
    textAreaRef.current.style.height = "auto";
    const nextHeight = Math.min(textAreaRef.current.scrollHeight, 140);
    textAreaRef.current.style.height = `${nextHeight}px`;
  }, [text]);

  useEffect(() => {
    if (!chatLogRef.current) {
      return;
    }
    chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
  }, [messages]);

  function appendMessage(role, content) {
    setMessages((prev) => [...prev, { role, content }]);
  }

  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("thread_id", threadId);
    formData.append("provider_name", providerNameFromFile(file));
    formData.append("file", file);

    const response = await fetch(`${apiBase}/upload`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail || `Error ${response.status} al subir archivo.`);
    }

    return formatUploadResponse(payload);
  }

  async function sendChatMessage(message) {
    const response = await fetch(`${apiBase}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        thread_id: threadId,
        message,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail || `Error ${response.status} en chat.`);
    }

    if (typeof payload?.response === "string" && payload.response.trim()) {
      return payload.response;
    }

    return JSON.stringify(payload, null, 2);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSending) {
      return;
    }

    const trimmed = text.trim();
    if (!trimmed && !selectedFile) {
      return;
    }

    setIsSending(true);
    try {
      if (selectedFile) {
        appendMessage("user", `[Archivo] ${selectedFile.name}`);
        const uploadResult = await uploadFile(selectedFile);
        appendMessage("assistant", uploadResult);
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }

      if (trimmed) {
        appendMessage("user", trimmed);
        setText("");
        const reply = await sendChatMessage(trimmed);
        appendMessage("assistant", reply);
      }
    } catch (error) {
      appendMessage("assistant", `Error: ${error?.message || String(error)}`);
    } finally {
      setIsSending(false);
      if (textAreaRef.current) {
        textAreaRef.current.focus();
      }
    }
  }

  function onFileChange(event) {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
  }

  function onMessageKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Evalify AI</h1>
      </header>

      <main ref={chatLogRef} className="chat-log" aria-live="polite">
        {messages.length === 0 ? <p className="chat-empty" /> : null}
        {messages.map((item, index) => (
          <article key={`${item.role}-${index}`} className={`message ${item.role}`}>
            <p className="message-role">{item.role === "user" ? "Tu" : "Evalify"}</p>
            <p className="message-content">{item.content}</p>
          </article>
        ))}
      </main>

      <form className="composer" onSubmit={handleSubmit}>
        <div className="composer-tools">
          <label className="file-button" htmlFor="fileInput">
            Cargar archivo PDF
          </label>
          <input
            ref={fileInputRef}
            id="fileInput"
            type="file"
            accept="application/pdf"
            onChange={onFileChange}
            disabled={isSending}
          />
          <span className="file-name">{selectedFile ? selectedFile.name : ""}</span>
        </div>

        <div className="composer-row">
          <textarea
            ref={textAreaRef}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={onMessageKeyDown}
            placeholder="Escribe tu mensaje"
            rows={1}
            disabled={isSending}
          />
          <button type="submit" disabled={isSending}>
            {isSending ? "Enviando..." : "Enviar"}
          </button>
        </div>
      </form>
    </div>
  );
}
