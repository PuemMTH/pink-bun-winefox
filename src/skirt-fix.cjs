// Keep skirt motion in the hip frame; the jacket may lean independently while running.
module.exports = function fixSkirt(geo, liningUv, animations) {
  const bones = geo["minecraft:geometry"][0].bones,
    by = Object.fromEntries(bones.map((b) => [b.name, b]));
  by.cloth.parent = "DownBody";
  for (const name of ["LeftLeg", "RightLeg"])
    for (const q of [...(by[name].cubes || [])]) {
      if (q.rotation || q.origin[1] + q.size[1] <= 16.2) continue;
      const oldHeight = q.size[1],
        newHeight = 16.2 - q.origin[1];
      if (newHeight <= 0) throw Error("Unexpected thigh geometry");
      q.size[1] = newHeight;
      // Preserve the UV scale of the visible thigh when removing its concealed upper end.
      for (const f of ["north", "south", "east", "west"]) {
        const u = q.uv[f],
          cut = ((oldHeight - newHeight) / oldHeight) * u.uv_size[1];
        u.uv[1] += cut;
        u.uv_size[1] -= cut;
      }
      // Preserve the exposed knee/thigh contour; taper only the section under the hem.
      const split = 14.3,
        upper = structuredClone(q),
        lowerHeight = split - q.origin[1];
      upper.origin[1] = split;
      upper.size[1] = 16.2 - split;
      upper.origin[0] += 0.3;
      upper.size[0] -= 0.6;
      upper.origin[2] += 1.2;
      upper.size[2] -= 2.4;
      for (const f of ["north", "south", "east", "west"]) {
        const scale = q.uv[f].uv_size[1] / q.size[1];
        upper.uv[f].uv_size[1] = upper.size[1] * scale;
        q.uv[f].uv[1] += upper.size[1] * scale;
        q.uv[f].uv_size[1] = lowerHeight * scale;
      }
      q.size[1] = lowerHeight;
      by[name].cubes.push(upper);
    }
  const lining = {
    name: "CustomSkirtLining",
    parent: "cloth",
    pivot: [0, 19.7, 0],
    cubes: [],
  };
  const green = liningUv || by.FrontClothe.cubes[0].uv;
  // Three stepped rectangular frames match the block construction of the JK pleats.
  // The walls overlap at corners, keeping a closed lining with only twelve cubes.
  const bands = 3,
    bottom = 14.8,
    top = 21,
    thickness = 0.18;
  for (let j = 0; j < bands; j++) {
    const t = j / bands,
      y = bottom + t * (top - bottom);
    const height = (top - bottom) / bands;
    const profile = (j + 0.5) / bands;
    const rx = 4.8 - profile * 0.95,
      rz = 3.25 - profile * 1.05;
    const walls = [
      { origin: [-rx, y, -rz], size: [2 * rx, height, thickness] },
      { origin: [-rx, y, rz - thickness], size: [2 * rx, height, thickness] },
      { origin: [-rx, y, -rz], size: [thickness, height, 2 * rz] },
      { origin: [rx - thickness, y, -rz], size: [thickness, height, 2 * rz] },
    ];
    for (const wall of walls) {
      wall.uv = structuredClone(green);
      for (const [name, face] of Object.entries(wall.uv)) {
        // Carry the same broad pixel pleats through all three lining tiers.
        const fullHeight = face.uv_size[1];
        face.uv[1] += ((bands - j - 1) / bands) * fullHeight;
        face.uv_size[1] = fullHeight / bands;
        if (name === "up" || name === "down") {
          face.uv[0] += 1;
          face.uv_size = [1, 1];
        }
      }
      lining.cubes.push(wall);
    }
  }
  bones.push(lining);
  // Keep the pleats and lining together, with a small shared sway at the waist.
  // Individual panels still retain their bind transforms so no seams open.
  const skirtBones = bones.filter((b) => {
    let parent = b;
    while (parent && parent.name !== "cloth") parent = by[parent.parent];
    return Boolean(parent);
  });
  for (const clip of ["run", "jump", "sneak", "sneaking"])
    for (const b of skirtBones)
      animations.animations[clip].bones[b.name] = {
        rotation: [0, 0, 0],
        position: [0, 0, 0],
        scale: [1, 1, 1],
      };
  const run = animations.animations.run.bones;
  const duration = animations.animations.run.animation_length;
  const sway = [1.2, 1.8, 0.8]; // pitch, yaw and roll amplitudes in degrees
  run.cloth.rotation = Object.fromEntries(
    Array.from({ length: 9 }, (_, i) => {
      const phase = (i / 8) * Math.PI * 2;
      return [
        ((duration * i) / 8).toFixed(4),
        [
          sway[0] * Math.cos(phase),
          sway[1] * Math.sin(phase),
          sway[2] * Math.cos(phase),
        ].map((n) => Math.round(n * 10000) / 10000),
      ];
    }),
  );
  // The imported crouch rotates the front pleat by -112 degrees. Keep that
  // panel down and move the whole skirt gently, with the lining following it.
  const sneak = animations.animations.sneak;
  sneak.bones.cloth.rotation = Object.fromEntries(
    Object.entries(run.cloth.rotation).map(([time, rotation]) => [
      ((Number(time) / duration) * sneak.animation_length).toFixed(4),
      rotation.map((n) => Math.round(n * 0.4 * 10000) / 10000),
    ]),
  );
  animations.animations.sneaking.bones.cloth.rotation = [2, 0, 0];
  animations.animations.jump.bones.cloth.rotation = [1.5, 0, 0];
  return geo;
};
