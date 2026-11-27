"""Run after installing ysm-render: python examples/render_character.py MODEL_PATH."""

from pathlib import Path
import sys
from ysm_render import load_model, render_to_file

model = load_model(sys.argv[1])
output = Path("renders")
for name, parameters in {
    "portrait": {"animation": "studio_photo_cheeks", "yaw": 15},
    "running": {"animation": "run", "time": 0.2, "yaw": 25, "pitch": 8},
    "side": {"animation": "idle", "time": 1, "yaw": 90},
}.items():
    print(
        render_to_file(
            model, output / f"{name}.png", width=512, height=768, **parameters
        )
    )
