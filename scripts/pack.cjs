const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const { crc } = require("./png.cjs");
const root = path.resolve(__dirname, "..");
function pack(source, destination) {
  const locals = [],
    directory = [];
  let offset = 0,
    count = 0;
  function walk(folder) {
    for (const entry of fs
      .readdirSync(folder, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name, "en"))) {
      const full = path.join(folder, entry.name);
      if (entry.isDirectory()) {
        walk(full);
        continue;
      }
      const name = Buffer.from(
        path.relative(source, full).split(path.sep).join("/"),
      );
      const raw = fs.readFileSync(full),
        compressed = zlib.deflateRawSync(raw),
        checksum = crc(raw);
      const header = Buffer.alloc(30);
      header.writeUInt32LE(0x04034b50);
      header.writeUInt16LE(20, 4);
      header.writeUInt16LE(0x800, 6);
      header.writeUInt16LE(8, 8);
      header.writeUInt16LE(0x21, 12);
      header.writeUInt32LE(checksum, 14);
      header.writeUInt32LE(compressed.length, 18);
      header.writeUInt32LE(raw.length, 22);
      header.writeUInt16LE(name.length, 26);
      locals.push(header, name, compressed);
      const central = Buffer.alloc(46);
      central.writeUInt32LE(0x02014b50);
      central.writeUInt16LE(20, 4);
      central.writeUInt16LE(20, 6);
      central.writeUInt16LE(0x800, 8);
      central.writeUInt16LE(8, 10);
      central.writeUInt16LE(0x21, 14);
      central.writeUInt32LE(checksum, 16);
      central.writeUInt32LE(compressed.length, 20);
      central.writeUInt32LE(raw.length, 24);
      central.writeUInt16LE(name.length, 28);
      central.writeUInt32LE(offset, 42);
      directory.push(central, name);
      offset += header.length + name.length + compressed.length;
      count++;
    }
  }
  walk(source);
  const central = Buffer.concat(directory),
    end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50);
  end.writeUInt16LE(count, 8);
  end.writeUInt16LE(count, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(offset, 16);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.writeFileSync(destination, Buffer.concat([...locals, central, end]));
  console.log(`Packed ${count} model files: ${destination}`);
}

if (require.main === module) {
  for (const name of [
    "pink_bun_winefox",
    "pink_bun_winefox_white",
    "pink_bun_winefox_square_eyes",
    "pink_bun_winefox_white_square_eyes",
    "satou_aunt",
  ])
    pack(
      path.join(root, "dist", name),
      path.join(root, "downloads", name.replaceAll("_", "-") + ".zip"),
    );
}

module.exports = pack;
