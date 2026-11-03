import "@fontsource-variable/inter";
import "@fontsource-variable/noto-sans-telugu"; // bundled: Telugu text without external font requests
import "./styles/tokens.css";
import "./styles/app.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
