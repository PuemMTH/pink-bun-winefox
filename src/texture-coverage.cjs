const assert = require("node:assert/strict");

function faceRegions(cube) {
  if (!Array.isArray(cube.uv))
    return Object.values(cube.uv ?? {}).map(({ uv, uv_size = [0, 0] }) => [
      ...uv,
      ...uv_size,
    ]);

  const [u, v] = cube.uv;
  const [w, h, d] = cube.size;
  return [
    [u + d, v + d, w, h],
    [u, v + d, d, h],
    [u + 2 * d + w, v + d, w, h],
    [u + d + w, v + d, d, h],
    [u + d, v, w, d],
    [u + d + w, v + d, w, -d],
  ];
}

function textureCoverage(geometryFiles, width, height) {
  const coverage = new Uint8Array(width * height);
  const texel = (position, extent) => Math.min(extent - 1, Math.max(0, position));
  for (const file of geometryFiles)
    for (const { description, bones } of file["minecraft:geometry"]) {
      assert.equal(description.texture_width, width);
      assert.equal(description.texture_height, height);
      for (const { cubes = [] } of bones)
        for (const cube of cubes)
          for (const [u, v, w, h] of faceRegions(cube)) {
            assert([u, v, w, h].every(Number.isFinite), "Expected a numeric UV region");
            // Keep endpoint samples and the neighboring texels used at face edges.
            const left = texel(Math.floor(Math.min(u, u + w)) - 1, width);
            const top = texel(Math.floor(Math.min(v, v + h)) - 1, height);
            const right = texel(Math.floor(Math.max(u, u + w)) + 1, width) + 1;
            const bottom = texel(Math.floor(Math.max(v, v + h)) + 1, height) + 1;
            for (let y = top; y < bottom; y++)
              coverage.fill(1, y * width + left, y * width + right);
          }
    }
  assert(coverage.includes(1), "No geometry samples the texture");
  return coverage;
}

function pruneTexture(pixels, width, height, geometryFiles) {
  assert.equal(pixels.length, width * height * 4);
  const coverage = textureCoverage(geometryFiles, width, height);
  for (let i = 0; i < coverage.length; i++)
    if (!coverage[i]) pixels.writeUInt32LE(0, i * 4);
}

module.exports = { pruneTexture, textureCoverage };
