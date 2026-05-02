import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import fs from "node:fs";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.NANOBOT_API_URL ?? "http://127.0.0.1:8765";
  const wsTarget = target.replace(/^http/, "ws");
  const workspaceRoot = path.resolve(
    env.NANOBOT_WORKSPACE ?? path.join(process.env.HOME ?? "~", ".nanobot/workspace"),
  );

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    optimizeDeps: {
      // Radix dialog was introduced mid-session for the mobile sidebar sheet.
      // When Vite re-optimizes it on a running dev server, the browser can race
      // and request stale chunk paths from `.vite/deps`. Excluding it keeps dev
      // reloads stable instead of rewriting those chunk filenames under us.
      exclude: ["@radix-ui/react-dialog"],
    },
    build: {
      outDir: path.resolve(__dirname, "../nanobot/web/dist"),
      emptyOutDir: true,
      sourcemap: false,
    },
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      // Move Vite's HMR socket to a dedicated port so it doesn't collide with
      // the ``/`` proxy below (Vite HMR and the nanobot ws upgrade both sit on
      // the root path, which triggers spurious write-after-end errors as each
      // side tries to close the other's socket).
      hmr: {
        host: "127.0.0.1",
        port: 5174,
      },
      proxy: {
        "/webui": { target, changeOrigin: true },
        "/api": { target, changeOrigin: true },
        "/auth": { target, changeOrigin: true },
        // Forward only WebSocket upgrades on ``/`` to the nanobot gateway;
        // plain HTTP GETs on ``/`` must stay with Vite so it can serve the SPA.
        // ``bypass`` returning the original URL skips the proxy for that
        // request; returning undefined lets the proxy (and ws upgrade handler)
        // take it.
        "/": {
          target: wsTarget,
          ws: true,
          changeOrigin: true,
          bypass: (req) =>
            req.headers.upgrade === "websocket" ? undefined : req.url,
        },
      },
    },
    // Serve workspace files so the frontend can download generated documents
    // without relying on the agent to inline them as ---DOCUMENT: blocks.
    configureServer(server) {
      server.middlewares.use("/workspace-files/", (req, res) => {
        const relativePath = req.url!.slice("/workspace-files/".length);
        // Block path traversal attempts
        if (relativePath.includes("..") || relativePath.includes("~")) {
          res.statusCode = 403;
          res.end("forbidden");
          return;
        }
        const filePath = path.resolve(workspaceRoot, relativePath);
        if (!filePath.startsWith(workspaceRoot)) {
          res.statusCode = 403;
          res.end("forbidden");
          return;
        }
        try {
          const stat = fs.statSync(filePath);
          if (!stat.isFile()) {
            res.statusCode = 404;
            res.end("not found");
            return;
          }
          const content = fs.readFileSync(filePath, "utf-8");
          res.setHeader("Content-Type", "text/markdown; charset=utf-8");
          res.setHeader(
            "Content-Disposition",
            `attachment; filename="${encodeURIComponent(path.basename(filePath))}"`,
          );
          res.end(content);
        } catch {
          res.statusCode = 404;
          res.end("not found");
        }
      });
    },
    test: {
      environment: "happy-dom",
      globals: true,
      setupFiles: ["./src/tests/setup.ts"],
    },
  };
});
