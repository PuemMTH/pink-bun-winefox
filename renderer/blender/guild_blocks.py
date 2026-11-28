"""Original unit-block guild city. Coordinates are Blender X/Y ground, Z up."""

import random

PALETTE = {
    'stone_bricks': (0.4, 0.43, 0.45),
    'cracked_stone_bricks': (0.33, 0.37, 0.39),
    'mossy_stone_bricks': (0.33, 0.41, 0.32),
    'cobblestone': (0.3, 0.33, 0.35),
    'smooth_stone': (0.56, 0.55, 0.52),
    'polished_andesite': (0.4, 0.42, 0.42),
    'calcite': (0.78, 0.72, 0.57),
    'white_terracotta': (0.68, 0.57, 0.48),
    'oak_planks': (0.47, 0.3, 0.15),
    'spruce_planks': (0.29, 0.18, 0.1),
    'dark_oak_planks': (0.17, 0.1, 0.065),
    'stripped_dark_oak_log': (0.2, 0.12, 0.07),
    'bricks': (0.47, 0.21, 0.15),
    'terracotta': (0.47, 0.24, 0.17),
    'red_terracotta': (0.45, 0.13, 0.08),
    'cyan_terracotta': (0.16, 0.28, 0.28),
    'blue_terracotta': (0.16, 0.21, 0.3),
    'light_blue_wool': (0.25, 0.53, 0.67),
    'blue_wool': (0.055, 0.15, 0.3),
    'yellow_wool': (0.91, 0.63, 0.15),
    'white_wool': (0.83, 0.78, 0.65),
    'red_wool': (0.55, 0.12, 0.1),
    'yellow_stained_glass': (0.83, 0.57, 0.19),
    'glass': (0.31, 0.53, 0.58),
    'glowstone': (0.98, 0.61, 0.23),
    'grass_block': (0.2, 0.37, 0.12),
    'dirt': (0.29, 0.18, 0.1),
    'oak_log': (0.25, 0.16, 0.075),
    'oak_leaves': (0.12, 0.3, 0.08),
    'spruce_leaves': (0.075, 0.23, 0.11),
    'water': (0.1, 0.37, 0.54),
    'black_concrete': (0.028, 0.035, 0.045),
    'gold_block': (0.85, 0.56, 0.12),
}


