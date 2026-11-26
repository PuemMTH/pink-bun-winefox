// UV/material authoring: preserve the native face layout and luminance ramps of Wine Fox JK.
module.exports = function materials(source, colors) {
  const names = Object.keys(colors),
    W = 2048,
    H = 512,
    pixels = Buffer.alloc(W * H * 4),
    samples = Object.fromEntries(names.map((n) => [n, []]));
  const rgb = (s) => s.match(/../g).map((n) => parseInt(n, 16));
  const offset = (n) => {
    const i = names.indexOf(n) + 1;
    if (i === 0) throw Error("Unknown material " + n);
    return [(i % 8) * 256, Math.floor(i / 8) * 256];
  };
  const luminance = (i) =>
    0.2126 * source[i] + 0.7152 * source[i + 1] + 0.0722 * source[i + 2];
  function swatch(n) {
    const [x, y] = offset(n);
    return { uv: [x + 184, y + 162], uv_size: [20, 76] };
  }
  function remap(q, n) {
    if (!q.uv) {
      q.uv = Object.fromEntries(
        ["north", "east", "south", "west", "up", "down"].map((f) => [
          f,
          swatch(n),
        ]),
      );
      return;
    }
    const [ox, oy] = offset(n);
    for (const u of Object.values(q.uv)) {
      const old = structuredClone(u),
        sx = old.uv_size?.[0] || 0,
        sy = old.uv_size?.[1] || 0;
      for (const fraction of [0.25, 0.5, 0.75]) {
        const x = Math.max(
            0,
            Math.min(255, Math.floor(old.uv[0] + sx * fraction)),
          ),
          y = Math.max(0, Math.min(255, Math.floor(old.uv[1] + sy * fraction))),
          i = (y * 256 + x) * 4;
        if (source[i + 3] > 128 && luminance(i) > 12)
          samples[n].push(luminance(i));
      }
      u.uv[0] += ox;
      u.uv[1] += oy;
    }
  }
  function finish() {
    for (let y = 0; y < 256; y++)
      source.copy(pixels, y * W * 4, y * 256 * 4, (y + 1) * 256 * 4);
    const references = {};
    for (const n of names) {
      const list = samples[n].sort((a, b) => a - b),
        ref = list.length ? list[Math.floor((list.length - 1) * 0.85)] : 200;
      references[n] = Math.round(ref);
      const [ox, oy] = offset(n),
        [light, dark] = colors[n].map(rgb),
        target = light.map((v, i) => v * 0.65 + dark[i] * 0.35);
      for (let y = 0; y < 256; y++)
        for (let x = 0; x < 256; x++) {
          const si = (y * 256 + x) * 4,
            di = ((y + oy) * W + x + ox) * 4,
            l = luminance(si),
            brightness = Math.max(0.18, Math.min(1.3, Math.pow(l / ref, 0.65)));
          for (let k = 0; k < 3; k++) {
            const shade = target[k] * Math.min(1, brightness),
              highlight = Math.max(0, brightness - 1) * 1.8;
            pixels[di + k] = Math.round(
              Math.min(255, shade + (255 - shade) * highlight),
            );
          }
          pixels[di + 3] = source[si + 3];
        }
      // New geometry uses a reserved ramp in the otherwise unused corner of each material tile.
      for (let y = 0; y < 80; y++)
        for (let x = 0; x < 24; x++) {
          const di = ((oy + 160 + y) * W + ox + 182 + x) * 4,
            t = y / 79;
          for (let k = 0; k < 3; k++)
            pixels[di + k] = Math.round(light[k] * (1 - t) + dark[k] * t);
          if (n === "vest") {
            // Broad, stepped light/shadow shapes match the JK fabric treatment, with
            // a fitted waist, shadow below the bow and restrained diagonal folds.
            const u = x / 23,
              edge = Math.abs(u - 0.5) * 2;
            let value = 1.06 - 0.19 * edge * edge - 0.06 * t;
            if (t < 0.22 && Math.abs(u - 0.5) < (0.22 - t) * 1.2) value -= 0.13;
            if (u < 0.18 && t > 0.3 && t < 0.65) value -= 0.09;
            if (u > 0.82 && t > 0.2 && t < 0.55) value -= 0.08;
            if (
              t > 0.56 &&
              t < 0.75 &&
              Math.abs(u - (0.12 + (t - 0.56) * 1.5)) < 0.045
            )
              value -= 0.12;
            if (t > 0.73 && Math.abs(u - (0.9 - (t - 0.73) * 1.1)) < 0.04)
              value -= 0.1;
            value = Math.round(value * 18) / 18;
            if (x === 11 && t > 0.22) value -= 0.12;
            for (let k = 0; k < 3; k++)
              pixels[di + k] = Math.min(255, Math.round(target[k] * value));
          }
          pixels[di + 3] = 255;
        }
    }
    return { pixels, references };
  }
  return { W, H, swatch, remap, finish };
};
