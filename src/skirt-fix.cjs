// Keep skirt motion in the hip frame; the jacket may lean independently while running.
module.exports = function fixSkirt(geo, liningUv) {
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
    parent: "DownBody",
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
      for (const face of Object.values(wall.uv)) {
        // One texel per face gives the lining the same flat pixel shading as JK solids.
        face.uv[0] += Math.floor(face.uv_size[0] / 2);
        face.uv[1] += Math.floor(
          (1 - (j + 0.5) / bands) * (face.uv_size[1] - 1),
        );
        face.uv_size = [1, 1];
      }
      lining.cubes.push(wall);
    }
  }
  bones.push(lining);
  return geo;
};
