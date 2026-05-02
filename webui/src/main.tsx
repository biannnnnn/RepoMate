import React from "react";
import ReactDOM from "react-dom/client";

import { TooltipProvider } from "@/components/ui/tooltip";
import App from "./App";
import "./globals.css";
import "./i18n";

const root = document.getElementById("root");
if (!root) throw new Error("root element missing");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <TooltipProvider delayDuration={300}>
      <App />
    </TooltipProvider>
  </React.StrictMode>,
);
