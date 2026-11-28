"""Copy actual in-game captures and draw two code-editor pages from our source."""
from pathlib import Path
import hashlib
import io
import json
import keyword
import shutil
import tokenize

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/monitor-screens'
CAPTURES = Path.home() / 'AppData/Roaming/ModrinthApp/profiles/CC/screenshots'
SELECTED = ['13.56.35', '13.56.51', '13.59.02', '13.59.22', '13.59.30', '13.59.34', '13.59.37', '13.59.03']


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = json.loads((OUT / 'SOURCES.json').read_text(encoding='utf-8'))
    sources = [s for s in sources if not s['file'].startswith(('game-', 'code-'))]
    for i, time in enumerate(SELECTED, 1):
        source = CAPTURES / f'2026-11-27_{time}.png'
        dest = OUT / f'game-{i:02}.png'
        shutil.copy2(source, dest)
        sources.append(dict(file=dest.name, source=source.name, owner='User in-game screenshot; Minecraft Mojang/Microsoft'))
    text = (ROOT / 'renderer/blender/monitor_room.py').read_text(encoding='utf-8')
    lines = text.splitlines()
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 19)
    ui = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
    for page, start in enumerate([67, 153], 1):
        im = Image.new('RGB', (1200, 1280), '#10151f')
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1200, 47), fill='#202a3b')
        d.text((24, 10), 'SATOU STUDIO  /  monitor_room.py', font=ui, fill='#dce9f9')
        d.rectangle((0, 48, 1200, 83), fill='#172030')
        d.text((23, 53), f'renderer  >  blender  >  monitor_room.py     page {page}', font=font, fill='#879bb5')
        char_width = d.textlength('M', font=font)
        for index in range(start, min(start + 48, len(lines))):
            y = 98 + (index-start)*23
            d.text((16, y), str(index+1).rjust(3), font=font, fill='#526780')
            d.text((75, y), lines[index][:91], font=font, fill='#c6d3e4')
            for tok in tokens:
                if tok.start[0] != index+1 or tok.end[0] != index+1: continue
                color = None
                if tok.type == tokenize.STRING: color = '#a8d69b'
                elif tok.type == tokenize.COMMENT: color = '#617b91'
                elif tok.type == tokenize.NUMBER: color = '#eead76'
                elif tok.type == tokenize.NAME and keyword.iskeyword(tok.string): color = '#cb9bf0'
                elif tok.type == tokenize.OP: color = '#74c4d7'
                if color and tok.start[1] < 91:
                    d.text((75 + tok.start[1]*char_width, y), tok.string[:91-tok.start[1]], font=font, fill=color)
        d.rectangle((0, 1240, 1200, 1280), fill='#254864')
        d.text((22, 1248), f'main    Python  |  UTF-8    Ln {start+1}    Blender / Cycles / OptiX', font=font, fill='#d5e9f8')
        dest = OUT / f'code-{page:02}.png'
        im.save(dest)
        sources.append(dict(file=dest.name, source='renderer/blender/monitor_room.py', owner='Project source rendered as a code editor; no terminal or credentials'))
    for s in sources:
        s['sha256'] = hashlib.sha256((OUT/s['file']).read_bytes()).hexdigest()
    (OUT/'SOURCES.json').write_text(json.dumps(sources, indent=2)+'\n', encoding='utf-8')
    assert len({s['sha256'] for s in sources if s['file'].startswith('game-')}) == 8
    print('PREPARED_8_UNIQUE_GAME_CAPTURES_AND_2_CODE_PAGES')


if __name__ == '__main__': main()
