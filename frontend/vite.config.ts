import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf("recharts") >= 0 || id.indexOf("d3-") >= 0) return "charts";
          if (id.indexOf("@xyflow") >= 0 || id.indexOf("dagre") >= 0) return "graph";
          if (id.indexOf("node_modules") >= 0) return "vendor";
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  preview: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
