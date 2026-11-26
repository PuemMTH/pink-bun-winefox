const fs = require("node:fs"),
  path = require("node:path"),
  zlib = require("node:zlib"),
  assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const config = JSON.parse(
  fs.readFileSync(path.join(root, "model.config.json"), "utf8"),
);
const base = path.join(root, "vendor/winefox-jk");
const out = path.join(root, "dist/pink_bun_winefox");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.mkdirSync(path.join(root, "docs"), { recursive: true });
if (!fs.existsSync(out)) fs.cpSync(base, out, { recursive: true });
const read = (p) => JSON.parse(fs.readFileSync(path.join(base, p), "utf8"));
const geo = read("models/main.json"),
  bones = geo["minecraft:geometry"][0].bones,
  by = Object.fromEntries(bones.map((b) => [b.name, b]));
const png = require("../scripts/png.cjs");
const source = png.read(path.join(base, "textures/skin.png")).pixels;
const materials = config.colors;
const nativeMaterials = require("./material-atlas.cjs")(source, materials),
  { W, H } = nativeMaterials;
let atlas;
function mat(name) {
  return nativeMaterials.swatch(name);
}
function recolor(q, c) {
  nativeMaterials.remap(q, c);
}
function add(b, o, s, c, rot, pivot) {
  const q = { origin: o, size: s };
  recolor(q, c);
  if (rot) {
    q.rotation = rot;
    q.pivot = pivot || o.map((n, i) => n + s[i] / 2);
  }
  (by[b].cubes ??= []).push(q);
  return q;
}
function ancestor(b, name) {
  for (let q = b; q; q = by[q.parent]) if (q.name === name) return true;
  return false;
}
const hidden = ["Ear", "flower", "hat", "MTail"];
let removed = 0,
  retained = 0;
for (const b of bones) {
  if (hidden.some((n) => ancestor(b, n))) {
    removed += b.cubes?.length || 0;
    delete b.cubes;
    continue;
  }
  for (const q of b.cubes || []) {
    retained++;
    if (ancestor(b, "Hair"))
      recolor(q, /Long/.test(b.name) ? "pinkshadow" : "pink");
    if (/^bow/.test(b.name)) recolor(q, "red");
    if (b.name === "jk" || b.name === "jk2") recolor(q, "navy");
    if (ancestor(b, "cloth")) recolor(q, "green");
    if (/^(Left|Right)Arm$/.test(b.name)) recolor(q, "navy");
    if (/^(Left|Right)ForeArm$/.test(b.name) && q.origin) {
      if (q.origin[1] > 18.8) recolor(q, "navy");
      else if (q.origin[1] > 16.8) recolor(q, "white");
    }
    if (/LowerLeg$/.test(b.name)) recolor(q, "sock");
    if (/Foot$/.test(b.name)) recolor(q, q.origin?.[1] < 0.8 ? "dark" : "shoe");
    if (/EyePublic$/.test(b.name)) recolor(q, "iris");
    else if (ancestor(b, "Eyes"))
      for (const [face, u] of Object.entries(q.uv || {})) {
        const x = Math.max(
            0,
            Math.min(255, Math.floor(u.uv[0] + (u.uv_size?.[0] || 0) / 2)),
          ),
          y = Math.max(
            0,
            Math.min(255, Math.floor(u.uv[1] + (u.uv_size?.[1] || 0) / 2)),
          ),
          i = (y * 256 + x) * 4;
        if (
          source[i] > source[i + 1] * 1.2 &&
          source[i + 1] > source[i + 2] * 1.4
        )
          q.uv[face] = mat("iris");
      }
  }
}
// The New Year/Hanfu Wine Fox crowns use a few stepped solids. Reuse that construction
// from the JK crown, mirrored into a bun; retain the JK UVs and its original hair shading.
const crown = read("models/main.json")
  ["minecraft:geometry"][0].bones.find((b) => b.name === "BaseHair")
  .cubes.filter((q) => q.origin[1] >= 38.9);
