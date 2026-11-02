import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const BACKEND = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1", // never expose the dev server on the network
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": BACKEND,
      "/ws": { target: BACKEND, ws: true },
    },
  },
  preview: { host: "127.0.0.1" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    coverage: { include: ["src/**"], exclude: ["src/main.tsx"] },
  },
});
