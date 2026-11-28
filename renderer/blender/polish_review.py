"""Crop the matching review sectors and package the editable Blender scene."""
import argparse
import html
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image, ImageDraw, ImageFont

from concept_review import SIZE, TILE_LABELS

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / 'output/blender-scenes/monitor-room-polish'
PREVIEW = ROOT / 'dist/viewer/monitor-room-polish'
ARCHIVE = ROOT / 'output/satou-monitor-room-polish.zip'

THAI_LABELS = (
    'หน้าต่างและชั้นซ้าย', 'ชั้นบนและจอฝั่งซ้าย', 'ชั้นบนและจอหลัก',
    'ชั้นขวาและจอโค้ด', 'เคสและจอพื้น', 'คีย์บอร์ดและท่านั่ง',
    'เก้าอี้และพรม', 'ตู้ลิ้นชักและมุมขวา',
)
WEIGHTS = {'composition_shape': 35, 'materials': 25, 'lighting': 20, 'details': 20}
IMAGE_NAMES = ('reference.png', 'room.png', 'floor-detail.png', 'library-angle.png')
SOURCE_MODULES = (
    'polish_room', 'polish_pose', 'polish_hardware', 'polish_review',
    'concept_room', 'concept_architecture', 'concept_furniture', 'concept_library',
    'concept_review', 'check_concept_room', 'monitor_room', 'bookshelves', 'pc_case',
    'sunset_city', 'sunset_landscape', 'convert',
)


def review_image(path):
    width, height = SIZE
    with Image.open(path) as image:
        if image.size not in {SIZE, (width + 1, height)}:
            raise ValueError(f'{path} has size {image.size}, expected {SIZE} or {(width + 1, height)}')
        # Both inputs use native pixels. The wider AI reference has one extra column.
        return image.convert('RGB').crop((0, 0, width, height))


def split(reference_path, render_path, output):
    reference = review_image(reference_path)
    render = review_image(render_path)
    width, height = SIZE
    font = ImageFont.load_default(size=16)
    index = []
    for number, label in enumerate(TILE_LABELS, start=1):
        row, column = divmod(number - 1, 4)
        bounds = (
            width * column // 4, height * row // 2,
            width * (column + 1) // 4, height * (row + 1) // 2,
        )
        tile = output / f'{number:02}'
        tile.mkdir(parents=True, exist_ok=True)
        original, rendered = reference.crop(bounds), render.crop(bounds)
        original.save(tile / 'original.png')
        rendered.save(tile / 'render.png')
        tile_width, tile_height = original.size
        pair = Image.new('RGB', (2 * tile_width + 8, tile_height + 34), '#131522')
        pair.paste(original, (0, 34))
        pair.paste(rendered, (tile_width + 8, 34))
        draw = ImageDraw.Draw(pair)
        draw.text((8, 8), f'{number}  Original', font=font, fill='white')
        draw.text((tile_width + 16, 8), f'{number}  Blender', font=font, fill='white')
        pair.save(tile / 'comparison.png')
        index.append(dict(tile=number, subject=label, pixel_bounds=bounds))
    (output / 'tiles.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')