for (const s of [-1, 1]) {
  const name = s < 0 ? "CustomBunRight" : "CustomBunLeft",
    center = [s * 4.9, 39.8, 0.5];
  const b = { name, parent: "Head", pivot: center, cubes: [] };
  bones.push(b);
  by[name] = b;
  for (const upper of [true, false])
    for (const original of crown) {
      const q = structuredClone(original),
        dy = (q.origin[1] - 38.95) * 0.55,
        h = q.size[1] * 0.55;
      const bigger = config.bunScale;
      q.origin = [
        center[0] + q.origin[0] * 0.36 * bigger,
        center[1] + (upper ? dy : -dy - h) * bigger,
        center[2] + (q.origin[2] - 0.2) * 0.36 * bigger,
      ];
      q.size = [
        q.size[0] * 0.36 * bigger,
        h * bigger,
        q.size[2] * 0.36 * bigger,
      ];
      delete q.rotation;
      delete q.pivot;
      recolor(q, "pink");
      b.cubes.push(q);
    }
}
// A checked red side ribbon with a lace edge replaces the fox accessories.
for (let j = 0; j < 7; j++)
  add(
    "Head",
    [4.5, 37.3 + j * 0.38, -0.75],
    [0.38, 0.32, 1.65],
    "white",
    [0, 0, -12],
  );
add("Head", [4.65, 33.1, -0.9], [1.05, 5.3, 0.35], "red", [0, 0, -10]);
add("Head", [4.8, 32.9, -0.94], [0.12, 5.5, 0.1], "white", [0, 0, -10]);
// Vest, collars, piping and gold buttons are fitted over the original school jacket.
add("jk", [-2.3, 20.5, -2.45], [4.6, 8.2, 0.24], "vest");
for (const s of [-1, 1]) {
  add("jk", [s < 0 ? -2.75 : 2.35, 20.1, -2.55], [0.4, 8.9, 0.2], "gold", [
    0,
    0,
    s * 5,
  ]);
  add("jk", [s < 0 ? -3.05 : 2.85, 20, -2.56], [0.18, 9.2, 0.18], "white", [
    0,
    0,
    s * 5,
  ]);
  add("jk", [s < 0 ? -2.1 : 0.1, 28.7, -2.54], [2, 1.1, 0.3], "white", [
    0,
    0,
    s * 18,
  ]);
}
for (const y of [21.8, 24.7])
  add("jk", [-0.22, y, -2.76], [0.44, 0.44, 0.15], "gold");
// Preserve the original animated bow but widen the loops to match the reference.
for (const n of ["bowL", "bowR"])
  for (const q of by[n].cubes || []) {
    q.size[0] *= 1.3;
    q.origin[0] *= 1.15;
  }
// The added vest projects in front of the original JK shirt. Move the entire bow
// assembly, including all rotation pivots, so its animated loops clear the vest.
for (const b of bones)
  if (ancestor(b, "bow")) {
    b.pivot[2] -= config.bowForwardOffset;
    for (const q of b.cubes || []) {
      q.origin[2] -= config.bowForwardOffset;
      if (q.pivot) q.pivot[2] -= config.bowForwardOffset;
    }
  }
add("Hair", [-0.2, 41.3, 0], [0.35, 1.7, 0.4], "pink", [0, 0, 18]);
add("Hair", [-0.2, 42.7, 0], [1, 0.3, 0.4], "pink", [0, 0, -15]);
require("./skirt-fix.cjs")(
  geo,
  Object.fromEntries(
    ["north", "east", "south", "west", "up", "down"].map((f) => [
      f,
      mat("green"),
    ]),
  ),
);
by.CustomSkirtLining = bones.find((b) => b.name === "CustomSkirtLining");
const runFace = require("./run-face.cjs")(
  geo,
  read("animations/main.animation.json"),
  add,
  mat,
);
by.CustomRunFace = runFace.face;
for (const b of runFace.irises) by[b.name] = b;
const write = (p, v) =>
  fs.writeFileSync(path.join(out, p), JSON.stringify(v, null, 2));
Object.assign(geo["minecraft:geometry"][0].description, {
  identifier: "geometry.pink_bun_winefox",
  texture_width: W,
  texture_height: H,
});
write("models/main.json", geo);
write("animations/main.animation.json", runFace.animations);
// Arm assets use the identical material mapping while retaining their original rig.
const arm = read("models/arm.json");
for (const g of arm["minecraft:geometry"]) {
  g.description.texture_width = W;
  g.description.texture_height = H;
  for (const b of g.bones)
    for (const q of b.cubes || [])
      if (q.origin && q.origin[1] > 17)
        recolor(q, q.origin[1] < 19 ? "white" : "navy");
}
write("models/arm.json", arm);
const meta = read("ysm.json");
meta.metadata.name = config.name;
meta.metadata.tips =
  "School-uniform character adapted from Wine Fox 07_jk. Pink twin buns, red ribbon, navy blazer, green skirt. Original Wine Fox face, rig and animations.";
