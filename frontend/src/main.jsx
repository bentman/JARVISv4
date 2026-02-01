import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

const initialResult = {
  taskId: "",
  state: "",
  error: ""
};

function App() {
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(initialResult);

  const canSubmit = useMemo(() => goal.trim().length > 0, [goal]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit || status === "submitting") {
      return;
    }

    setStatus("submitting");
    setResult(initialResult);

    try {
      const response = await fetch("/v1/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ goal: goal.trim() })
      });

      if (!response.ok) {
        let errorMessage = `Request failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (errorPayload?.detail) {
            errorMessage = errorPayload.detail;
          }
        } catch (parseError) {
          // Ignore JSON parse failures and fall back to status message.
        }
        setResult({ ...initialResult, error: errorMessage });
        setStatus("error");
        return;
      }

      const data = await response.json();
      setResult({
        taskId: data.task_id ?? "",
        state: data.state ?? "",
        error: data.error ?? ""
      });
      setStatus("success");
    } catch (error) {
      setResult({
        ...initialResult,
        error: error?.message ?? "Unexpected network error."
      });
      setStatus("error");
    }
  };

  return (
    <main
      style={{
        fontFamily: "system-ui",
        padding: "2rem",
        maxWidth: "640px",
        margin: "0 auto"
      }}
    >
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ marginBottom: "0.25rem" }}>JARVISv4 Task Submission</h1>
        <p style={{ margin: 0, color: "#444" }}>
          Submit a goal to start a task run.
        </p>
      </header>

      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <label
          htmlFor="goal"
          style={{ display: "block", fontWeight: 600, marginBottom: "0.5rem" }}
        >
          Goal
        </label>
        <textarea
          id="goal"
          name="goal"
          rows={3}
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="Describe the task goal..."
          style={{
            width: "100%",
            padding: "0.75rem",
            borderRadius: "6px",
            border: "1px solid #ccc",
            resize: "vertical",
            marginBottom: "0.75rem"
          }}
        />
        <button
          type="submit"
          disabled={!canSubmit || status === "submitting"}
          style={{
            padding: "0.65rem 1.25rem",
            borderRadius: "6px",
            border: "none",
            background: canSubmit && status !== "submitting" ? "#1f6feb" : "#94a3b8",
            color: "#fff",
            fontWeight: 600,
            cursor: canSubmit && status !== "submitting" ? "pointer" : "not-allowed"
          }}
        >
          {status === "submitting" ? "Submitting..." : "Submit Task"}
        </button>
      </form>

      <section
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "8px",
          padding: "1rem",
          background: "#f8fafc"
        }}
      >
        <h2 style={{ marginTop: 0 }}>Response</h2>
        {status === "idle" && <p>Awaiting submission.</p>}
        {status === "submitting" && <p>Submitting to backend...</p>}
        {status === "success" && (
          <div>
            <p>
              <strong>Task ID:</strong> {result.taskId || "(none)"}
            </p>
            <p>
              <strong>State:</strong> {result.state || "(none)"}
            </p>
            {result.error && (
              <p style={{ color: "#b91c1c" }}>
                <strong>Error:</strong> {result.error}
              </p>
            )}
          </div>
        )}
        {status === "error" && (
          <p style={{ color: "#b91c1c" }}>
            {result.error || "Unable to submit task."}
          </p>
        )}
      </section>
    </main>
  );
}

const root = createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
