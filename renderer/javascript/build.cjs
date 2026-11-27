const fs = require("node:fs"),
  path = require("node:path");
const root = path.resolve(__dirname, "../.."),
  out = path.join(root, "dist/javascript");
fs.mkdirSync(path.join(out, "core/lib"), { recursive: true });
for (const file of [
  "model.mjs",
  "animation.mjs",
  "photo-poses.mjs",
  "studio.mjs",
])
  fs.copyFileSync(
    path.join(root, "viewer", file),
    path.join(out, "core", file),
  );
for (const file of [
  "three.module.min.js",
  "three.core.min.js",
  "THREE-LICENSE.txt",
])
  fs.copyFileSync(
    path.join(root, "viewer/lib", file),
    path.join(out, "core/lib", file),
  );
for (const file of ["index.mjs", "README.md", "example.html"])
  fs.copyFileSync(path.join(__dirname, file), path.join(out, file));
fs.copyFileSync(path.join(root, "LICENSE"), path.join(out, "LICENSE"));
fs.writeFileSync(
  path.join(out, "package.json"),
  JSON.stringify(
    {
      name: "ysm-render-js",
      version: "0.1.0",
      type: "module",
      exports: "./index.mjs",
      license: "CC-BY-NC-SA-4.0",
      files: ["index.mjs", "core", "README.md", "LICENSE"],
    },
    null,
    2,
  ),
);
console.log(out);
