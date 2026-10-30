# SPDX-License-Identifier: GPL-3.0-or-later
"""SAVIOR warehouse classes (paper Table 4.1) with their role, COCO category id and oracle colour (RGB)."""

CLASSES = [
    # name,        role,        coco id, colour (RGB) used in /cam*/segmentation
    ('rack',       'static',    1, (230, 120, 20)),
    ('guard_rail', 'static',    2, (250, 230, 0)),
    ('window',     'static',    3, (90, 200, 255)),
    ('forklift',   'potential', 4, (255, 40, 40)),
    ('box',        'potential', 5, (160, 100, 50)),
    ('pallet',     'potential', 6, (60, 180, 75)),
    ('trolley',    'potential', 7, (180, 60, 220)),
    ('person',     'dynamic',   8, (35, 213, 234)),   # same colour as uHumans2 humans
]
NAMES = [c[0] for c in CLASSES]
ROLE = {c[0]: c[1] for c in CLASSES}
COCO_ID = {c[0]: c[2] for c in CLASSES}
COLOR = {c[0]: c[3] for c in CLASSES}
MOVING_SPEED = 0.05  # m/s: an instance is "moving" in a frame when its true speed exceeds this

# Isaac People characters used (People/Characters/<name>/<name>.usd); their retargeted clips are baked once by
# isaac/bake_people.py into <data>/cache/anims/<name>.usda
CHARACTERS = ['male_adult_construction_01_new', 'male_adult_construction_03', 'male_adult_construction_05_new',
              'male_adult_police_04', 'M_Medical_01', 'F_Business_02', 'F_Medical_01', 'female_adult_police_01_new',
              'female_adult_police_02', 'female_adult_police_03_new']
