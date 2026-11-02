import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // 5173 is already used by the existing Knowledge Repository portal
    // (D:\AFC-Automation). The 5180-5220 range also turned out to have
    // other dev servers churning through it on this machine, so this picks
    // a port well outside any common dev-server range.
    port: 4521,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
