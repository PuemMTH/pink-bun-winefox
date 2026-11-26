import * as THREE from "./lib/three.module.min.js";
import { poseFor } from "./animation.mjs";
import { makePhotoAnimations } from "./photo-poses.mjs";

const toWorld = ([x = 0, y = 0, z = 0]) =>
  new THREE.Vector3(-x / 16, y / 16, z / 16);
const toRotation = ([x = 0, y = 0, z = 0]) =>
  new THREE.Euler(
    (-x * Math.PI) / 180,
    (-y * Math.PI) / 180,
    (z * Math.PI) / 180,
    "ZYX",
  );
const faces = {
  north: [2, 4, 6, 0],
  south: [5, 3, 1, 7],
  west: [3, 2, 0, 1],
  east: [4, 5, 7, 6],
  up: [3, 5, 4, 2],
  down: [0, 6, 7, 1],
};

export function cubeGeometry(cube, description, bonePivot) {
  const o = cube.origin,
    s = cube.size,
    inflate = cube.inflate || 0;
  const min = [-(o[0] + s[0]) - inflate, o[1] - inflate, o[2] - inflate];
  const max = [-o[0] + inflate, o[1] + s[1] + inflate, o[2] + s[2] + inflate];
  for (let i = 0; i < 3; i++) if (max[i] < min[i]) max[i] = min[i] + 0.001;
  const [x, y, z] = min,
    [X, Y, Z] = max;
  const vertices = [
    [x, y, z],
    [x, y, Z],
    [x, Y, z],
    [x, Y, Z],
    [X, Y, z],
    [X, Y, Z],
    [X, y, z],
    [X, y, Z],
  ];
  const position = [],
    uv = [],
    indices = [];
  const pivot = toWorld(cube.pivot || [0, 0, 0]),
    rotation = toRotation(cube.rotation || [0, 0, 0]);
  const width = description.texture_width,
    height = description.texture_height;
  for (const [name, order] of Object.entries(faces)) {
    const [u0, v0] = Array.isArray(cube.uv) ? cube.uv : [0, 0];
    const [w, h, d] = cube.size;
    const boxUv = {
      north: { uv: [u0 + d, v0 + d], uv_size: [w, h] },
      east: { uv: [u0, v0 + d], uv_size: [d, h] },
      south: { uv: [u0 + 2 * d + w, v0 + d], uv_size: [w, h] },
      west: { uv: [u0 + d + w, v0 + d], uv_size: [d, h] },
      up: { uv: [u0 + d, v0], uv_size: [w, d] },
      down: { uv: [u0 + d + w, v0 + d], uv_size: [w, -d] },
    };
    const face = Array.isArray(cube.uv) ? boxUv[name] : cube.uv?.[name];
    if (!face) continue;
    const [u, v] = face.uv,
      [du, dv] = face.uv_size || [0, 0];
    let corners = [
      [u + du, v],
      [u, v],
      [u, v + dv],
      [u + du, v + dv],
    ];
    const turns = Math.round((face.uv_rotation || 0) / 90) % 4;
    corners = [...corners.slice(turns), ...corners.slice(0, turns)];
    const start = position.length / 3;
    const key = cube.mirror
      ? { east: "west", west: "east", up: "down", down: "up" }[name] || name
      : name;
    const chosen = cube.mirror ? faces[key] : order;
    chosen.forEach((index, i) => {
      const point = new THREE.Vector3(...vertices[index]).divideScalar(16);
      if (cube.rotation) point.sub(pivot).applyEuler(rotation).add(pivot);
      point.sub(bonePivot);
      position.push(point.x, point.y, point.z);
      uv.push(corners[i][0] / width, corners[i][1] / height);
    });
    indices.push(start, start + 1, start + 2, start, start + 2, start + 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(position, 3),
  );
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

export function createCharacter(geometryFile, texture, animationFile) {
  const geometry = geometryFile["minecraft:geometry"]?.[0];
  if (!geometry?.bones)
    throw Error("ไฟล์โมเดลต้องเป็น Bedrock geometry ที่มี bones");
  const root = new THREE.Group(),
    bones = new Map(),
    meshes = [];
  const material = new THREE.MeshLambertMaterial({
    map: texture,
    alphaTest: 0.01,
    side: THREE.DoubleSide,
  });
  const flat = new THREE.MeshBasicMaterial({
    map: texture,
    alphaTest: 0.01,
    side: THREE.DoubleSide,
  });
  const wire = new THREE.MeshBasicMaterial({
    color: 0xffb6d7,
    wireframe: true,
  });
  for (const source of geometry.bones) {
    const group = new THREE.Group();
    group.name = source.name;
    bones.set(source.name, {
      group,
      source,
      pivot: toWorld(source.pivot || [0, 0, 0]),
      bindRotation: source.rotation || [0, 0, 0],
    });
  }
  let cubes = 0,
    triangles = 0;
  for (const bone of bones.values()) {
    const parent = bones.get(bone.source.parent);
    bone.bindPosition = bone.pivot
      .clone()
      .sub(parent?.pivot || new THREE.Vector3());
    bone.group.position.copy(bone.bindPosition);
    bone.group.rotation.copy(toRotation(bone.bindRotation));
    (parent?.group || root).add(bone.group);
    for (const cube of bone.source.cubes || []) {
      if (!cube.origin || !cube.size || !cube.uv) continue;
      const shape = cubeGeometry(cube, geometry.description, bone.pivot);
      const mesh = new THREE.Mesh(shape, material);
      mesh.name = bone.source.name;
      mesh.castShadow = true;
      mesh.receiveShadow = false;
      bone.group.add(mesh);
      meshes.push(mesh);
      cubes++;
      triangles += shape.index.count / 3;
    }
  }
  const sourceAnimations = animationFile.animations || {};
  const animations = {
    ...sourceAnimations,
    ...makePhotoAnimations(sourceAnimations, bones.keys()),
  };
  return {
    root,
    bones,
    animations,
    stats: { bones: bones.size, cubes, triangles },
    update(clip, time, options = {}) {
      const pose = poseFor(animations, clip, time, {
        speed: clip === "run" ? 5.6 : clip === "walk" ? 3 : 0,
        ...options,
      });
      for (const [name, bone] of bones) {
        const value = pose.get(name) || {};
        bone.group.position
          .copy(bone.bindPosition)
          .add(toWorld(value.position || [0, 0, 0]));
        bone.group.rotation.copy(
          toRotation(
            bone.bindRotation.map((v, i) => v + (value.rotation?.[i] || 0)),
          ),
        );
        bone.group.scale.set(...(value.scale || [1, 1, 1]));
      }
    },
    setMaterial(mode) {
      for (const mesh of meshes)
        mesh.material =
          mode === "wire" ? wire : mode === "flat" ? flat : material;
    },
    setWireColor(color) {
      wire.color.set(color);
    },
    dispose() {
      for (const mesh of meshes) mesh.geometry.dispose();
      material.dispose();
      flat.dispose();
      wire.dispose();
      texture.dispose();
    },
  };
}

export async function loadTexture(url) {
  const texture = await new THREE.TextureLoader().loadAsync(url);
  texture.flipY = false;
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
