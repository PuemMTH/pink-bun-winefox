from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np
from PIL import Image

from ysm_render import Model, RenderOptions, load_model, render, render_to_file
from ysm_render.animation import evaluate, sample
from ysm_render.model import cube_geometry

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "dist/pink_bun_winefox"


class RendererTests(unittest.TestCase):
    def test_molang_and_keyframes(self):
        self.assertAlmostEqual(evaluate("math.sin(90)+math.cos(180)"), 0)
        self.assertEqual(evaluate("ysm.food_level<=6?5:0", {"ysm.food_level": 4}), 5)
        self.assertEqual(evaluate("math.round(-1.5)"), -1)
        self.assertEqual(evaluate("-5%3"), -2)
        self.assertEqual(evaluate("math.clamp(-5,0,10)+math.lerp(2,6,0.5)"), 4)
        self.assertEqual(evaluate("1/0"), 0)
        self.assertEqual(evaluate("__import__('os').system('echo unsafe')"), 0)
        self.assertEqual(evaluate("v.s=48; v.s"), 0)
        keys = {
            "0": [0, 0, 0],
            "1": {"pre": [10, 0, 0], "post": [20, 0, 0]},
            "2": [30, 0, 0],
        }
        self.assertEqual(sample(keys, 0.5), [5, 0, 0])
        self.assertEqual(sample(keys, 1), [20, 0, 0])
        self.assertEqual(sample(keys, 1.5), [25, 0, 0])
        self.assertEqual(
            sample(
                {"0": {"post": [0, 0, 0], "lerp_mode": "catmullrom"}, "1": [10, 0, 0]},
                0.5,
            ),
            [5, 0, 0],
        )

    def test_reflection_signed_uv_and_inflate(self):
        description = {"texture_width": 16, "texture_height": 16}
        vertices, uv, triangles = cube_geometry(
            {
                "origin": [0, 0, 0],
                "size": [2, 3, 4],
                "uv": {"north": {"uv": [4, 5], "uv_size": [-2, 3]}},
            },
            description,
            np.zeros(3),
        )
        np.testing.assert_allclose(vertices[0], [-2 / 16, 3 / 16, 0])
        np.testing.assert_allclose(uv[:2], [[2 / 16, 5 / 16], [4 / 16, 5 / 16]])
        self.assertEqual(len(triangles), 2)
        vertices, _, triangles = cube_geometry(
            {"origin": [0, 0, 0], "size": [2, 3, 4], "inflate": 0.5, "uv": [0, 0]},
            description,
            np.zeros(3),
        )
        self.assertAlmostEqual(vertices[:, 0].min(), -2.5 / 16)
        self.assertAlmostEqual(vertices[:, 1].max(), 3.5 / 16)
        self.assertEqual(len(triangles), 12)
        with self.assertRaisesRegex(ValueError, "finite"):
            cube_geometry(
                {"origin": [0, 0, 0], "size": [1, 1, 1], "uv": [float("nan"), 0]},
                description,
                np.zeros(3),
            )

    def test_depth_and_alpha_holes(self):
        # The front surface has a transparent half; the rear green face must show through.
        texture = Image.fromarray(
            np.array(
                [[[255, 0, 0, 255], [0, 0, 0, 0], [0, 255, 0, 255], [0, 255, 0, 255]]],
                dtype=np.uint8,
            )
        )
        geometry = {
            "minecraft:geometry": [
                {
                    "description": {"texture_width": 4, "texture_height": 1},
                    "bones": [
                        {
                            "name": "Root",
                            "cubes": [
                                {
                                    "origin": [-1, 0, 0],
                                    "size": [2, 2, 0.1],
                                    "uv": {"north": {"uv": [0, 0], "uv_size": [2, 1]}},
                                },
                                {
                                    "origin": [-1, 0, 1],
                                    "size": [2, 2, 0.1],
                                    "uv": {"north": {"uv": [2, 0], "uv_size": [2, 1]}},
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        model = Model(geometry, texture)
        image = render(model, width=32, height=32, pitch=0, padding=0, shading="unlit")
        self.assertEqual(image.getpixel((8, 16)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((24, 16)), (0, 255, 0, 255))
        light = np.array([0.0, 2.0, -2.0])
        render(model, width=16, height=16, light_direction=light)
        np.testing.assert_array_equal(light, [0.0, 2.0, -2.0])
        with self.assertRaises(ValueError):
            render(model, width=0)
        with self.assertRaises(ValueError):
            render(model, zoom=float("nan"))
        with self.assertRaises(ValueError):
            render(model, animation="unknown")

    def test_bad_hierarchy_and_asset_paths(self):
        geometry = {
            "minecraft:geometry": [
                {"bones": [{"name": "a", "parent": "b"}, {"name": "b", "parent": "a"}]}
            ]
        }
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            Model(geometry, Image.new("RGBA", (1, 1)))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "ysm.json").write_text(
                json.dumps(
                    {
                        "files": {
                            "player": {
                                "model": {"main": "../private.json"},
                                "texture": ["skin.png"],
                            }
                        }
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "escapes"):
                load_model(folder)
            archive = folder / "bad.zip"
            with ZipFile(archive, "w") as output:
                output.write(folder / "ysm.json", "ysm.json")
            with self.assertRaisesRegex(ValueError, "escapes"):
                load_model(archive)

    @unittest.skipUnless(
        (MODEL / "ysm.json").is_file(),
        "Run npm run build for the real-model integration checks",
    )
    def test_real_model_folder_zip_parameters_and_photo_recovery(self):
        model = load_model(MODEL)
        self.assertEqual(model.cube_count, 292)
        self.assertEqual(model.triangle_count, 3504)
        self.assertEqual(
            len([n for n in model.animations if n.startswith("studio_photo_")]), 6
        )
        self.assertEqual(
            model.pose("run", 0.2)["CustomRunIrisLeft"]["scale"], [1, 1, 1]
        )
        self.assertEqual(
            model.pose("studio_photo_cheeks", 0)["CustomRunIrisLeft"]["scale"],
            [0, 0, 0],
        )
        self.assertEqual(model.pose("idle", 0)["CustomRunIrisLeft"]["scale"], [0, 0, 0])
        options = RenderOptions(width=128, height=192, animation="run", time=0.2)
        image = render(model, options)
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertGreater(np.count_nonzero(np.array(image)[:, :, 3]), 1000)
        np.testing.assert_array_equal(np.array(image), np.array(render(model, options)))
        self.assertFalse(
            np.array_equal(np.array(image), np.array(render(model, options, yaw=90)))
        )
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "model.zip"
            with ZipFile(archive, "w") as output:
                for source in MODEL.rglob("*"):
                    if source.is_file():
                        output.write(
                            source, "character/" + source.relative_to(MODEL).as_posix()
                        )
            zipped = load_model(archive)
            self.assertEqual(
                load_model(archive, manifest=r"character\ysm.json").triangle_count,
                model.triangle_count,
            )
            np.testing.assert_array_equal(
                np.array(image), np.array(render(zipped, options))
            )
            destination = render_to_file(
                model,
                Path(directory) / "nested/out.png",
                width=64,
                height=96,
                background="#f3e7f1",
                supersample=2,
            )
            with Image.open(destination) as result:
                self.assertEqual(result.size, (64, 96))
                self.assertEqual(result.getpixel((0, 0)), (243, 231, 241, 255))
                self.assertEqual(result.info["Model"], model.name)
        raw = load_model(
            MODEL / "models/main.json",
            texture=MODEL / "textures/pink_bun.png",
            animations=MODEL / "animations/main.animation.json",
        )
        self.assertEqual(raw.triangle_count, model.triangle_count)

    @unittest.skipUnless(
        shutil.which("node") and (MODEL / "ysm.json").is_file(),
        "Node + repository model required for cross-language parity",
    )
    def test_matches_existing_three_renderer(self):
        reference = json.loads(
            subprocess.check_output(
                [
                    shutil.which("node"),
                    str(Path(__file__).with_name("reference.mjs")),
                    str(MODEL),
                ],
                text=True,
                encoding="utf-8",
                timeout=60,
            )
        )
        model = load_model(MODEL)
        for frame in reference:
            parameters = {
                "animation": frame["animation"],
                "time": frame["time"],
                "blink": False,
            }
            matrices, mesh = model.bone_matrices(**parameters), model.mesh(**parameters)
            for bone, flat in frame["matrices"].items():
                np.testing.assert_allclose(
                    matrices[bone],
                    np.array(flat).reshape(4, 4).T,
                    atol=1e-6,
                    err_msg=f"{frame['animation']}: {bone}",
                )
            for sample in frame["samples"]:
                np.testing.assert_allclose(
                    mesh.vertices[sample["index"]], sample["position"], atol=1e-6
                )
                np.testing.assert_allclose(
                    mesh.uvs[sample["index"]], sample["uv"], atol=1e-6
                )


if __name__ == "__main__":
    unittest.main()
