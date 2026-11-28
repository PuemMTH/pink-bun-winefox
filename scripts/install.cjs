const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const { parseArgs } = require("node:util");
const { values, positionals } = parseArgs({
  options: { "square-eyes": { type: "boolean" } },
  allowPositionals: true,
});
const root = path.resolve(__dirname, "..");
const configFile = path.join(root, "local.config.json");
const local = fs.existsSync(configFile)
  ? JSON.parse(fs.readFileSync(configFile, "utf8"))
  : {};
const supplied =
  positionals[0] || process.env.YSM_CUSTOM_DIR || local.customDirectory;
if (!supplied)
  throw Error(
    "Set customDirectory in local.config.json, YSM_CUSTOM_DIR, or pass the custom directory as an argument.",
  );
const custom = path.resolve(supplied);
if (path.basename(custom) !== "custom" || !fs.statSync(custom).isDirectory())
  throw Error("Choose an existing yes_steve_model/custom directory.");
const models = [
  "pink_bun_winefox_square_eyes",
  "pink_bun_winefox_white_square_eyes",
];
if (!values["square-eyes"]) models.push("satou_aunt");
const legacySkin = path.join("textures", "skin.png");
const build = path.join(root, "dist");
for (const name of models) fs.accessSync(path.join(build, name, "ysm.json"));
const backup = path.join(
  root,
  "local-backups",
  `${new Date().toISOString().replace(/[:.]/g, "-")}-${randomUUID().slice(0, 8)}`,
);
for (const name of models) {
  const target = path.join(custom, name);
  const source = path.join(build, name);
  if (fs.existsSync(target)) {
    const previous = path.join(backup, name);
    fs.mkdirSync(backup, { recursive: true });
    fs.cpSync(target, previous, { recursive: true });
    console.log(`Previous model backed up to ${previous}`);
  }
  fs.cpSync(source, target, { recursive: true, force: true });
  // Remove an old copy of the vendor skin when the build no longer includes it.
  if (!fs.existsSync(path.join(source, legacySkin)))
    fs.rmSync(path.join(target, legacySkin), { force: true });
  console.log(`Installed: ${target}`);
}
console.log("In Minecraft: /ysm model reload");
