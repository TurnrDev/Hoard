import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";

// https://vite.dev/config/
export default defineConfig({
  base: "/static/",
  plugins: [vue(), vuetify({ autoImport: true })],
  build: { manifest: true, rollupOptions: { input: "src/main.ts" } },
  server: {
    origin: "http://localhost:5173",
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
