const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const root = path.resolve(__dirname, "..");
const configFile = path.join(root, "local.config.json");
const local = fs.existsSync(configFile)
  ? JSON.parse(fs.readFileSync(configFile, "utf8"))
  : {};
const supplied =
  process.argv[2] || process.env.YSM_CUSTOM_DIR || local.customDirectory;
if (!supplied)
  throw Error(
    "Set customDirectory in local.config.json, YSM_CUSTOM_DIR, or pass the custom directory as an argument.",
  );
const custom = path.resolve(supplied);
if (path.basename(custom) !== "custom" || !fs.statSync(custom).isDirectory())
  throw Error("Choose an existing yes_steve_model/custom directory.");
const source = path.join(root, "dist", "pink_bun_winefox");
const target = path.join(custom, "pink_bun_winefox");
if (fs.existsSync(target)) {
  const backup = path.join(
    root,
    "local-backups",
    `${new Date().toISOString().replace(/[:.]/g, "-")}-${randomUUID().slice(0, 8)}`,
  );
  fs.mkdirSync(path.dirname(backup), { recursive: true });
  fs.cpSync(target, backup, { recursive: true });
  console.log(`Previous model backed up to ${backup}`);
}
fs.cpSync(source, target, { recursive: true, force: true });
console.log(`Installed: ${target}\nIn Minecraft: /ysm model reload`);
