import * as THREE from "./lib/three.module.min.js";
import { createCharacter, loadTexture } from "./model.mjs";

export const cameraDirections = {
  front: [0, 0.05, -5],
  side: [5, 0, 0],
  back: [0, 0, 5],
  three: [-4, 1.5, -5],
  top: [0, 5, -0.001],
  front3q: [-4, 1.5, -5],
  back3q: [4, 1.5, 5],
  left: [-5, 0, 0],
  right: [5, 0, 0],
};

export function createStage() {
  const scene = new THREE.Scene();
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    preserveDrawingBuffer: true,
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const key = new THREE.DirectionalLight(0xfff4ed, 2.1);
  key.position.set(-3, 6, -5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, { left: -6, right: 6, top: 5, bottom: -3 });
  key.shadow.normalBias = 0.015;
  key.shadow.bias = -0.0003;
  const rim = new THREE.DirectionalLight(0xcfb6ff, 0.65);
  rim.position.set(3, 3, 4);
  scene.add(new THREE.AmbientLight(0xffffff, 1.25), key, rim);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(200, 200),
    new THREE.ShadowMaterial({ opacity: 0.18 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.012;
  ground.receiveShadow = true;
  scene.add(ground);

  const grid = new THREE.GridHelper(30, 120, 0x61506d, 0x3c3446);
  grid.material.transparent = true;
  grid.material.opacity = 0.42;
  grid.position.y = -0.015;
  scene.add(grid);
  return { scene, renderer, ground, grid };
}

export async function characterFromData(data) {
  const local = typeof data.texture !== "string";
  const url = local ? URL.createObjectURL(data.texture) : data.texture;
  let texture;
  try {
    texture = await loadTexture(url);
    const character = createCharacter(data.geometry, texture, data.animations);
    const properties = data.info?.properties || {};
    const height = Number(properties.height_scale) || 0.7;
    const width = Number(properties.width_scale) || height;
    character.root.scale.set(width, height, width);
    const poseRoot = character.root;
    const root = new THREE.Group().add(poseRoot);
    const clipUpdate = character.update;
    let sleepOffset;
    return {
      ...character,
      root,
      update(clip, time, options = {}) {
        if (clip === "jump") {
          options = {
            ...options,
            variables: {
              "query.vertical_speed": 8 - 20 * Math.min(0.75, time),
              "query.is_on_ground": 0,
              ...options.variables,
            },
          };
        }
        poseRoot.rotation.set(0, 0, 0);
        poseRoot.position.set(0, 0, 0);
        if (
          clip === "sleep" &&
          character.bones.has("DownBody") &&
          character.bones.has("Head")
        ) {
          // The sleep animation curls the limbs. The player renderer supplies
          // the separate laying rotation, approximated here for one bed direction.
          if (sleepOffset === undefined) {
            clipUpdate(clip, 0, { blink: false });
            const hips = character.bones
              .get("DownBody")
              .group.getWorldPosition(new THREE.Vector3());
            const axis = character.bones
              .get("Head")
              .group.getWorldPosition(new THREE.Vector3())
              .sub(hips);
            sleepOffset = null;
            if (Math.abs(axis.y) > Math.hypot(axis.x, axis.z)) {
              poseRoot.rotateZ(Math.PI / 2).rotateY((3 * Math.PI) / 2);
              const box = new THREE.Box3().setFromObject(poseRoot);
              const origin = root.getWorldPosition(new THREE.Vector3());
              sleepOffset = origin
                .clone()
                .sub(box.getCenter(new THREE.Vector3()));
              sleepOffset.y = origin.y - box.min.y;
            }
          }
          if (sleepOffset) {
            poseRoot.rotation.set(0, 0, 0);
            poseRoot.rotateZ(Math.PI / 2).rotateY((3 * Math.PI) / 2);
            poseRoot.position.copy(sleepOffset);
          }
        }
        clipUpdate(clip, time, options);
      },
    };
  } catch (error) {
    texture?.dispose();
    throw error;
  } finally {
    if (local) URL.revokeObjectURL(url);
  }
}
