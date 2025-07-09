
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import { waitForApp } from "./utils/comfyapp.ts";
import "./scoped-tailwind.css";
import { app } from "./utils/comfyapp";
import "./fonts.css";

const App = React.lazy(() =>
  import("./App.tsx").then(({ default: App }) => ({
    default: App,
  })),
);

function waitForDocumentBody() {
  return new Promise((resolve) => {
    if (document.body) {
      return resolve(document.body);
    }

    document.addEventListener("DOMContentLoaded", () => {
      resolve(document.body);
    });
  });
}

waitForDocumentBody()
  .then(() => waitForApp())
  .then(() => {
    app.extensionManager.registerSidebarTab({
      id: "comfyui-copilot",
      icon: "cc-icon-logo",
      title: "ComfyUI Copilot",
      tooltip: "ComfyUI Copilot",
      type: "custom",
      render: (el: HTMLElement) => {
        const container = document.createElement("div");
        container.id = "comfyui-copilot-plugin";
        container.className = "h-full w-full flex flex-col";
        el.style.height = "100%";
        el.appendChild(container);
        ReactDOM.createRoot(container).render(
          <React.StrictMode>
            <Suspense fallback={<div className="h-full w-full flex items-center justify-center">Loading...</div>}>
              <App />
            </Suspense>
          </React.StrictMode>,
        );
      },
    });
  })
  // .then(() => {
  //   app.extensionManager.setting.set('Comfy.Sidebar.Location', 'left');
  // })
  ;
