const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const root = path.resolve(__dirname, "..");
const install = process.argv.includes("--install");
let timer;
function rebuild() {
  for (const script of [
    "src/build.cjs",
    "scripts/check.cjs",
    ...(install ? ["scripts/install.cjs"] : []),
  ]) {
    const result = spawnSync(process.execPath, [path.join(root, script)], {
      cwd: root,
      stdio: "inherit",
    });
    if (result.status !== 0) {
      console.error("Build stopped; fix the reported error and save again.");
      return;
    }
  }
  console.log(
    `Watching source/config changes${install ? "; game copy updated" : ""}. Ctrl+C to stop.`,
  );
}
for (const entry of ["src", "scripts", "vendor", "model.config.json"]) {
  fs.watch(
    path.join(root, entry),
    { recursive: entry !== "model.config.json" },
    () => {
      clearTimeout(timer);
      timer = setTimeout(rebuild, 200);
    },
  );
}
rebuild();
