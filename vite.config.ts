import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

const packageMetadata = JSON.parse(
  readFileSync(new URL("./package.json", import.meta.url), "utf8"),
) as { version: string };

// https://vite.dev/config/
export default defineConfig({
  base: "/static/",
  define: {
    __HOARD_VERSION__: JSON.stringify(packageMetadata.version),
  },
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./hoard", import.meta.url)),
    },
  },
  publicDir: "hoard/public",
  build: {
    outDir: "hoard/dist",
    manifest: true,
    rollupOptions: { input: "hoard/main.ts" },
  },
  server: {
    origin: "http://localhost:5173",
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
