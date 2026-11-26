const fs = require("node:fs");
const zlib = require("node:zlib");
const assert = require("node:assert/strict");

function crc(buffer) {
  let c = 0xffffffff;
  for (const byte of buffer) {
    c ^= byte;
    for (let i = 0; i < 8; i++) c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function write(file, width, height, pixels) {
  function chunk(type, data) {
    const name = Buffer.from(type),
      length = Buffer.alloc(4),
      checksum = Buffer.alloc(4);
    length.writeUInt32BE(data.length);
    checksum.writeUInt32BE(crc(Buffer.concat([name, data])));
    return Buffer.concat([length, name, data, checksum]);
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  const rows = [];
  for (let y = 0; y < height; y++)
    rows.push(
      Buffer.from([0]),
      pixels.subarray(y * width * 4, (y + 1) * width * 4),
    );
  fs.writeFileSync(
    file,
    Buffer.concat([
      Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
      chunk("IHDR", header),
      chunk("IDAT", zlib.deflateSync(Buffer.concat(rows))),
      chunk("IEND", Buffer.alloc(0)),
    ]),
  );
}

function read(file) {
  const data = fs.readFileSync(file),
    idat = [];
  assert(
    data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])),
    "Invalid PNG",
  );
  const width = data.readUInt32BE(16),
    height = data.readUInt32BE(20);
  assert(
    data[24] === 8 && data[25] === 6 && data[28] === 0,
    "Base texture must be an 8-bit RGBA, non-interlaced PNG",
  );
  for (let offset = 8; offset < data.length; ) {
    const length = data.readUInt32BE(offset),
      type = data.toString("ascii", offset + 4, offset + 8);
    if (type === "IDAT")
      idat.push(data.subarray(offset + 8, offset + 8 + length));
    offset += length + 12;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat)),
    stride = width * 4;
  assert.equal(raw.length, height * (stride + 1));
  const pixels = Buffer.alloc(width * height * 4);
  function paeth(a, b, c) {
    const p = a + b - c,
      pa = Math.abs(p - a),
      pb = Math.abs(p - b),
      pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  }
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    assert(filter <= 4, "Invalid PNG row filter");
    for (let x = 0; x < stride; x++) {
      const i = y * stride + x,
        a = x >= 4 ? pixels[i - 4] : 0;
      const b = y ? pixels[i - stride] : 0,
        c = y && x >= 4 ? pixels[i - stride - 4] : 0;
      const prediction = [0, a, b, Math.floor((a + b) / 2), paeth(a, b, c)][
        filter
      ];
      pixels[i] = (raw[y * (stride + 1) + x + 1] + prediction) & 255;
    }
  }
  return { width, height, pixels };
}

module.exports = { read, write, crc };
