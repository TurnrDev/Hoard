import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

const packageMetadata = JSON.parse(
  readFileSync(new URL("./package.json", import.meta.url), "utf8"),
) as { version: string };
const backendUrl = process.env.VITE_BACKEND_URL ?? "http://localhost:8000";

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
      "/api": backendUrl,
      "/media": backendUrl,
      "/release-manifest.json": backendUrl,
      "/ws": { target: backendUrl, ws: true },
    },
  },
});
