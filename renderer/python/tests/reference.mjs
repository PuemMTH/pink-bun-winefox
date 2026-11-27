// Development-only parity oracle. The Python package itself does not need Node.
import fs from "node:fs";
import path from "node:path";
import * as THREE from "../../../viewer/lib/three.module.min.js";
import { createCharacter } from "../../../viewer/model.mjs";
const root = process.argv[2];
const read = (file) => JSON.parse(fs.readFileSync(path.join(root, file), "utf8"));
const info = read("ysm.json"), files = info.files.player;
const animations = { animations: {} };
for (const file of Object.values(files.animation)) Object.assign(animations.animations, read(file).animations);
const character = createCharacter(read(files.model.main), new THREE.Texture(), animations);
const height = Number(info.properties?.height_scale) || .7;
const width = Number(info.properties?.width_scale) || height;
character.root.scale.set(width, height, width);
const result = [];
for (const [animation, time] of [["idle",1], ["walk",.5], ["run",.2], ["studio_photo_cheeks",0]]) {
  character.update(animation, time, { blink: false });
  character.root.updateMatrixWorld(true);
  const matrices = Object.fromEntries([...character.bones].map(([name, bone]) => [name, [...bone.group.matrixWorld.elements]]));
  const samples = [];
  let offset = 0;
  for (const bone of character.bones.values()) for (const mesh of bone.group.children.filter(child => child.isMesh)) {
    const positions = mesh.geometry.attributes.position, uvs = mesh.geometry.attributes.uv;
    for (const index of [0, positions.count-1]) {
      const point = new THREE.Vector3().fromBufferAttribute(positions,index).applyMatrix4(mesh.matrixWorld);
      samples.push({index:offset+index,position:point.toArray(),uv:[uvs.getX(index),uvs.getY(index)]});
    }
    offset += positions.count;
  }
  result.push({ animation, time, matrices, samples });
}
character.dispose();
process.stdout.write(JSON.stringify(result));
