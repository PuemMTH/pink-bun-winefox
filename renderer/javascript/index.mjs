import * as THREE from "./core/lib/three.module.min.js";
import { createCharacter, loadTexture } from "./core/model.mjs";
import { readModelFolders } from "./core/studio.mjs";
export { evaluate, sample, poseFor } from "./core/animation.mjs";
export { cubeGeometry } from "./core/model.mjs";

async function json(source) {
  if (typeof source !== "string" && !(source instanceof URL))
    return source || {};
  const response = await fetch(source);
  if (!response.ok)
    throw Error(`Cannot load ${source}: HTTP ${response.status}`);
  return response.json();
}

/** Load a URL to a YSM directory or {geometry,texture,animations,info} data/URLs. */
export async function loadModel(source) {
  if (typeof source === "string" || source instanceof URL) {
    const base = new URL(
      String(source).replace(/\/?$/, "/"),
      globalThis.location?.href,
    );
    const info = await json(new URL("ysm.json", base));
    const player = info.files?.player;
    if (!player?.model?.main) throw Error("ysm.json has no player model");
    const animations = { animations: {} };
    for (const file of Object.values(player.animation || {}))
      Object.assign(
        animations.animations,
        (await json(new URL(file, base))).animations,
      );
    const choice = player.texture?.[0];
    source = {
      info,
      animations,
      geometry: await json(new URL(player.model.main, base)),
      texture: new URL(typeof choice === "string" ? choice : choice?.uv, base)
        .href,
    };
  }
  const [geometry, animations, info] = await Promise.all([
    json(source.geometry),
    json(source.animations),
    json(source.info),
  ]);
  let texture, objectURL;
  try {
    if (source.texture?.isTexture) texture = source.texture.clone();
    else {
      const url =
        source.texture instanceof Blob
          ? (objectURL = URL.createObjectURL(source.texture))
          : source.texture;
      if (!url) throw Error("A texture URL, Blob or THREE.Texture is required");
      texture = await loadTexture(url);
    }
    texture.flipY = false;
    texture.magFilter = texture.minFilter = THREE.NearestFilter;
    texture.generateMipmaps = false;
    texture.colorSpace = THREE.SRGBColorSpace;
    const model = createCharacter(geometry, texture, animations);
    const height = Number(info.properties?.height_scale) || 0.7;
    const width = Number(info.properties?.width_scale) || height;
    model.root.scale.set(width, height, width);
    model.info = info;
    return model;
  } catch (error) {
    texture?.dispose();
    throw error;
  } finally {
    if (objectURL) URL.revokeObjectURL(objectURL);
  }
}

/** Local directory input, including a parent directory with several models. No upload. */
export async function loadModelFiles(files) {
  const data = await readModelFolders([...files]);
  const results = await Promise.allSettled(data.map(loadModel));
  const failure = results.find((r) => r.status === "rejected");
  if (failure) {
    for (const result of results)
      if (result.status === "fulfilled") result.value.dispose();
    throw failure.reason;
  }
  return results.map((r) => r.value);
}

export function applyPose(
  model,
  {
    animation = "auto",
    time = 0,
    loop = true,
    blink = false,
    speed,
    headYaw = 0,
    headPitch = 0,
    variables = {},
    boneOverrides = {},
  } = {},
) {
  if (!Number.isFinite(time) || time < 0)
    throw Error("time must be finite and non-negative");
  if (animation === "auto") animation = model.animations.idle ? "idle" : null;
  if (animation !== null && !model.animations[animation])
    throw Error(`Unknown animation: ${animation}`);
  const duration = Number(model.animations[animation]?.animation_length) || 1;
  const localTime = loop ? time % duration : Math.min(time, duration);
  for (const [name, channels] of Object.entries(boneOverrides)) {
    if (!model.bones.has(name)) throw Error(`Unknown bone: ${name}`);
    for (const [kind, values] of Object.entries(channels)) {
      if (
        !["rotation", "position", "scale"].includes(kind) ||
        !Array.isArray(values) ||
        values.length !== 3 ||
        !values.every(Number.isFinite)
      )
        throw Error(`Invalid override: ${name}.${kind}`);
    }
  }
  model.update(animation, localTime, {
    blink,
    ...(speed === undefined ? {} : { speed }),
    headYaw,
    headPitch,
    variables,
  });
  for (const [name, channels] of Object.entries(boneOverrides)) {
    const bone = model.bones.get(name),
      group = bone.group;
    if (channels.rotation) {
      const [x, y, z] = channels.rotation.map(
        (v, i) => v + bone.bindRotation[i],
      );
      group.rotation.set(
        (-x * Math.PI) / 180,
        (-y * Math.PI) / 180,
        (z * Math.PI) / 180,
        "ZYX",
      );
    }
    if (channels.position) {
      const [x, y, z] = channels.position;
      group.position
        .copy(bone.bindPosition)
        .add(new THREE.Vector3(-x, y, z).divideScalar(16));
    }
    if (channels.scale) group.scale.set(...channels.scale);
  }
  model.root.updateMatrixWorld(true);
  return model;
}