def review_sections(scene, review):
    rounds = review['rounds']
    if not rounds or review['weights'] != WEIGHTS or review['goal_per_tile'] != 90:
        raise ValueError('Expected completed rounds and the original 90-point visual review rubric')
    sections = []
    for review_round in rounds:
        tiles = review_round['tiles']
        if [tile['tile'] for tile in tiles] != list(range(1, 9)):
            raise ValueError(f"{review_round['label']} must contain tiles 1 through 8 in order")
        folder = review_round['folder']
        if Path(folder).name != folder or folder in {'', '.', '..'}:
            raise ValueError(f'Invalid review folder {folder}')
        figures = []
        for tile, name in zip(tiles, THAI_LABELS):
            score = tile['score']
            subscores = tile['subscores']
            if (len(subscores) != len(WEIGHTS) or sum(subscores) != score
                    or any(not 0 <= value <= limit for value, limit in zip(subscores, WEIGHTS.values()))):
                raise ValueError(f"{folder} tile {tile['tile']} has invalid subscores")
            path = f"reviews/{folder}/{tile['tile']:02}"
            for filename in ('original.png', 'render.png', 'comparison.png'):
                if not (scene / path / filename).is_file():
                    raise FileNotFoundError(scene / path / filename)
            path = html.escape(path)
            note = html.escape(tile['note'])
            figures.append(
                f'<figure><figcaption>{name} <strong>{score}/100</strong></figcaption>'
                f'<a href="{path}/comparison.png">'
                f'<img loading="lazy" src="{path}/comparison.png" alt="{name} เทียบต้นฉบับกับ Blender"></a>'
                f'<p>{note}</p><p><a href="{path}/original.png">ต้นฉบับ</a> · '
                f'<a href="{path}/render.png">เรนเดอร์</a></p></figure>'
            )
        average = sum(tile['score'] for tile in tiles) / len(tiles)
        title = html.escape(review_round['label'])
        expanded = ' open' if review_round is rounds[-1] else ''
        sections.append(
            f'<details{expanded}><summary>{title} · {average:.1f}/100</summary>'
            f'<div class="grid">{"".join(figures)}</div></details>'
        )
    return ''.join(sections)


def write_gallery(scene, review):
    sections = review_sections(scene, review)
    page = '''<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ฉากห้อง Blender เทียบภาพอ้างอิง</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0b0e15;color:#e7edf8;font:16px/1.55 system-ui,sans-serif}
main{max-width:1460px;margin:auto;padding:28px clamp(16px,4vw,48px)}
h1{font-size:clamp(27px,4vw,44px);line-height:1.25}
a{color:#a8d2ff;text-underline-offset:4px}
.files{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
figure{margin:0;border:1px solid #313b4d;border-radius:9px;overflow:hidden;background:#151a26}
figcaption,p{margin:0;padding:10px 14px}
figcaption strong{float:right}
figure img{width:100%;display:block}
details,section{margin:20px 0}
summary{cursor:pointer;padding:13px;background:#232d3d;margin-bottom:12px;border-radius:7px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body><main>
<h1>ฉากห้อง Blender เทียบภาพอ้างอิง</h1>
<div class="files">
<a href="room.blend" download>ดาวน์โหลดฉาก Blender</a>
<a href="reference.png">ภาพอ้างอิงเต็ม</a>
<a href="validation.json">ผลตรวจไฟล์ Blender</a>
<a href="reviews/scores.json">คะแนนรายช่อง</a>
</div>
<figure><a href="room.png"><img src="room.png" alt="ภาพเรนเดอร์หลักของห้อง"></a>
<figcaption>ภาพเรนเดอร์มุมหลัก</figcaption></figure>
<section class="grid">
<figure><a href="floor-detail.png"><img loading="lazy" src="floor-detail.png" alt="จอคู่ เคส คีย์บอร์ด และตัวละคร"></a>
<figcaption>มุมชุดคอมพื้น</figcaption></figure>
<figure><a href="library-angle.png"><img loading="lazy" src="library-angle.png" alt="โต๊ะและชั้นหนังสือ"></a>
<figcaption>มุมโต๊ะและชั้นหนังสือ</figcaption></figure>
</section>
<h2>ผลตรวจ 8 ช่องในแต่ละรอบ</h2>
<p>คะแนนประเมินด้วยสายตาจากองค์ประกอบและรูปทรง 35 คะแนน วัสดุ 25 คะแนน แสงและสี 20 คะแนน และรายละเอียด 20 คะแนน</p>
'''
    (scene / 'index.html').write_text(page + sections + '</main></body></html>\n', encoding='utf-8')

    rounds = review['rounds']
    final = [tile['score'] for tile in rounds[-1]['tiles']]
    (scene / 'README.md').write_text(f'''# ฉากห้อง Blender เทียบภาพอ้างอิง

เปิด room.blend ใน Blender เพื่อแก้ไขฉาก ภาพเรนเดอร์อยู่ใน room.png, floor-detail.png และ library-angle.png ฉากตั้งไว้ที่ Cycles GPU หากใช้ NVIDIA ให้เลือก OptiX ใน Preferences ก่อนเรนเดอร์ด้วย F12

เปิด index.html เพื่อดูคะแนนและภาพเทียบทั้ง 8 ช่อง ภาพถูกตัดเป็นกริด 4 × 2 ตรงพิกัดเดียวกัน ภาพอ้างอิงกว้างกว่า 1 พิกเซล จึงตัดเฉพาะคอลัมน์ขวาสุดก่อนแบ่งกริด

ตรวจ {len(rounds)} รอบ รอบล่าสุดได้เฉลี่ย {sum(final) / len(final):.1f}/100 และต่ำสุด {min(final)}/100 ผ่านเป้าหมาย 90 คะแนน {sum(score >= 90 for score in final)} จาก 8 ช่อง คะแนนนี้มาจากการประเมินด้วยสายตา

source/ มีสคริปต์แก้ฉากและสคริปต์ตัดภาพตรวจ การสร้างฉากซ้ำใช้ room.blend ของฉาก monitor-room-concept ในโปรเจกต์เดิม พื้นผิวของฉากพร้อมใช้ในไฟล์ Blender เครดิตตัวละครอยู่ใน CHARACTER-ATTRIBUTION.md และ Text blocks ของฉาก
''', encoding='utf-8')


