import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Vite configuration.
 *
 * The browser must talk to the API on the SAME origin as the page. Cookies
 * (session + CSRF) are host-scoped; a different port is a different origin, so
 * `document.cookie` cannot read the CSRF token and `credentials: "same-origin"`
 * never attaches the session. Compose therefore leaves `VITE_SCHOOL_API_URL`
 * empty and sets `SCHOOL_API_PROXY_TARGET` so Vite proxies `/api` (and the
 * health probes) into the API container.
 *
 * The published frontend port still comes from the environment because
 * `scripts/dev.py up` allocates it dynamically.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@shared": path.resolve(import.meta.dirname, "src/shared"),
      "@features": path.resolve(import.meta.dirname, "src/features"),
      "@app": path.resolve(import.meta.dirname, "src/app"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: Number(process.env.SCHOOL_FRONTEND_PORT ?? 5173),
    strictPort: false,
    proxy: {
      "/api": {
        target: process.env.SCHOOL_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/healthz": {
        target: process.env.SCHOOL_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/readyz": {
        target: process.env.SCHOOL_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
