import argparse
import json
from pathlib import Path
import sys

from . import load_model, render_to_file


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render a YSM character directly to PNG with Python"
    )
    parser.add_argument(
        "model", help="YSM folder, ZIP, viewer assets folder, or Bedrock geometry JSON"
    )
    parser.add_argument("--out", default="render.png")
    parser.add_argument("--texture", help="Texture path for a direct geometry JSON")
    parser.add_argument(
        "--animations",
        action="append",
        help="Animation JSON; repeat for multiple files",
    )
    parser.add_argument("--manifest", help="Select ysm.json inside a multi-model ZIP")
    parser.add_argument("--skin", type=int, default=0)
    parser.add_argument(
        "--params",
        type=Path,
        help="JSON file of RenderOptions; explicit CLI flags override it",
    )
    parser.add_argument("--list-animations", action="store_true")
    parser.add_argument("--animation", default=argparse.SUPPRESS)
    for name in (
        "time",
        "yaw",
        "pitch",
        "roll",
        "zoom",
        "padding",
        "ambient",
        "head-yaw",
        "head-pitch",
        "speed",
    ):
        parser.add_argument("--" + name, type=float, default=argparse.SUPPRESS)
    for name in ("width", "height", "supersample"):
        parser.add_argument("--" + name, type=int, default=argparse.SUPPRESS)
    parser.add_argument(
        "--background",
        default=argparse.SUPPRESS,
        help="transparent, a color name or #RRGGBB",
    )
    parser.add_argument(
        "--shading", choices=("lit", "unlit"), default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--loop", action=argparse.BooleanOptionalAction, default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--blink", action=argparse.BooleanOptionalAction, default=argparse.SUPPRESS
    )
    args = vars(parser.parse_args(argv))
    model_path, output = args.pop("model"), args.pop("out")
    config, listing = args.pop("params"), args.pop("list_animations")
    loader = {
        key: args.pop(key) for key in ("texture", "animations", "manifest", "skin")
    }
    try:
        model = load_model(model_path, **loader)
        if listing:
            print(
                json.dumps(
                    {
                        name: value.get("animation_length", 1)
                        for name, value in model.animations.items()
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            return 0
        options = json.loads(config.read_text(encoding="utf-8-sig")) if config else {}
        options.update(args)
        if options.get("animation") == "none":
            options["animation"] = None
        print(render_to_file(model, output, **options))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ysm-render: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
