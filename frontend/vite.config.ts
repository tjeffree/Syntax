import { defineConfig } from "vite";

// Relative base so the built app works under any hosting path (Firebase Hosting
// serves at root, but this keeps `vite preview` and sub-path hosting happy).
export default defineConfig({
  base: "./",
  build: {
    target: "es2020",
    sourcemap: true,
  },
  server: {
    port: 5173,
  },
});