/** Browser WebGL renderer with no UI, event handlers or animation loop. */
export function createRenderer({ canvas, pixelRatio = 1 } = {}) {
  if (!Number.isFinite(pixelRatio) || pixelRatio <= 0 || pixelRatio > 4)
    throw Error("Invalid pixelRatio");
  const engine = new THREE.WebGLRenderer({
    ...(canvas ? { canvas } : {}),
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: true,
  });
  engine.setPixelRatio(pixelRatio);
  engine.outputColorSpace = THREE.SRGBColorSpace;
  engine.toneMapping = THREE.NoToneMapping;
  const scene = new THREE.Scene(),
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 1000);
  const ambient = new THREE.AmbientLight(0xffffff, 1.25);
  const key = new THREE.DirectionalLight(0xfff4ed, 2.1);
  key.position.set(-3, 6, -5);
  const rim = new THREE.DirectionalLight(0xcfb6ff, 0.65);
  rim.position.set(3, 3, 4);
  scene.add(ambient, key, rim);
  let disposed = false;
  return {
    canvas: engine.domElement,
    render(model, parameters = {}) {
      if (disposed) throw Error("Renderer has been disposed");
      const {
        width = 512,
        height = 768,
        yaw = 0,
        pitch = 3,
        roll = 0,
        zoom = 1,
        padding = 0.08,
        background = null,
        shading = "lit",
      } = parameters;
      if (
        ![width, height].every((v) => Number.isInteger(v) && v > 0) ||
        width * height * pixelRatio ** 2 > 16777216
      )
        throw Error("Invalid image size (maximum 16,777,216 working pixels)");
      if (
        ![yaw, pitch, roll, zoom, padding].every(Number.isFinite) ||
        zoom <= 0 ||
        padding < 0 ||
        padding >= 0.5
      )
        throw Error("Invalid camera parameters");
      if (!["lit", "unlit", "wire"].includes(shading))
        throw Error("Invalid shading");
      if (model.root.parent)
        throw Error(
          "Detach the model from its existing scene before rendering",
        );
      applyPose(model, parameters);
      model.setMaterial(shading === "unlit" ? "flat" : shading);
      engine.setSize(width, height, false);
      engine.setClearColor(
        background === null || background === "transparent" ? 0 : background,
        background === null || background === "transparent" ? 0 : 1,
      );
      scene.add(model.root);
      try {
        const box = new THREE.Box3().setFromObject(model.root);
        if (box.isEmpty()) throw Error("Model contains no geometry");
        const target = box.getCenter(new THREE.Vector3());
        const y = (yaw * Math.PI) / 180,
          p = (pitch * Math.PI) / 180;
        const direction = new THREE.Vector3(
          Math.sin(y) * Math.cos(p),
          Math.sin(p),
          -Math.cos(y) * Math.cos(p),
        );
        const size = box.getSize(new THREE.Vector3());
        camera.position
          .copy(target)
          .addScaledVector(direction, Math.max(10, size.length() * 2));
        camera.up.set(0, 1, 0);
        camera.lookAt(target);
        camera.rotateZ((roll * Math.PI) / 180);
        camera.updateMatrixWorld(true);
        const projected = [];
        for (const x of [box.min.x, box.max.x])
          for (const y of [box.min.y, box.max.y])
            for (const z of [box.min.z, box.max.z])
              projected.push(
                new THREE.Vector3(x, y, z).applyMatrix4(
                  camera.matrixWorldInverse,
                ),
              );
        const bounds = new THREE.Box3()
          .setFromPoints(projected)
          .getSize(new THREE.Vector3());
        const span =
          Math.max(bounds.y, bounds.x / (width / height), 0.001) /
          (1 - 2 * padding) /
          zoom;
        Object.assign(camera, {
          left: (-span * (width / height)) / 2,
          right: (span * (width / height)) / 2,
          top: span / 2,
          bottom: -span / 2,
        });
        camera.updateProjectionMatrix();
        engine.render(scene, camera);
        return engine.domElement;
      } finally {
        scene.remove(model.root);
      }
    },
    toBlob() {
      if (disposed) return Promise.reject(Error("Renderer has been disposed"));
      return new Promise((resolve, reject) =>
        engine.domElement.toBlob(
          (blob) =>
            blob
              ? resolve(blob)
              : reject(Error("Cannot encode PNG; check texture CORS")),
          "image/png",
        ),
      );
    },
    dispose() {
      if (!disposed) {
        disposed = true;
        engine.dispose();
      }
    },
  };
}
