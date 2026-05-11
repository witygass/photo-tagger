import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Auth/drive/health have no conflicting frontend routes — always proxy
      "/auth": "http://127.0.0.1:8000",
      "/drive": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      // /people and /jobs have matching frontend routes, so bypass for browser
      // navigations (Accept: text/html) and let React Router handle them
      "/people": {
        target: "http://127.0.0.1:8000",
        bypass: (req) => {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
      "/jobs": {
        target: "http://127.0.0.1:8000",
        bypass: (req) => {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
    },
  },
});
