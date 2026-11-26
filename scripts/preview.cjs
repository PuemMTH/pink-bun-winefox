const png = require("./png.cjs");
// Orthographic software preview. In-game lighting and animation can differ.
module.exports = function preview(
  geometry,
  atlas,
  W,
  H,
  destination,
  running = false,
) {
  const bones = structuredClone(geometry["minecraft:geometry"][0].bones);
  const by = Object.fromEntries(bones.map((b) => [b.name, b]));
  function ancestor(b, name) {
    for (let q = b; q; q = by[q.parent]) if (q.name === name) return true;
    return false;
  }
  for (const b of bones) {
    const hideNormal =
      running &&
      (ancestor(b, "LeftEyelidBase") ||
        ancestor(b, "RightEyelidBase") ||
        ancestor(b, "Mouth"));
    const hideCustom = !running && b.name.startsWith("CustomRun");
    if (
      hideNormal ||
      hideCustom ||
      ["kongju", "jingya", "xiao"].some((n) => ancestor(b, n))
    )
      delete b.cubes;
    for (const q of b.cubes || [])
      if (q.inflate) {
        q.origin = q.origin.map((v) => v - q.inflate);
        q.size = q.size.map((v) => Math.max(0.005, v + 2 * q.inflate));
        delete q.inflate;
      }
  }
  function rotate(v, r, p = [0, 0, 0]) {
    let [x, y, z] = v.map((n, i) => n - p[i]);
    for (let a = 0; a < 3; a++) {
      const t = (-(r?.[a] || 0) * Math.PI) / 180,
        c = Math.cos(t),
        s = Math.sin(t);
      if (a === 0) [y, z] = [y * c - z * s, y * s + z * c];
      if (a === 1) [x, z] = [x * c + z * s, -x * s + z * c];
      if (a === 2) [x, y] = [x * c - y * s, x * s + y * c];
    }
    return [x + p[0], y + p[1], z + p[2]];
  }
  function world(v, b) {
    for (let q = b; q; q = by[q.parent]) v = rotate(v, q.rotation, q.pivot);
    return v;
  }
  const rw = 720,
    rh = 1050,
    render = Buffer.alloc(rw * rh * 4),
    depth = new Float64Array(rw * rh).fill(Infinity);
  for (let y = 0; y < rh; y++)
    for (let x = 0; x < rw; x++) {
      const i = (y * rw + x) * 4;
      render[i] = 232;
      render[i + 1] = 234;
      render[i + 2] = 243;
      render[i + 3] = 255;
    }
  const faces = {
    north: [0, 3, 2, 1],
    south: [5, 6, 7, 4],
    west: [4, 7, 3, 0],
    east: [1, 2, 6, 5],
    up: [3, 7, 6, 2],
    down: [4, 0, 1, 5],
  };
  function tri(a, b, c, tex, shade) {
    const area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    if (Math.abs(area) < 0.01) return;
    for (
      let y = Math.max(0, Math.floor(Math.min(a[1], b[1], c[1])));
      y < Math.min(rh, Math.ceil(Math.max(a[1], b[1], c[1])));
      y++
    )
      for (
        let x = Math.max(0, Math.floor(Math.min(a[0], b[0], c[0])));
        x < Math.min(rw, Math.ceil(Math.max(a[0], b[0], c[0])));
        x++
      ) {
        const u = ((b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)) / area,
          v = ((c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)) / area,
          t = 1 - u - v;
        if (u < 0 || v < 0 || t < 0) continue;
        const z = u * a[2] + v * b[2] + t * c[2],
          idx = y * rw + x;
        if (z >= depth[idx]) continue;
        const tx = Math.min(
            W - 1,
            Math.max(
              0,
              Math.floor(
                tex.uv[0] + (u * a[3] + v * b[3] + t * c[3]) * tex.uv_size[0],
              ),
            ),
          ),
          ty = Math.min(
            H - 1,
            Math.max(
              0,
              Math.floor(
                tex.uv[1] + (u * a[4] + v * b[4] + t * c[4]) * tex.uv_size[1],
              ),
            ),
          ),
          si = (ty * W + tx) * 4;
        if (atlas[si + 3] === 0) continue;
        depth[idx] = z;
        for (let k = 0; k < 3; k++)
          render[idx * 4 + k] = Math.round(atlas[si + k] * shade);
      }
  }
  for (const b of bones)
    for (const q of b.cubes || []) {
      const [o, s] = [q.origin, q.size],
        points = [
          [0, 0, 0],
          [1, 0, 0],
          [1, 1, 0],
          [0, 1, 0],
          [0, 0, 1],
          [1, 0, 1],
          [1, 1, 1],
          [0, 1, 1],
        ].map((v) => {
          v = v.map((n, i) => o[i] + n * s[i]);
          v = world(rotate(v, q.rotation, q.pivot), b);
          v = rotate(v, [-2, -12, 0]);
          return [rw / 2 + v[0] * 20, rh - 50 - v[1] * 20, v[2]];
        });
      for (const [f, inds] of Object.entries(faces)) {
        const shade = {
            north: 1,
            south: 1,
            west: 0.94,
            east: 0.94,
            up: 1,
            down: 0.94,
          }[f],
          uvs = [
            [0, 1],
            [0, 0],
            [1, 0],
            [1, 1],
          ],
          p = inds.map((n, i) => [...points[n], ...uvs[i]]);
        tri(p[0], p[1], p[2], q.uv[f], shade);
        tri(p[0], p[2], p[3], q.uv[f], shade);
      }
    }
  png.write(destination, rw, rh, render);
};
