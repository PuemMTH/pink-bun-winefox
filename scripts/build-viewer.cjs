const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const output = path.join(root, "dist/viewer");
fs.mkdirSync(output, { recursive: true });
fs.cpSync(path.join(root, "viewer"), output, { recursive: true });
const assets = path.join(output, "assets");
for (const [folder, destination, preview] of [
  ["pink_bun_winefox_square_eyes", assets, "preview.png"],
  ["pink_bun_winefox_white_square_eyes", path.join(assets, "white"), "preview-white.png"],
  ["satou_aunt", path.join(assets, "aunt")],
]) {
  const model = path.join(root, "dist", folder);
  if (!fs.existsSync(path.join(model, "ysm.json")))
    throw Error("Run npm run build first.");
  fs.mkdirSync(destination, { recursive: true });
  const read = (file) =>
    JSON.parse(fs.readFileSync(path.join(model, file), "utf8"));
  const write = (file, data) =>
    fs.writeFileSync(path.join(destination, file), JSON.stringify(data));
  const info = read("ysm.json");
  const player = info.files.player;
  write("info.json", info);
  write("model.json", read(player.model.main));
  write("animations.json", {
    animations: {
      ...read(player.animation.main).animations,
      ...read(player.animation.extra).animations,
    },
  });
  const choice = player.texture[0];
  fs.copyFileSync(
    path.join(model, typeof choice === "string" ? choice : choice.uv),
    path.join(destination, "texture.png"),
  );
  if (preview) {
    fs.copyFileSync(
      path.join(root, "docs", preview),
      path.join(destination, "preview.png"),
    );
  }
  fs.copyFileSync(
    path.join(model, "ATTRIBUTION.md"),
    path.join(destination, "ATTRIBUTION.md"),
  );
}
console.log(`Viewer built: ${output}`);
