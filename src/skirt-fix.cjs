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
  const n = 32,
    bands = 8,
    bottom = 14.8,
    top = 21;
  for (let j = 0; j < bands; j++)
    for (let i = 0; i < n; i++) {
      const y = bottom + ((j + 0.5) * (top - bottom)) / bands,
        t = (y - bottom) / (top - bottom),
        rx = 4.8 - t * 0.95,
        rz = 3.25 - t * 1.05;
      // The original pleats enclose a rounded rectangle, rather than a narrow ellipse.
      const section = (a) => [
        Math.sign(Math.sin(a)) * Math.sqrt(Math.abs(Math.sin(a))),
        Math.sign(Math.cos(a)) * Math.sqrt(Math.abs(Math.cos(a))),
      ];
      const a = (2 * Math.PI * (i + 0.5)) / n,
        [s, c] = section(a),
        center = [rx * s, y, rz * c];
      const yaw =
        (Math.atan2((s * s * s) / rx, (c * c * c) / rz) * 180) / Math.PI;
      const slope = (-0.95 * s * s - 1.05 * c * c) / (top - bottom);
      const first = section((2 * Math.PI * i) / n),
        last = section((2 * Math.PI * (i + 1)) / n);
      const width =
          Math.hypot(rx * (last[0] - first[0]), rz * (last[1] - first[1])) *
          1.12,
        height = ((top - bottom) / bands) * Math.sqrt(1 + slope * slope) * 1.12;
      const panelUv = structuredClone(green);
      for (const face of ["north", "east", "south", "west"]) {
        const u = panelUv[face],
          full = u.uv_size[1];
        u.uv[1] += ((bands - j - 1) / bands) * full;
        u.uv_size[1] = full / bands;
      }
      lining.cubes.push({
        origin: [
          center[0] - width / 2,
          center[1] - height / 2,
          center[2] - 0.07,
        ],
        size: [width, height, 0.14],
        pivot: center,
        rotation: [(-Math.atan(slope) * 180) / Math.PI, -yaw, 0],
        uv: panelUv,
      });
    }
  bones.push(lining);
  return geo;
};
