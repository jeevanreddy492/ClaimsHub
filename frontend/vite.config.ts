import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local dev, /api and /health go to the FastAPI app on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  test: { environment: "node" },
});