def pack():
    review = json.loads((SCENE / 'reviews/scores.json').read_text(encoding='utf-8'))
    validation = json.loads((SCENE / 'validation.json').read_text(encoding='utf-8'))
    if validation['status'] != 'passed':
        raise ValueError('Run Blender validation before packaging')
    names = (*IMAGE_NAMES, 'room.blend', 'validation.json')
    for name in names:
        if not (SCENE / name).is_file():
            raise FileNotFoundError(SCENE / name)
    write_gallery(SCENE, review)
    source = SCENE / 'source'
    source.mkdir(exist_ok=True)
    for module in SOURCE_MODULES:
        module_file = f'{module}.py'
        shutil.copy2(Path(__file__).parent / module_file, source / module_file)
    origin = SCENE.parent / 'monitor-room-rgb'
    attribution = {
        'CHARACTER-ATTRIBUTION.md': origin / 'CHARACTER-ATTRIBUTION.md',
        'library/satou-aunt.validation.json': origin / 'library/satou-aunt.validation.json',
        'vendor/winefox-jk/ysm.json': ROOT / 'vendor/winefox-jk/ysm.json',
        'LICENSE': ROOT / 'LICENSE',
    }
    for name, original in attribution.items():
        target = SCENE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

    paths = [SCENE / name for name in (*names, 'index.html', 'README.md', *attribution)]
    paths.extend(source / f'{module}.py' for module in SOURCE_MODULES)
    paths.append(SCENE / 'reviews/scores.json')
    for round_info in review['rounds']:
        folder = SCENE / 'reviews' / round_info['folder']
        paths.append(folder / 'tiles.json')
        for tile in round_info['tiles']:
            tile_folder = folder / f"{tile['tile']:02}"
            paths.extend(tile_folder / name for name in ('original.png', 'render.png', 'comparison.png'))
    paths.extend(sorted((SCENE / 'textures').glob('*.png')))
    temporary = ARCHIVE.with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipped:
            for path in paths:
                zipped.write(path, path.relative_to(SCENE.parent))
        with zipfile.ZipFile(temporary) as zipped:
            broken = zipped.testzip()
            if broken is not None:
                raise ValueError(f'Archive failed a CRC check on {broken}')
        temporary.replace(ARCHIVE)
    finally:
        temporary.unlink(missing_ok=True)

    for path in paths:
        target = PREVIEW / path.relative_to(SCENE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    print(f'PACKED {ARCHIVE} ({len(paths)} files)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    crop = actions.add_parser('split', help='Write eight native-pixel original/render crop pairs')
    crop.add_argument('--reference', type=Path, required=True)
    crop.add_argument('--render', type=Path, required=True)
    crop.add_argument('--output', type=Path, required=True)
    actions.add_parser('pack', help='Create the editable scene archive and offline viewer')
    args = parser.parse_args()
    if args.action == 'split':
        split(args.reference, args.render, args.output)
    else:
        pack()


if __name__ == '__main__':
    main()
