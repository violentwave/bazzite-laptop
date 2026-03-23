export default function({ project }) {
  return {
    "tool.execute.before": async ({ tool }) => {
      if (tool.name === "read" && tool.input?.path) {
        const blocked = [".env", "keys.env", ".pem", ".key", "bazzite-ai/keys"];
        if (blocked.some(pattern => tool.input.path.includes(pattern))) {
          throw new Error(`Blocked: reading secrets file ${tool.input.path}`);
        }
      }
    }
  };
}
