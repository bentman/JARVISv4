import React from "react";
import { createRoot } from "react-dom/client";

const root = createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>JARVISv4 UI</h1>
      <p>Frontend container substrate ready.</p>
    </main>
  </React.StrictMode>
);
