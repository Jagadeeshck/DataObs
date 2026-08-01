import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import { initializeObservability, startupEvent } from "./observability";
import "./styles/global.css";

void initializeObservability();
startupEvent("react.root.create");
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
