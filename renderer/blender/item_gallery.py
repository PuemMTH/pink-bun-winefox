"""Check item deliverables and publish a local index of the individual files."""
import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'dist/scene-items'
SPECS = Path(__file__).with_name('item_specs')
PACK = ROOT / 'output/scene-item-builds'
GROUPS = {'room': 'ส่วนประกอบห้อง', 'case': 'เคสคอมและเฟอร์นิเจอร์',
          'decor': 'ชั้นหนังสือและของตกแต่ง', 'peripherals': 'จอและอุปกรณ์'}
VIEWS = ('RIGHT', 'LEFT', 'FRONT', 'BACK', 'BUTTOM', 'TOP')


def specs(group):
    return json.loads((SPECS / f'{group}.json').read_text(encoding='utf-8-sig'))


def make_review(group):
    DATA.mkdir(parents=True, exist_ok=True)
    entries = [entry for entry in specs(group) if (PACK/entry['id']/'item.json').exists()]
    font = ImageFont.truetype('arial.ttf', 14)
    tile, row = 132, 155
    for start in range(0, len(entries), 5):
        batch = entries[start:start+5]
        image = Image.new('RGB', (len(VIEWS)*tile, 24+len(batch)*row), '#4a484c')
        draw = ImageDraw.Draw(image)
        for j, view in enumerate(VIEWS):
            draw.text((j*tile+5,4), view, fill='white', font=font)
        for i, entry in enumerate(batch):
            y = 24+i*row
            draw.text((5,y), entry['id'], fill='#ffd493', font=font)
            for j, view in enumerate(VIEWS):
                with Image.open(PACK / entry['id'] / f'{view}.png') as source:
                    shown = source.convert('RGBA').resize((tile-4,tile-4), Image.Resampling.LANCZOS)
                image.paste(shown, (j*tile+2,y+21), shown)
        image.save(DATA / f'review-{group}-{1+start//5}.jpg', quality=88)


def verify(folder):
    assert (folder/'model.blend').stat().st_size > 10000, folder
    expected = json.loads((folder/'item.json').read_text(encoding='utf-8'))
    assert expected['model_objects'] > 0
    for view in VIEWS:
        with Image.open(folder/f'{view}.png') as file:
            assert file.size == (900, 900) and file.mode == 'RGBA', (folder, view)
            # A centered isolated object has transparent corners and nonempty silhouette.
            alpha = file.getchannel('A')
            box = alpha.getbbox()
            assert box and box[0] > 1 and box[1] > 1 and box[2] < 899 and box[3] < 899, (folder, view, box)


def publish():
    scores = json.loads((DATA/'qa-results.json').read_text(encoding='utf-8-sig'))
    lookup = {score['id']:score for score in scores}
    assert len(lookup) == 41
    for record in scores:
        weights = {'shape':35, 'materials':25, 'details':40}
        assert record['subscores'].keys() == weights.keys()
        assert record['score'] == sum(record['subscores'].values())
        assert all(0 <= point <= weights[key] for key,point in record['subscores'].items())
    elements = []
    for group, title in GROUPS.items():
        cards = []
        for item in specs(group):
            slug = item['id']
            verify(PACK/slug)
            rating = lookup[slug]
            angles = ''.join(f'<a href="{slug}/{v}.png"><img loading="lazy" src="{slug}/{v}.png" alt="{v}">{v}</a>'
                             for v in VIEWS)
            details = ''.join(f'<li>{html.escape(d)}</li>' for d in item['details'])
            thumb = f'<img class="thumb" src="{slug}/FRONT.png" loading="lazy" alt="">'
            cards.append(f'<article id="{slug}"><details><summary>{thumb}<span>{html.escape(item["title"])}</span>'
                         f'<strong>{rating["score"]}/100</strong></summary><div class="content">'
                         f'<a href="{slug}/model.blend">ไฟล์ Blender</a> · <a href="{slug}/item.json">ข้อมูลชิ้นงาน</a>'
                         f'<div class="angles">{angles}</div><p>{html.escape(rating["note"])}</p>'
                         f'<ul>{details}</ul></div></details></article>')
        elements.append(f'<section><h2>{title}</h2>{"".join(cards)}</section>')
    passed = sum(record['score'] >= 90 for record in scores)
    (PACK/'quality-check.json').write_text(json.dumps(scores, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    page = '''<!doctype html><html lang="th"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>โมเดลแยกชิ้นจากฉากห้องคอม</title>
<style>
:root{color-scheme:dark;background:#16151a;color:#f2e9e2;font:16px/1.55 system-ui,sans-serif}
main{width:min(1120px,94vw);margin:32px auto}a{color:#ffd194;text-underline-offset:.15em}
section{margin:2rem 0}article{border-bottom:1px solid #42383e}summary{cursor:pointer;display:flex;align-items:center;gap:.9rem}
summary span{flex:1}.thumb{width:72px;height:72px;object-fit:contain;background:#424146}
.content{padding:15px}.angles{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:8px;margin:14px 0}
.angles a{text-align:center}.angles img{display:block;width:100%;background:radial-gradient(#5a585b,#3c3a41);border-radius:.35rem}
</style><main><h1>โมเดลแยกชิ้นจากฉากห้องคอม</h1>
<p>เปิดแต่ละรายการเพื่อดูไฟล์ Blender ภาพทั้งหกด้าน และผลตรวจ รายการ BUTTOM คือภาพด้านใต้</p>
<p>ผู้ตรวจให้คะแนนจากรูปทรง 35 คะแนน วัสดุ 25 คะแนน และรายละเอียดตาม checklist 40 คะแนน</p>
<p><a href="../scene-item-reference/index.html">Checklist ต้นทาง ภาพอ้างอิง และเท็กซ์เจอร์</a></p>
'''
    page += f'<p>ผ่านเกณฑ์ 90/100 จำนวน {passed} จาก 41 รายการ · <a href="quality-check.json">คะแนนรายชิ้น</a></p>'
    (PACK/'index.html').write_text(page+''.join(elements)+'</main></html>\n', encoding='utf-8')
    print(f'VERIFIED {len(scores)} items / {len(scores)*6} images / {passed} pass 90', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', action='store_true')
    args = parser.parse_args()
    if args.review:
        for group in GROUPS:
            make_review(group)
    else:
        publish()