def build_city():
    rng = random.Random(714)
    blocks = {}

    def fill(x0, x1, y0, y1, z0, z1, state):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    if state:
                        blocks[x, y, z] = state
                    else:
                        blocks.pop((x, y, z), None)

    def walls(x0, x1, y0, y1, z0, z1, state):
        fill(x0, x1, y0, y0, z0, z1, state)
        fill(x0, x1, y1, y1, z0, z1, state)
        fill(x0, x0, y0, y1, z0, z1, state)
        fill(x1, x1, y0, y1, z0, z1, state)

    def roof(x0, x1, y0, y1, base, state):
        for step in range((x1 - x0) // 2 + 1):
            a, b = x0 + step, x1 - step
            fill(a, a, y0, y1, base + step, base + step, state)
            fill(b, b, y0, y1, base + step, base + step, state)
            if a < b:
                for y in [y0 + 1, y1 - 1]:
                    fill(a + 1, b - 1, y, y, base + step, base + step, 'calcite')
        ridge = (x0 + x1) // 2
        fill(ridge, ridge, y0, y1, base + (x1 - x0) // 2 + 1,
             base + (x1 - x0) // 2 + 1, 'dark_oak_planks')

    def house(cx, cy, width, depth, height, roof_state, plaster='calcite'):
        x0, x1 = cx - width // 2, cx + width // 2
        y0, y1 = cy - depth // 2, cy + depth // 2
        fill(x0, x1, y0, y1, 0, 0, 'stone_bricks')
        walls(x0, x1, y0, y1, 1, 3, 'stone_bricks')
        walls(x0, x1, y0, y1, 4, height, plaster)
        for x in [x0, x1, cx]:
            for y in [y0, y1]:
                fill(x, x, y, y, 1, height, 'stripped_dark_oak_log')
        for z in range(4, height + 1, 4):
            walls(x0, x1, y0, y1, z, z, 'dark_oak_planks')
            fill(x0 + 1, x1 - 1, y0 + 1, y1 - 1, z, z, 'oak_planks')
        for y in [y0, y1]:
            for x in range(x0 + 2, x1, 4):
                for z in range(2, height - 1, 4):
                    fill(x, min(x + 1, x1 - 1), y, y, z, z + 1, 'glass')
        for x in [x0, x1]:
            for y in range(y0 + 2, y1, 4):
                for z in range(2, height - 1, 4):
                    fill(x, x, y, min(y + 1, y1 - 1), z, z + 1, 'glass')
        fill(cx, cx + 1, y1, y1, 1, 3, 'spruce_planks')
        roof(x0 - 1, x1 + 1, y0 - 1, y1 + 1, height + 1, roof_state)
        fill(x0 + 2, x0 + 3, y0 + 2, y0 + 3, height, height + width // 2 + 3, 'bricks')
        fill(x0 + 1, x0 + 4, y0 + 1, y0 + 4, height + width // 2 + 3,
             height + width // 2 + 3, 'stone_bricks')

    # Roads and square sit on the same one-metre block grid as the buildings.
    fill(-58, 58, -84, 38, -2, -2, 'dirt')
    fill(-58, 58, -84, 38, -1, -1, 'grass_block')
    for x in range(-18, 19):
        for y in range(-9, 32):
            blocks[x, y, -1] = rng.choice(['stone_bricks'] * 5 + ['cobblestone', 'polished_andesite'])
    for center in [-28, 28]:
        for x in range(center - 4, center + 5):
            for y in range(-76, 32):
                blocks[x, y, -1] = rng.choice(['cobblestone', 'stone_bricks', 'polished_andesite'])
    fill(-55, 55, -41, -34, -1, -1, 'cobblestone')

    # Monumental guild hall with two street-facing towers and a block-letter sign.
    house(0, -23, 23, 25, 14, 'blue_terracotta')
    for x in [-15, 15]:
        house(x, -21, 7, 17, 12, 'blue_terracotta')
        walls(x - 3, x + 3, -13, -7, 0, 18, 'stone_bricks')
        for z in [4, 9, 14, 18]:
            walls(x - 4, x + 4, -14, -6, z, z, 'dark_oak_planks')
        for z in [6, 11, 15]:
            fill(x - 1, x + 1, -7, -7, z, z + 2, 'yellow_stained_glass')
        roof(x - 5, x + 5, -15, -5, 19, 'blue_terracotta')
        fill(x, x, -10, -10, 25, 27, 'stripped_dark_oak_log')
        fill(x + 1, x + 3, -10, -10, 26, 27, 'blue_wool')
        blocks[x + 2, -10, 26] = 'yellow_wool'

    fill(-12, 12, -11, -7, 0, 0, 'stone_bricks')
    fill(-8, 8, -10, -7, 1, 1, 'stone_bricks')
    # An open, stepped arch with a dark interior behind the entrance.
    fill(-3, 3, -11, -10, 1, 6, None)
    fill(-2, 2, -11, -10, 7, 7, None)
    fill(-4, -4, -10, -10, 1, 6, 'stripped_dark_oak_log')
    fill(4, 4, -10, -10, 1, 6, 'stripped_dark_oak_log')
    fill(-3, 3, -10, -10, 7, 7, 'stripped_dark_oak_log')
    fill(-2, 2, -10, -10, 8, 8, 'stripped_dark_oak_log')
    fill(-3, 3, -15, -15, 1, 7, 'black_concrete')
    for x in [-8, 7]:
        fill(x, x + 1, -11, -11, 2, 6, 'yellow_stained_glass')
        fill(x - 1, x + 2, -10, -10, 1, 1, 'dark_oak_planks')
    fill(-10, 10, -10, -10, 9, 15, 'blue_wool')
    glyphs = {'G': ['111', '100', '101', '101', '111'],
              'U': ['101', '101', '101', '101', '111'],
              'I': ['111', '010', '010', '010', '111'],
              'L': ['100', '100', '100', '100', '111'],
              'D': ['110', '101', '101', '101', '110']}
    for letter, char in enumerate('GUILD'):
        for row, pattern in enumerate(glyphs[char]):
            for col, active in enumerate(pattern):
                if active == '1':
                    blocks[9 - letter * 4 - col, -9, 14 - row] = 'yellow_wool'
    for x in [-10, 10]:
        fill(x, x, -9, -9, 9, 15, 'gold_block')
    for x in [-19, 19]:
        fill(x, x, -7, -7, 1, 6, 'stripped_dark_oak_log')
        fill(x - 1, x + 1, -7, -7, 5, 8, 'red_wool')
        blocks[x, -6, 6] = 'yellow_wool'

    # Deep streets and three receding layers of original houses.
    roofs = ['red_terracotta', 'cyan_terracotta', 'spruce_planks', 'terracotta']
    count = 0
    for y in [15, -6, -27, -49, -68]:
        for x in [-46, -37, 37, 47]:
            house(x, y, 7 if x % 2 else 9, 11, 7 + rng.choice([0, 4, 8]),
                  roofs[count % 4], 'calcite' if count % 3 else 'white_terracotta')
            count += 1
    for x in [-15, 0, 15]:
        house(x, -56, 9, 13, 11 + (x == 0) * 4, roofs[count % 4])
        count += 1

    # Perimeter ramparts and towers make the town read as a large district.
    walls(-57, 57, -81, 28, 0, 5, 'stone_bricks')
    for x in range(-57, 58, 3):
        blocks[x, -81, 6] = 'stone_bricks'
    for y in range(-81, 28, 3):
        for x in [-57, 57]:
            blocks[x, y, 6] = 'stone_bricks'
    for x in [-55, -25, 25, 55]:
        walls(x - 3, x + 3, -83, -77, 0, 13, 'stone_bricks')
        fill(x - 4, x + 4, -84, -76, 13, 13, 'stone_bricks')
        for a in range(x - 4, x + 5, 2):
            for y in [-84, -76]:
                blocks[a, y, 14] = 'stone_bricks'
    # A foreground wall opening keeps the camera and approach road clear.
    fill(-12, 12, 28, 28, 0, 6, None)

    def tree(x, y, height):
        fill(x, x, y, y, 0, height, 'oak_log')
        for z, radius in [(height - 2, 2), (height - 1, 3), (height, 3), (height + 1, 2), (height + 2, 1)]:
            for a in range(-radius, radius + 1):
                for b in range(-radius, radius + 1):
                    if abs(a) + abs(b) < radius * 2:
                        blocks[x + a, y + b, z] = 'oak_leaves'
    for x, y in [(-22, 13), (22, 13), (-22, -29), (23, -33), (-48, 31), (45, 31), (-14, 23), (16, 24)]:
        tree(x, y, 6 + abs(x) % 3)

    lamps = []
    for x in [-9, 9]:
        for y in [0, 20]:
            fill(x, x, y, y, 0, 3, 'stripped_dark_oak_log')
            fill(x - 1, x + 1, y - 1, y + 1, 4, 4, 'dark_oak_planks')
            blocks[x, y, 3] = 'glowstone'
            lamps.append((x + 0.5, y + 0.5, 3.3))
    for x, y, tint in [(-17, 2, 'red_wool'), (16, 2, 'blue_wool'), (-17, 20, 'yellow_wool')]:
        for a in [x, x + 5]:
            fill(a, a, y, y + 3, 0, 3, 'stripped_dark_oak_log')
        for a in range(6):
            fill(x + a, x + a, y - 1, y + 4, 4, 4, tint if a % 2 else 'white_wool')
        fill(x, x + 5, y + 1, y + 2, 1, 1, 'oak_planks')
    for x, y in [(-10, 8), (-11, 7), (10, 7), (11, 8)]:
        fill(x, x + 1, y, y + 1, 0, 1, 'spruce_planks')
    # Low fountain left of the central approach.
    walls(-12, -6, -2, 4, 0, 0, 'stone_bricks')
    fill(-11, -7, -1, 3, 0, 0, 'water')
    fill(-9, -9, 1, 1, 0, 3, 'stone_bricks')
    blocks[-9, 1, 4] = 'water'
    return blocks, {'houses': count, 'lamps': lamps, 'guild_front': -10,
                    'size_blocks': [117, 123, 30]}


def city_entrance(blocks, details):
    """Replace the draft guild signage with a town hall and build a city gate."""
    def fill(x0, x1, y0, y1, z0, z1, state):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    if state:
                        blocks[x, y, z] = state
                    else:
                        blocks.pop((x, y, z), None)

    fill(-10, 10, -10, -9, 9, 15, None)
    fill(-2, 2, -11, -11, 9, 12, 'glass')
    fill(-58, 58, 39, 56, -2, -2, 'dirt')
    fill(-58, 58, 39, 56, -1, -1, 'grass_block')
    fill(-7, 7, 29, 56, -1, -1, 'stone_bricks')

    # Open stepped stone arch, flanked by roofed watchtowers.
    fill(-7, 7, 27, 30, 0, 12, 'stone_bricks')
    fill(-5, 5, 27, 30, 0, 8, None)
    fill(-4, 4, 27, 30, 9, 9, None)
    fill(-3, 3, 27, 30, 10, 10, None)
    fill(-7, 7, 27, 30, 13, 13, 'dark_oak_planks')
    for x in [-11, 11]:
        for a in range(x - 3, x + 4):
            for y in range(24, 32):
                for z in range(14):
                    if a in [x - 3, x + 3] or y in [24, 31] or z in [0, 6, 13]:
                        blocks[a, y, z] = 'stone_bricks'
        for a in [x - 3, x + 3]:
            fill(a, a, 31, 31, 1, 13, 'stripped_dark_oak_log')
        fill(x - 1, x + 1, 31, 31, 7, 9, 'glass')
        fill(x - 4, x + 4, 23, 32, 13, 13, 'dark_oak_planks')
        for step in range(5):
            for a in [x - 4 + step, x + 4 - step]:
                fill(a, a, 23, 32, 14 + step, 14 + step, 'red_terracotta')
            if step < 4:
                fill(x - 3 + step, x + 3 - step, 24, 24, 14 + step, 14 + step, 'calcite')
                fill(x - 3 + step, x + 3 - step, 31, 31, 14 + step, 14 + step, 'calcite')
        fill(x - 1, x + 1, 32, 32, 3, 6, 'blue_wool')
        blocks[x, 33, 5] = 'yellow_wool'
    for x in range(-7, 8, 2):
        blocks[x, 30, 14] = 'stone_bricks'
    for x in [-8, 8]:
        fill(x, x, 37, 37, 0, 3, 'stripped_dark_oak_log')
        fill(x - 1, x + 1, 36, 38, 4, 4, 'dark_oak_planks')
        blocks[x, 37, 3] = 'glowstone'
        details['lamps'].append((x + 0.5, 37.5, 3.3))
    details.pop('guild_front', None)
    details['entrance_front'] = 31
    details['size_blocks'] = [117, 141, 30]
    return blocks, details
