const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const model = path.join(root, "dist/pink_bun_winefox");
const output = path.join(root, "dist/viewer");
if (!fs.existsSync(path.join(model, "ysm.json")))
  throw Error("Run npm run build first.");
fs.mkdirSync(output, { recursive: true });
fs.cpSync(path.join(root, "viewer"), output, { recursive: true });
const assets = path.join(output, "assets");
fs.mkdirSync(assets, { recursive: true });
for (const [source, destination] of [
  ["models/main.json", "model.json"],
  ["animations/main.animation.json", "animations.json"],
  ["ysm.json", "info.json"],
])
  fs.writeFileSync(
    path.join(assets, destination),
    JSON.stringify(
      JSON.parse(fs.readFileSync(path.join(model, source), "utf8")),
    ),
  );
fs.copyFileSync(
  path.join(model, "textures/pink_bun.png"),
  path.join(assets, "texture.png"),
);
fs.copyFileSync(
  path.join(root, "docs/preview.png"),
  path.join(assets, "preview.png"),
);
fs.copyFileSync(
  path.join(root, "ATTRIBUTION.md"),
  path.join(assets, "ATTRIBUTION.md"),
);
console.log(`Viewer built: ${output}`);
