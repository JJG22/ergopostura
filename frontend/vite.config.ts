import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En desarrollo la app vive en /app/ y Vite reenvía /api/ a Django.
// Al compilar, los archivos se publican como estáticos de Django bajo /static/app/.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/app/" : "/app/",
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: { "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000" } },
    // La carpeta del proyecto está en OneDrive: el sondeo detecta los cambios de forma fiable.
    watch: { usePolling: true, interval: 300 },
  },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
}));
