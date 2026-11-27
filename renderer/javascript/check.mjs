import assert from "node:assert/strict";
import fs from "node:fs";
import * as THREE from "../../dist/javascript/core/lib/three.module.min.js";
import {
  loadModel,
  applyPose,
  evaluate,
} from "../../dist/javascript/index.mjs";
const root = new URL("../../dist/pink_bun_winefox/", import.meta.url);
const json = (file) => JSON.parse(fs.readFileSync(new URL(file, root), "utf8"));
const input = {
  geometry: json("models/main.json"),
  animations: json("animations/main.animation.json"),
  info: json("ysm.json"),
  texture: new THREE.Texture(),
};
const model = await loadModel(input);
assert.equal(
  model.stats.cubes,
  input.geometry["minecraft:geometry"][0].bones.reduce(
    (n, b) =>
      n + (b.cubes || []).filter((c) => c.origin && c.size && c.uv).length,
    0,
  ),
);
assert.notEqual(model.root.children.length, 0);
assert.equal(model.root.scale.y, 0.7);
assert.equal(evaluate("math.sin(90)"), 1);
applyPose(model, { animation: "run", time: 0.2 });
assert.equal(model.bones.get("CustomRunIrisLeft").group.scale.x, 1);
applyPose(model, { animation: "studio_photo_cheeks" });
assert.equal(model.bones.get("CustomRunIrisLeft").group.scale.x, 0);
applyPose(model, {
  animation: "idle",
  boneOverrides: { Head: { rotation: [0, -15, 5] } },
});
assert(
  Math.abs(model.bones.get("Head").group.rotation.y - Math.PI / 12) < 1e-8,
);
applyPose(model, { animation: "idle" });
assert(Math.abs(model.bones.get("Head").group.rotation.y) < 1e-10);
assert.throws(
  () => applyPose(model, { animation: "missing" }),
  /Unknown animation/,
);
assert.throws(
  () =>
    applyPose(model, { boneOverrides: { Missing: { rotation: [0, 0, 0] } } }),
  /Unknown bone/,
);
assert.equal(
  input.texture.magFilter,
  THREE.LinearFilter,
  "Caller texture must not be modified",
);
model.dispose();
console.log(
  "JS core: portable import, pose reset, overrides, photo poses and input ownership passed",
);
