import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Vite configuration.
 *
 * The dev server port and the API base URL both come from the environment,
 * because `scripts/dev.py up` allocates host ports dynamically so that two
 * modules can run at once. Hardcoding 5173 would defeat that.
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
    host: "127.0.0.1",
    port: Number(process.env.SCHOOL_FRONTEND_PORT ?? 5173),
    strictPort: false,
  },
});
