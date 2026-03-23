export default function({ project }) {
  const BLOCKED_PATTERNS = [
    /rm\s+-rf/,
    /git\s+reset\s+--hard/,
    /systemctl\s+(enable|disable|stop|start|restart|mask)/,
    /rpm-ostree\s+(install|remove|upgrade|rebase|override)/,
  ];

  const BLOCKED_WRITE_PATHS = ["/usr/", "/etc/", "/boot/", "/ostree/"];

  return {
    "tool.execute.before": async ({ tool }) => {
      // Block dangerous shell commands
      if ((tool.name === "bash" || tool.name === "run") && tool.input?.command) {
        const cmd = tool.input.command;
        for (const pattern of BLOCKED_PATTERNS) {
          if (pattern.test(cmd)) {
            throw new Error(
              `Blocked destructive command: ${pattern} matched in: ${cmd}`
            );
          }
        }
      }

      // Block writes to system paths
      if (tool.name === "write" && tool.input?.path) {
        const path = tool.input.path;
        for (const blocked of BLOCKED_WRITE_PATHS) {
          if (path.startsWith(blocked)) {
            throw new Error(
              `Blocked write to system path: ${path} (blocked prefix: ${blocked})`
            );
          }
        }
      }
    }
  };
}
