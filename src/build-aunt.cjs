const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const png = require("../scripts/png.cjs");
const { pruneTexture } = require("./texture-coverage.cjs");

const root = path.resolve(__dirname, "..");
const source = path.join(root, "vendor", "winefox-matured");
const output = path.join(root, "dist", "satou_aunt");
const read = (file) => JSON.parse(fs.readFileSync(path.join(source, file), "utf8"));
const write = (file, data) =>
  fs.writeFileSync(path.join(output, file), JSON.stringify(data, null, 2) + "\n");

const manifest = read("ysm.json");
const player = manifest.files.player;
const geo = read(player.model.main);
const arm = read(player.model.arm);
const animations = read(player.animation.main);
const extra = read(player.animation.extra);
const texture = player.texture[0].uv;
const { pixels: atlas, width, height } = png.read(path.join(source, texture));
const geometry = geo["minecraft:geometry"][0];

// Keep the rig and its attachment bones while removing the old costume props.
const accessories = new Set([
  "FOX", "Ear", "MTail", "Mask", "bow11", "UmbrellaArm",
  "JiuHu", "bow", "magicbook", "swordroot", "chair2", "heart", "ysmGlowZZZ",
]);
const byName = new Map(geometry.bones.map((bone) => [bone.name, bone]));
for (const bone of geometry.bones)
  for (let group = bone; group; group = byName.get(group.parent)) {
    if (!accessories.has(group.name)) continue;
    delete bone.cubes;
    break;
  }

delete animations.animations.pre_parallel0.bones.MAllbody;
delete animations.animations.parallel4;
delete extra.animations.extra0;
delete manifest.properties.extra_animation_buttons;
manifest.properties.preview_animation = "idle";
manifest.properties.extra_animation = {
  extra1: "Wave",
  extra2: "Clap",
  extra3: "Get Down",
  extra4: "Dance",
  extra5: "Smile",
  extra6: "Hand Gesture",
  extra7: "Duet Dance",
};

const { authors, license } = manifest.metadata;
manifest.metadata = { name: "Satou's Aunt", tips: "Pink Dress · Lavender Braid", license };
geometry.description.identifier = "geometry.satou_aunt";
arm["minecraft:geometry"][0].description.identifier = "geometry.satou_aunt_arm";
const input = { geo, arm, atlas, width, height, animations, extra };
require("./aunt-head.cjs")(input);
require("./aunt-outfit.cjs")(input);
const { glide, creative } = require("./aunt-flight.cjs")(animations.animations.elytra_fly);
animations.animations.elytra_fly = glide;
animations.animations.fly = creative;
const boneNames = new Set(geometry.bones.map(({ name }) => name));
for (const pose of [glide, creative])
  for (const name of Object.keys(pose.bones))
    assert(boneNames.has(name), `Flight pose uses missing bone: ${name}`);

for (const file of [geo, arm])
  for (const { description, bones } of file["minecraft:geometry"]) {
    assert.equal(description.texture_width, width);
    assert.equal(description.texture_height, height);
    const names = new Set(bones.map((bone) => bone.name));
    assert.equal(names.size, bones.length, "Duplicate bone names");
    for (const { name, parent, cubes = [] } of bones) {
      if (parent) assert(names.has(parent), `Missing parent of ${name}`);
      for (const cube of cubes) {
        assert(cube.origin.every(Number.isFinite) && cube.size.every(Number.isFinite), name);
        for (const { uv, uv_size } of Object.values(cube.uv ?? {})) {
          if (!uv || !uv_size) continue;
          for (const [axis, limit] of [width, height].entries()) {
            const end = uv[axis] + uv_size[axis];
            assert(
              Math.min(uv[axis], end) >= 0 && Math.max(uv[axis], end) <= limit,
              `UV outside texture: ${name}`,
            );
          }
        }
      }
    }
  }

pruneTexture(atlas, width, height, [geo, arm]);
fs.cpSync(source, output, {
  recursive: true,
  filter: (file) => !["avatar", "lang"].includes(path.relative(source, file)),
});
write("ysm.json", manifest);
write(player.model.main, geo);
write(player.model.arm, arm);
write(player.animation.main, animations);
write(player.animation.extra, extra);
png.write(path.join(output, texture), width, height, atlas);
fs.copyFileSync(path.join(root, "LICENSE"), path.join(output, "LICENSE"));
fs.writeFileSync(
  path.join(output, "ATTRIBUTION.md"),
  "# Satou's Aunt — attribution\n\n" +
    "This fan model adapts **Matured Wine Fox (大酒狐), variant `13_matured`**, bundled with [Yes Steve Model](https://modrinth.com/mod/yes-steve-model).\n\n" +
    authors.map(({ name, role, contact }) => `- ${name} (${role}) · ${Object.values(contact).join(" · ")}`).join("\n") +
    "\n\nThe base and adaptation use [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See LICENSE. The original source metadata is preserved in the development repository.\n\n" +
    "Changes include the face, hair, dress, limbs, accessory visibility, and supporting animation adjustments. Character design follows the supplied Happy Sugar Life references. Character rights remain with their respective owners.\n",
);
console.log(`Built ${manifest.metadata.name}: ${output}`);
if (process.argv.includes("--pack")) {
  require("../scripts/pack.cjs")(output, path.join(root, "downloads", "satou-aunt.zip"));
}
