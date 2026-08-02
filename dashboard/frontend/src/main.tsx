import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";

import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
    <Toaster
      richColors
      closeButton
      position="top-right"
      toastOptions={{ style: { fontFamily: "Montserrat, sans-serif" } }}
    />
  </StrictMode>
);
