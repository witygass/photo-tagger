import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Auth/drive/health have no conflicting frontend routes — always proxy
      "/auth": backendTarget,
      "/drive": backendTarget,
      "/health": backendTarget,
      // /people and /jobs have matching frontend routes, so bypass for browser
      // navigations (Accept: text/html) and let React Router handle them
      "/people": {
        target: backendTarget,
        bypass: (req) => {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
      "/jobs": {
        target: backendTarget,
        bypass: (req) => {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
    },
  },
});
