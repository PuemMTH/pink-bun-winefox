# ysm-render-js

UI-independent JavaScript ES module for browser-side YSM/Bedrock rendering. Works on static hosting, including GitHub Pages; no backend or Python is required. Uses the existing Three.js geometry, UV, Molang and photo-pose core.

From the repository root, build the portable package:

```sh
node renderer/javascript/build.cjs
```

Copy **all of `dist/javascript/`** into your website. It contains its own core modules and pinned Three.js files, with no CDN or npm dependencies. Serve it through HTTP/HTTPS; opening HTML using `file://` is not supported. To use with a bundler: `npm install ./dist/javascript`, then import from `ysm-render-js`. This package is not published to npm.

```html
<canvas id="character"></canvas>
<script type="module">
  import { loadModel, createRenderer } from './javascript/index.mjs';
  const model = await loadModel('./models/my-character/'); // Contains ysm.json
  const renderer = createRenderer({canvas: document.querySelector('#character')});
  renderer.render(model, {
    animation: 'run', time: 0.2,
    width: 512, height: 768, yaw: 25, pitch: 8,
    background: null, shading: 'lit'
  });
  const png = await renderer.toBlob(); // PNG Blob; download or upload as needed
  // Reuse renderer/model for other frames and angles.
  // renderer.dispose(); model.dispose(); when finished.
</script>
```

`loadModel` also accepts `{geometry, texture, animations, info}`: JSON objects or URLs for JSON fields; a URL, Blob/File or Three.js Texture for the texture. The model owns its loaded/cloned texture. Its `root`, `bones`, `animations`, `stats` and `info` remain accessible for other Three.js applications. To use a renderer model inside another scene, detach it before calling `renderer.render`.

```js
const model = await loadModel({
  geometry: './assets/model.json', texture: './assets/texture.png',
  animations: './assets/animations.json', info: './assets/info.json'
});
// Local folder input: <input type="file" webkitdirectory multiple>
const models = await loadModelFiles(input.files); // No upload; one or several models
```

Exports: `loadModel`, `loadModelFiles`, `createRenderer`, `applyPose`, `cubeGeometry`, `poseFor`, `sample`, `evaluate`. `applyPose(model, parameters)` updates the skeleton without creating a WebGL context; numeric geometry/animation exports also work in Node. Image rendering needs a browser canvas/WebGL; this is not a Node CPU rasterizer.

Render parameters: `animation` (auto/idle by default, `null` for bind pose), `time` (seconds), `loop`, `blink`, `speed`, `headYaw`, `headPitch`, `variables`, `boneOverrides`, `width`, `height`, `yaw`, `pitch`, `roll` (degrees), `zoom`, `padding`, `background` (null/transparent or Three.js color), and `shading` (lit/unlit/wire). `boneOverrides` uses Bedrock rotations/positions and three-element scale vectors; for example `{Head:{rotation:[0,-15,5]}}`. Camera yaw 0 is front, 90 is side. Calls reset the sampled pose, so separate renders do not retain old overrides. Caller controls animation timing; no event listeners or animation loop are installed.

Models/textures must be same-origin or allow CORS for loading and PNG export. Folder input accepts unpacked JSON/PNG assets; ZIP and encrypted `.ysm` imports are not implemented in this browser loader. Native YSM physics/controllers/items/lightmaps are outside this adapter. Six photo poses are available on compatible Wine Fox rigs. Character assets retain their original licenses and are not bundled in this package. Code: repository CC BY-NC-SA 4.0; bundled Three.js: MIT (`core/lib/THREE-LICENSE.txt`).
