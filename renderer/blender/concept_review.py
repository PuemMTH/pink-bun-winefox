"""Prepare the supplied concept and make eight corresponding review tiles."""
import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont

SIZE = (1671, 941)
TILE_LABELS = (
    'Left window and upper library', 'Upper ledge and left monitors',
    'Upper ledge and main monitors', 'Right library and code display',
    'Computer case and left floor display', 'Floor reader and keyboard',
    'Chair, seated player and rug', 'Desk drawers and right foreground',
)


def prepare(reference, folder, forest=None):
    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(reference) as image:
        assert image.size == SIZE, image.size
        shutil.copy2(reference, folder / 'reference.png')
        textures = folder / 'textures'
        textures.mkdir(exist_ok=True)
        # Isolate the supplied artwork inside each screen for its UV surface.
        left = (186, 693, 191, 809, 374, 791, 374, 679)
        right = (386, 678, 388, 791, 557, 780, 552, 675)
        for label, quad in [('left', left), ('right', right)]:
            image.convert('RGB').transform(
                (640, 360), Image.Transform.QUAD, quad, Image.Resampling.BICUBIC
            ).save(textures / f'floor-{label}.png')
        # This swatch contains only the game sky inside the upper center display.
        # Its lower game view uses the separate in-game capture beneath this sample.
        image.convert('RGB').transform(
            (640, 206), Image.Transform.QUAD,
            (817, 256, 818, 315, 993, 318, 993, 262), Image.Resampling.BICUBIC,
        ).save(textures/'center-screen-sky.png')
    if forest:
        with Image.open(forest) as capture:
            width, height = capture.size
            capture.crop((round(width*.19),0,round(width*.98),round(height*.81))).resize(
                (960,540), Image.Resampling.LANCZOS).save(textures/'game-forest-clear.png')


def split(original, render, output):
    output.mkdir(parents=True, exist_ok=True)
    width, height = SIZE
    reference = Image.open(original).convert('RGB')
    result = Image.open(render).convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)
    assert reference.size == SIZE
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    index = []
    for i, label in enumerate(TILE_LABELS):
        row, col = divmod(i, 4)
        bounds = (width*col//4, height*row//2, width*(col+1)//4, height*(row+1)//2)
        tile = output / f'{i+1:02}'
        tile.mkdir(exist_ok=True)
        a, b = (im.crop(bounds) for im in (reference, result))
        a.save(tile/'original.png')
        b.save(tile/'render.png')
        w, h = a.size
        pair = Image.new('RGB', (2*w+8, h+34), '#131522')
        pair.paste(a, (0, 34))
        pair.paste(b, (w+8, 34))
        draw = ImageDraw.Draw(pair)
        draw.text((8, 5), f'{i+1}  Original', font=font, fill='white')
        draw.text((w+16, 5), f'{i+1}  Blender', font=font, fill='white')
        pair.save(tile/'comparison.png')
        index.append(dict(tile=i+1, subject=label, pixel_bounds=bounds))
    (output/'tiles.json').write_text(json.dumps(index, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'split'])
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', type=Path)
    parser.add_argument('--forest', type=Path, help='Additional in-game capture for the center upper monitor')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.reference, args.output, args.forest)
    else:
        split(args.reference, args.render, args.output)


if __name__ == '__main__':
    main()
