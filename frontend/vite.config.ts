import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/people": "http://127.0.0.1:8000",
      "/drive": "http://127.0.0.1:8000",
      "/jobs": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