meta.metadata.authors.push({
  name: "Custom reference adaptation",
  role: "Geometry and UV material changes",
  comment:
    "Modified Wine Fox 07_jk for the supplied character references. Original authors and license retained.",
});
meta.properties.default_texture = "pink_bun";
meta.files.player.texture = ["textures/pink_bun.png"];
write("ysm.json", meta);
const materialResult = nativeMaterials.finish();
atlas = materialResult.pixels;
runFace.paint(atlas, W);
for (let y = 0; y < 256; y++)
  assert(
    atlas
      .subarray(y * W * 4, y * W * 4 + 256 * 4)
      .equals(source.subarray(y * 256 * 4, (y + 1) * 256 * 4)),
    "Original face/skin texels changed",
  );
const vestUv = mat("vest").uv,
  vestLeft = ((vestUv[1] + 30) * W + vestUv[0]) * 4,
  vestCenter = vestLeft + 9 * 4;
assert(
  !atlas
    .subarray(vestLeft, vestLeft + 3)
    .equals(atlas.subarray(vestCenter, vestCenter + 3)),
  "Vest must have lateral fabric shading",
);
fs.writeFileSync(
  path.join(root, "dist/material-shading.json"),
  JSON.stringify(materialResult.references, null, 2),
);
fs.writeFileSync(
  path.join(out, "ADAPTATION.txt"),
  "Base: YSM builtin Wine Fox / 07_jk.\nOriginal authors, author links and CC BY-NC-SA 4.0 license preserved in ysm.json.\nLicense: https://creativecommons.org/licenses/by-nc-sa/4.0/\nChanges: removed fox ears, tail, flower and hat geometry; added twin buns and side ribbon; remapped hair, eyes, school uniform, socks and shoes to new procedural material tiles; added waistcoat and lapel details.\nOriginal face and skin texture pixels are packed unchanged beside the new material tiles. Original skeleton, expressions and animations are retained.\nCharacter likeness follows user-supplied references; character rights remain with their respective owners.\n",
);
fs.appendFileSync(
  path.join(out, "ADAPTATION.txt"),
  "Revision: native JK material luminance patterns remapped to the pink/navy/green palette; skirt attached to hip rig; concealed upper thighs tapered and cropped with preserved visible UV density; continuous inner skirt lining added to cover pleat seams.\n",
);
fs.appendFileSync(
  path.join(out, "ADAPTATION.txt"),
  "Revision: replaced dense bun surfaces with mirrored JK crown solids, following the stepped construction also present in New Year and Hanfu Wine Fox; added stepped fabric shading, bow shadow, side folds and center seam to the original brown vest palette.\n",
);
fs.appendFileSync(
  path.join(out, "ADAPTATION.txt"),
  "Revision: buns enlarged by 15 percent with unchanged part count; sprint locomotion uses custom red spiral eyes and a small neutral mouth, returning to normal facial geometry in other main states.\n",
);
fs.appendFileSync(
  path.join(out, "ADAPTATION.txt"),
  "Revision: bow geometry and every bow pivot moved 1.5 model units forward to clear the added vest during animation.\n",
);
// Previews are independent of the game installation; they do not mutate model files.
png.write(path.join(out, "textures/pink_bun.png"), W, H, atlas);
const preview = require("../scripts/preview.cjs");
preview(geo, atlas, W, H, path.join(root, "docs/preview.png"), false);
preview(geo, atlas, W, H, path.join(root, "docs/preview-run-face.png"), true);
// Validate real output, not the temporary preview representation.
const written = JSON.parse(
  fs.readFileSync(path.join(out, "models/main.json"), "utf8"),
);
for (const b of written["minecraft:geometry"][0].bones) {
  if (b.parent) assert(by[b.parent], b.name);
  for (const q of b.cubes || []) {
    assert(q.size.every(Number.isFinite));
    for (const u of Object.values(q.uv || {})) {
      for (let k = 0; k < 2; k++)
        assert(u.uv[k] >= 0 && u.uv[k] <= [W, H][k], b.name);
    }
  }
}
for (const value of Object.values(meta.files.player.animation))
  assert(fs.existsSync(path.join(out, value)), value);
assert.deepEqual(meta.metadata.license, read("ysm.json").metadata.license);
console.log(
  JSON.stringify({
    out,
    retainedBaseCubes: retained,
    removedAccessoryCubes: removed,
    addedCubes:
      written["minecraft:geometry"][0].bones.reduce(
        (n, b) => n + (b.cubes?.length || 0),
        0,
      ) - retained,
    checks: "passed",
  }),
);
