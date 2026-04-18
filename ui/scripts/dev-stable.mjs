import { existsSync, rmSync } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";

const CACHE_PATHS = [
  path.join(".next", "cache", "turbopack"),
  path.join(".next", "server", "chunks"),
  path.join(".next", "static", "chunks"),
];

for (const cachePath of CACHE_PATHS) {
  if (existsSync(cachePath)) {
    rmSync(cachePath, { recursive: true, force: true });
  }
}

const nextBinary =
  process.platform === "win32"
    ? path.join("node_modules", ".bin", "next.cmd")
    : path.join("node_modules", ".bin", "next");

const child = spawn(nextBinary, ["dev", ...process.argv.slice(2)], {
  stdio: "inherit",
  shell: false,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
