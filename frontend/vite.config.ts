import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Load environment variables based on the current mode (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), "");

  // Safely fallback if the variable is not set
  const backendTarget = env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

  return {
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
  };
});
