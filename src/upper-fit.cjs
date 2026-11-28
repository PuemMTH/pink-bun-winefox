const assert = require("node:assert/strict");

module.exports = function fitUpperOutfit({ geo, atlas, width, model, mat }) {
  const bones = geo["minecraft:geometry"][0].bones;
  const jacket = bones.find((bone) => bone.name === "jk").cubes;
  if (model === "school") {
    const leaves = jacket.filter(
      (cube) => cube.origin[1] === 28.7 && cube.origin[2] === -2.54,
    );
    assert.equal(leaves.length, 2, "Expected the two JK collar leaves");
    for (const cube of leaves) {
      cube.origin[1] += 0.18;
      cube.pivot[1] += 0.18;
    }
    // The inset stand joins the raised leaves to the neck and covers the dark
    // center of the old jacket neckline. The bow still uses its own rig.
    const white = mat("white");
    const gold = mat("gold");
    const vest = mat("vest");
    jacket.push({
      origin: [-1.4, 29.75, -2.39],
      size: [2.8, 1.2, 0.94],
      uv: { north: white },
    });
    const shadeRows = { north: 18, south: 36, east: 44, west: 44, up: 4, down: 62 };
    for (const cube of jacket) {
      const [u, v] = cube.uv.north.uv;
      const isVest = u === vest.uv[0] && v === vest.uv[1];
      const isTrim = [white, gold].some(({ uv }) => u === uv[0] && v === uv[1]);
      if (isTrim || isVest)
        cube.uv = Object.fromEntries(
          Object.entries(shadeRows).map(([face, shade]) => [
            face,
            isVest && face === "north"
              ? vest
              : { uv: [u, v + (isVest ? 3 : shade)], uv_size: [1, 1] },
          ]),
        );
    }
    return;
  }

  assert.equal(model, "white");
  // Mutate these faces' own texels, keeping the shapes, buttons and base white
  // shirt surfaces as the painter built them. The lighter top row stays white.
  function lilac(face, delta, bottomOnly = false) {
    const [u, v] = face.uv;
    const [w, h] = face.uv_size;
    // Match white-outfit's one-texel edge padding to the newly tinted texels.
    for (let y = bottomOnly ? h - 1 : -1; y <= h; y++)
      for (let x = -1; x <= w; x++) {
        if (u + x < 0 || u + x >= width || v + y < 0) continue;
        const offset = ((v + y) * width + u + x) * 4;
        if (offset + 4 > atlas.length) continue;
        for (let k = 0; k < 3; k++)
          atlas[offset + k] = Math.max(0, atlas[offset + k] - delta[k]);
      }
  }
  const leaves = jacket.filter(
    (cube) => cube.origin[1] === 29.58 && cube.rotation,
  );
  assert.equal(leaves.length, 2, "Expected the two white shirt collar leaves");
  for (const cube of leaves) {
    lilac(cube.uv.north, [22, 25, 13], true);
    lilac(cube.uv.down, [10, 13, 4]);
  }
  const yoke = bones.find((bone) => bone.name === "WhiteShirtYoke");
  const plackets = [...jacket, ...yoke.cubes].filter(
    (cube) =>
      Math.abs(cube.origin[0]) < 0.35 &&
      cube.size[0] < 0.65 &&
      cube.size[1] > 2,
  );
  assert.equal(plackets.length, 2, "Expected upper and lower shirt plackets");
  for (const cube of plackets) {
    lilac(cube.uv.north, [14, 17, 8]);
    lilac(cube.uv.east, [11, 16, 7]);
    lilac(cube.uv.west, [11, 16, 7]);
  }
};
