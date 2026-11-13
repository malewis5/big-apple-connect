"""Build the demo video scene: the box at work in a miniature NYC apartment.

A cutaway diorama of a modest, charming New York City living room: brick,
radiator, fire escape, a NYCHA tower outside the window. The box is plugged
into the router, days and nights pass, results build up beside the promise,
and a look ahead shows the box tuning the Wi-Fi.

Run from the repository root:

    BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
    $BLENDER -b -P design/demo/build_demo.py -- --aspect wide --stills 1,300,600
    $BLENDER -b -P design/demo/build_demo.py -- --aspect tall --draft --animation
    $BLENDER -b -P design/demo/build_demo.py -- --aspect wide --animation

Options after `--`:
    --aspect wide|tall   16:9 or 9:16 (default wide)
    --draft              EEVEE, 720p, every other frame; otherwise Cycles, 1080p
    --stills F,F,...     render these frames to out/<aspect>-<quality>/still-FFFF.png
    --animation          render every frame to out/<aspect>-<quality>/frames/
    --res N              short side in pixels (default 720 draft, 1080 final)
    --samples N          Cycles samples (default 64; denoised, it matches 128)

Writes demo-<aspect>.blend and the renders to design/demo/out/, which git
ignores. make_video.sh turns the frames and captions into a video.

Built in metres. X runs along the back wall (window to the right), Y from the
open front (-Y) to the back wall (+Y), Z up. The camera looks in from the
open front-right corner.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "out")
BOX_SCRIPT = os.path.join(ROOT, "design", "box", "build_box.py")
FONT_DIR = os.path.expanduser("~/Library/Fonts")

FPS = 30
FRAMES = 1350  # 45 seconds

# The story, in frames. Captions in build_captions.py follow the same beats.
SETUP = 140  # drift in toward the console
DROP = (185, 212)  # the box is set down on the console
ETH = (224, 292)  # the network cable rises from behind and plugs in
POWER = (290, 356)  # then power
LIGHT = (360, 372)  # the status light fades on
DAYS = (390, 870)  # three days and nights pass
CALM = (870, 990)  # a quiet look at the box
WIFI = (990, 1230)  # coming soon: tuning the Wi-Fi
SWITCH = 1120  # the moment it moves to a clearer channel
END = (1230, 1350)  # pull back for the end card

# Room.
X0, X1 = -2.2, 2.2  # inside faces of the left wall and the open right edge
Y0, Y1 = -1.8, 1.8  # open front edge and the back wall's inside face
WALL_H, WALL_T = 2.7, 0.15
WIN_X0, WIN_X1, WIN_Z0, WIN_Z1 = 0.25, 1.45, 0.9, 2.3

# Console against the back wall, with the router and the box on it.
# The console stands a little off the wall, so cords can rise behind it.
CONSOLE = (-1.1, Y1 - 0.27, 0.5)  # centre x, centre y, top z
ROUTER = (-0.42, Y1 - 0.22)
BOX_AT = (-0.80, Y1 - 0.27)
GAP_Y = Y1 - 0.03  # where cords run, between the console and the wall
BOX_SCALE = 1.6  # a touch larger than life, so it reads in the room

rng = random.Random(11)


# ---------------------------------------------------------------- the box

def load_box_helpers():
    """Load build_box.py's materials and geometry without running it."""
    with open(BOX_SCRIPT) as f:
        src = f.read()
    src = src.rsplit("\nmain()", 1)[0]
    ns = {"__name__": "build_box", "__file__": BOX_SCRIPT}
    exec(compile(src, BOX_SCRIPT, "exec"), ns)
    return ns


B = load_box_helpers()
srgb, box, rounded, cylinder, join, smooth, activate = (
    B["srgb"], B["box"], B["rounded"], B["cylinder"], B["join"], B["smooth"], B["activate"])


# ---------------------------------------------------------------- materials

def material(name, hex_color, rough=0.6, sheen=0.0, coat=0.0, metal=0.0, emit=None, strength=0.0,
             subsurface=0.0):
    m = B["material"](name, hex_color, rough=rough, metal=metal, coat=coat, emit=emit, strength=strength)
    p = m.node_tree.nodes["Principled BSDF"]
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
        p.inputs["Sheen Tint"].default_value = (1, 1, 1, 1)
    if subsurface:
        p.inputs["Subsurface Weight"].default_value = subsurface
        p.inputs["Subsurface Radius"].default_value = (0.05, 0.03, 0.02)
    return m


def principled(m):
    return m.node_tree.nodes["Principled BSDF"]


def brick_material(name, brick, mortar, scale=8.0, plank=False):
    """Bricks or floor planks from Blender's brick texture, softly bumped."""
    m = material(name, brick, rough=0.85)
    nt = m.node_tree
    p = principled(m)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexBrick")
    tex.offset = 0.5
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Color1"].default_value = (*srgb(brick), 1)
    tex.inputs["Color2"].default_value = (*[c * 0.78 for c in srgb(brick)], 1)
    tex.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    if plank:
        tex.inputs["Mortar Size"].default_value = 0.006
        tex.inputs["Brick Width"].default_value = 1.6
        tex.inputs["Row Height"].default_value = 0.16
        tex.squash = 1.0
    else:
        tex.inputs["Mortar Size"].default_value = 0.018
        tex.inputs["Mortar Smooth"].default_value = 0.4
        tex.inputs["Brick Width"].default_value = 0.5
        tex.inputs["Row Height"].default_value = 0.18
    tex.inputs["Bias"].default_value = 0.0
    src = coord.outputs["Object"]
    if not plank:
        # Bricks are on a wall in the YZ plane: feed Y and Z as the pattern.
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(src, sep.inputs[0])
        nt.links.new(sep.outputs["Y"], comb.inputs["X"])
        nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
        src = comb.outputs[0]
    nt.links.new(src, tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def glow_material(name, hex_color, strength=0.0, alpha=1.0):
    """Pure emission over transparency, for lights, rings and the sky."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "Emission"
    em.inputs["Color"].default_value = (*srgb(hex_color), 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.name = "Alpha"
    mix.inputs["Fac"].default_value = alpha
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def palette():
    return {
        "wall": material("Wall Cream", "#F2E6D3", rough=0.92),
        "section": material("Cut Section", "#E8DAC4", rough=0.9),
        "slab": material("Slab Side", "#D9C6AA", rough=0.9),
        "trim": material("Trim White", "#FBF7F0", rough=0.5),
        "brick": brick_material("Brick", "#B4593B", "#E6D6C0", scale=1.0),
        "floor": brick_material("Floor Planks", "#C99460", "#7A5233", scale=1.0, plank=True),
        "rug": material("Rug", "#EFE2CC", rough=1.0, sheen=0.6),
        "rug_border": material("Rug Border", "#D9826A", rough=1.0, sheen=0.6),
        "sofa": material("Sofa Sage", "#8EA68A", rough=0.9, sheen=0.8),
        "mustard": material("Mustard", "#E2AE48", rough=0.9, sheen=0.7),
        "coral": material("Coral", "#F07466", rough=0.85, sheen=0.7),
        "terracotta": material("Terracotta", "#C8684A", rough=0.8),
        "walnut": material("Walnut", "#8A5B3A", rough=0.55, coat=0.2),
        "oak": material("Oak", "#D3A26C", rough=0.5, coat=0.2),
        "tv": material("TV Black", "#16171A", rough=0.15, coat=0.6),
        "router": material("Router", "#2B2D31", rough=0.4, coat=0.3),
        "router_light": material("Router Light", "#BFE3FF", rough=0.3, emit="#7FC4FF", strength=3.0),
        "radiator": material("Radiator", "#EFEBE3", rough=0.35, metal=0.3),
        "iron": material("Fire Escape", "#2A2B2F", rough=0.55, metal=0.4),
        "tower": brick_material("Tower Brick", "#9A5038", "#C9B39A", scale=1.0),
        "tower_trim": material("Tower Trim", "#D8CFC2", rough=0.8),
        "leaf": material("Leaf", "#4F8A4B", rough=0.6, subsurface=0.15),
        "leaf_light": material("Leaf Light", "#73A85C", rough=0.6, subsurface=0.15),
        "brass": material("Brass", "#C9A15A", rough=0.3, metal=1.0),
        "shade": material("Lamp Shade", "#F6EAD7", rough=0.8, emit="#FFC27A", strength=0.0, subsurface=0.3),
        "mug": material("Mug", "#F7F3EC", rough=0.3, coat=0.4),
        "phone": material("Phone", "#1A1B1E", rough=0.2, coat=0.6),
        "screen": material("Phone Screen", "#0B0C0E", rough=0.15, emit="#DFF5E9", strength=0.0),
        "paper": material("Paper", "#FFFDF6", rough=0.9),
        "frame_dark": material("Frame Dark", "#2E2C2A", rough=0.5),
        "sky_blue": material("Art Blue", "#6E9BC8", rough=0.9),
        "sun_yellow": material("Art Yellow", "#F4C64E", rough=0.9),
        "book_a": material("Book Teal", "#3E7C7B", rough=0.8),
        "book_b": material("Book Cream", "#EADFC8", rough=0.8),
        "book_c": material("Book Navy", "#2F3E63", rough=0.8),
        "card": material("Card", "#FFFFFF", rough=0.45, coat=0.3),
        "ink": material("Ink", "#1C1C1E", rough=0.6),
        "ink_soft": material("Ink Soft", "#5F5F66", rough=0.6),
        "good": material("Bar Green", "#2FBF71", rough=0.45, emit="#2FBF71", strength=0.15),
        "dip": material("Bar Amber", "#F2A43A", rough=0.45, emit="#F2A43A", strength=0.15),
        "promise": material("Promise Line", "#F07466", rough=0.5, emit="#F07466", strength=0.2),
        "pill": material("Pill Coral", "#E0533F", rough=0.5),
        "white_text": material("White Text", "#FFFFFF", rough=0.5),
        # A plain window by day that glows warm at night.
        "window_lit": material("Window Lit", "#5C6B7A", rough=0.2, coat=0.5, emit="#FFD08A", strength=0.0),
        "window_dark": material("Window Dark", "#5C6B7A", rough=0.2, coat=0.5),
    }


# ---------------------------------------------------------------- geometry

def soft(name, size, loc, mat, bevel=0.012, segments=3, rot=None):
    """A box with every edge softly rounded: the diorama's basic block."""
    o = box(name, size, loc, mat)
    if rot:
        o.rotation_euler = rot
    if bevel:
        b = o.modifiers.new("soft", "BEVEL")
        b.width = min(bevel, min(size) * 0.49)
        b.segments = segments
        b.limit_method = "ANGLE"
        b.harden_normals = False
    smooth(o, 40)
    return o


def cyl(name, r, depth, loc, mat, axis=2, verts=32, bevel=0.0):
    o = cylinder(name, r, depth, loc, mat, axis=axis, vertices=verts)
    if bevel:
        b = o.modifiers.new("soft", "BEVEL")
        b.width = bevel
        b.segments = 3
        b.limit_method = "ANGLE"
    smooth(o, 40)
    return o


def blob(name, radius, loc, mat, scale=(1, 1, 1), rot=(0, 0, 0), subdiv=3):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=radius, subdivisions=subdiv, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    B["assign"](o, mat)
    bpy.ops.object.shade_smooth()
    return o


def curve_tube(name, points, radius, mat, handles="AUTO"):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 4
    data.use_fill_caps = True
    data.resolution_u = 24
    sp = data.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = handles
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def text(name, body, size, loc, mat, weight="Medium", align="LEFT", parent=None, extrude=0.0015):
    path = os.path.join(FONT_DIR, f"Geist-{weight}.otf")
    font = bpy.data.fonts.load(path, check_existing=True) if os.path.exists(path) else None
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    if font:
        data.font = font
    data.size = size
    data.align_x = align
    data.align_y = "CENTER"
    data.extrude = extrude
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def parent_to(children, parent):
    for c in children:
        mw = c.matrix_world.copy()
        c.parent = parent
        c.matrix_world = mw


# ---------------------------------------------------------------- the room

def room(m):
    o = []
    # Floor slab, its cut edges showing like a section drawing.
    o.append(soft("Slab", (X1 - X0 + WALL_T, Y1 - Y0 + WALL_T, 0.32),
                  ((X0 - WALL_T + X1) / 2, (Y0 + Y1 + WALL_T) / 2, -0.16), m["slab"], bevel=0.04))
    o.append(soft("Floor", (X1 - X0, Y1 - Y0, 0.02), ((X0 + X1) / 2, (Y0 + Y1) / 2, 0.0), m["floor"], bevel=0.004))

    # Back wall, built around the window opening.
    yb = Y1 + WALL_T / 2
    xl = X0 - WALL_T
    # One piece with the window cut out: separate blocks left grooves where
    # their rounded edges met.
    back = soft("Back wall", (X1 - xl, WALL_T, WALL_H), ((xl + X1) / 2, yb, WALL_H / 2), m["wall"])
    B["cut"](back, box("Window opening", (WIN_X1 - WIN_X0, WALL_T * 3, WIN_Z1 - WIN_Z0),
                       ((WIN_X0 + WIN_X1) / 2, yb, (WIN_Z0 + WIN_Z1) / 2)), m["wall"])
    smooth(back, 40)
    o.append(back)
    # Left wall: plaster outside, exposed brick inside.
    o.append(soft("Left wall", (WALL_T, Y1 - Y0 + WALL_T, WALL_H), (X0 - WALL_T / 2, (Y0 + Y1 + WALL_T) / 2,
                                                                     WALL_H / 2), m["wall"]))
    brick = soft("Brick face", (0.012, Y1 - Y0 - 0.02, WALL_H - 0.02), (X0 + 0.006, (Y0 + Y1) / 2,
                                                                         WALL_H / 2), m["brick"], bevel=0.003)
    o.append(brick)
    # Cut tops of the walls, in the section colour.
    o.append(soft("Back cap", (X1 - xl, WALL_T + 0.004, 0.02), ((xl + X1) / 2, yb, WALL_H), m["section"], bevel=0.006))
    o.append(soft("Left cap", (WALL_T + 0.004, Y1 - Y0 + WALL_T, 0.02), (X0 - WALL_T / 2, (Y0 + Y1 + WALL_T) / 2,
                                                                          WALL_H), m["section"], bevel=0.006))
    # The back wall carries on past the cut, for shadows only, so sunlight
    # enters through the window and not around the end of the wall.
    for name, size, loc in (("Shadow wall", (5.0, 0.6, 3.2), (X1 + 2.5, Y1 + 0.3, 1.6)),
                            ("Shadow roof", (X1 - X0 + 5.0, 0.8, 0.05), ((X0 + X1) / 2 + 2.0, Y1 - 0.2, WALL_H + 0.3))):
        blocker = box(name, size, loc)
        for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission",
                     "visible_volume_scatter"):
            setattr(blocker, attr, False)
    # Baseboards.
    o.append(soft("Base back", (X1 - X0, 0.025, 0.11), ((X0 + X1) / 2, Y1 - 0.0125, 0.065), m["trim"], bevel=0.006))
    o.append(soft("Base left", (0.025, Y1 - Y0, 0.11), (X0 + 0.0245, (Y0 + Y1) / 2, 0.065), m["trim"], bevel=0.006))
    return o


def window(m):
    o = []
    cx, w = (WIN_X0 + WIN_X1) / 2, WIN_X1 - WIN_X0
    h, cz = WIN_Z1 - WIN_Z0, (WIN_Z0 + WIN_Z1) / 2
    y = Y1 + 0.05
    t = 0.06
    # Side jambs only, flush with the opening: a head piece stuck out past the
    # sides like a curtain rod.
    o.append(soft("Frame L", (t, 0.1, h), (WIN_X0 + t / 2, y, cz), m["trim"]))
    o.append(soft("Frame R", (t, 0.1, h), (WIN_X1 - t / 2, y, cz), m["trim"]))
    o.append(soft("Sill", (w + 0.22, 0.2, 0.045), (cx, Y1 - 0.02, WIN_Z0 - 0.01), m["trim"], bevel=0.015))
    # A double-hung window, its lower sash raised a little.
    o.append(soft("Meeting rail", (w, 0.05, 0.05), (cx, y + 0.02, cz + 0.08), m["trim"], bevel=0.008))
    o.append(soft("Mullion", (0.035, 0.04, h), (cx, y + 0.03, cz), m["trim"], bevel=0.006))
    # Radiator under the window: rounded fins on two pipes.
    rad_w, rad_h = 0.95, 0.5
    for i in range(16):
        x = cx - rad_w / 2 + (i + 0.5) * rad_w / 16
        o.append(soft(f"Fin {i}", (0.045, 0.12, rad_h), (x, Y1 - 0.11, 0.14 + rad_h / 2), m["radiator"],
                      bevel=0.02, segments=4))
    for z in (0.18, 0.6):
        o.append(cyl(f"Pipe {z}", 0.018, rad_w + 0.04, (cx, Y1 - 0.11, z), m["radiator"], axis=0))
    o.append(cyl("Feet L", 0.012, 0.14, (cx - rad_w / 2 + 0.04, Y1 - 0.11, 0.07), m["radiator"]))
    o.append(cyl("Feet R", 0.012, 0.14, (cx + rad_w / 2 - 0.04, Y1 - 0.11, 0.07), m["radiator"]))
    # Plants on the sill.
    for i, x in enumerate((WIN_X0 + 0.15, WIN_X1 - 0.18)):
        o += potted_plant(m, (x, Y1 - 0.03, WIN_Z0 + 0.012), 0.75 + 0.2 * i, f"Sill plant {i}")
    return o


def outside(m):
    """The view: sky, a NYCHA tower across the way, and a fire escape. Kept
    in a shallow box behind the window so it stays hidden from outside."""
    o = []
    yw = Y1 + WALL_T
    # A fire escape landing just outside the window. Its railing read as a
    # rod across the glass, so it has none.
    fy = yw + 0.25
    o.append(soft("Escape deck", (1.9, 0.42, 0.025), (0.55, fy, WIN_Z0 - 0.07), m["iron"], bevel=0.004))
    # A NYCHA tower across the street: brown brick, rows of windows.
    ty = yw + 0.55
    tower = soft("Tower", (1.05, 0.06, 2.2), (0.15, ty, 1.0), m["tower"], bevel=0.01)
    tower2 = soft("Tower 2", (0.7, 0.06, 2.4), (1.25, ty + 0.03, 0.8), m["tower"], bevel=0.01)
    o += [tower, tower2]
    lit = []
    for col in range(6):
        for row in range(9):
            for k, (x0, top, n) in enumerate(((0.15 - 0.42, 1.98, 6), (1.25 - 0.27, 1.85, 4))):
                if col >= n:
                    continue
                x = x0 + col * 0.168
                z = top - row * 0.22
                if z < 0.2:
                    continue
                on = rng.random() < 0.45
                w = soft(f"Win {k}{col}{row}", (0.07, 0.012, 0.1), (x, ty - 0.035 + k * 0.03, z),
                         m["window_lit"] if on else m["window_dark"], bevel=0.003)
                o.append(w)
                if on:
                    lit.append(w)
    for ob in o:
        if ob.name.startswith(("Tower", "Win ")):
            ob.visible_shadow = False
    # Sky: a soft gradient card whose colours follow the time of day.
    sky = bpy.data.materials.new("Sky")
    sky.use_nodes = True
    nt = sky.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.name = "Sky Mix"
    mix.inputs["A"].default_value = (*srgb("#F6D9B8"), 1)  # horizon
    mix.inputs["B"].default_value = (*srgb("#8CC4EA"), 1)  # zenith
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    em.name = "Sky Emission"
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    sky_o = box("Sky", (2.4, 0.02, 2.1), (0.3, yw + 0.7, 1.05), sky)
    sky_o.visible_shadow = False
    o.append(sky_o)
    sun = blob("Sun disc", 0.09, (0.5, yw + 0.66, 1.7), glow_material("Sun Glow", "#FFE9B0", 4.0), subdiv=3)
    moon = blob("Moon disc", 0.065, (0.5, yw + 0.66, 1.7), glow_material("Moon Glow", "#EEF2FF", 2.0), subdiv=3)
    for d in (sun, moon):
        d.visible_shadow = False
        d.scale = (1, 0.2, 1)
    stars_mat = glow_material("Stars", "#FFFFFF", 0.0)
    for i in range(26):
        s = blob(f"Star {i}", 0.006, (rng.uniform(-0.6, 1.4), yw + 0.68, rng.uniform(1.25, 2.05)), stars_mat,
                 subdiv=1)
        s.visible_shadow = False
    return {"objects": o, "sky": sky, "sun": sun, "moon": moon, "stars": stars_mat}


def potted_plant(m, base, size, name):
    x, y, z = base
    o = [cyl(f"{name} pot", 0.06 * size, 0.11 * size, (x, y, z + 0.055 * size), m["terracotta"], verts=24,
             bevel=0.008 * size)]
    for i in range(7):
        a = i / 7 * math.tau + rng.uniform(-0.3, 0.3)
        r = 0.05 * size
        o.append(blob(f"{name} leaf {i}", 0.045 * size,
                      (x + math.cos(a) * r, y + math.sin(a) * r, z + (0.14 + rng.uniform(0, 0.08)) * size),
                      m["leaf"] if i % 2 else m["leaf_light"], scale=(1.0, 0.55, 1.4),
                      rot=(rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), a)))
    return o


def floor_plant(m, base):
    """A tall leafy plant for the corner."""
    x, y, z = base
    o = [cyl("Big pot", 0.17, 0.36, (x, y, 0.18), m["terracotta"], verts=32, bevel=0.02)]
    for i in range(16):
        a = i * 2.4
        h = 0.55 + (i % 5) * 0.16
        r = 0.08 + (i % 3) * 0.06
        stem_top = (x + math.cos(a) * r, y + math.sin(a) * r, h)
        o.append(curve_tube(f"Stem {i}", [(x, y, 0.32), stem_top], 0.006, m["leaf"]))
        o.append(blob(f"Big leaf {i}", 0.13, (stem_top[0] + math.cos(a) * 0.08, stem_top[1] + math.sin(a) * 0.08,
                                               h + 0.05), m["leaf"] if i % 2 else m["leaf_light"],
                      scale=(1.25, 0.18, 0.85), rot=(0.4, -0.5, a + math.pi / 2)))
    return o


def furniture(m):
    o = []
    cx, cy, top = CONSOLE
    # Console.
    o.append(soft("Console", (1.75, 0.42, top - 0.1), (cx, cy, 0.1 + (top - 0.1) / 2), m["walnut"], bevel=0.02))
    for i, dx in enumerate((-0.44, 0.0, 0.44)):
        o.append(soft(f"Door {i}", (0.4, 0.01, 0.28), (cx + dx * 1.3, cy - 0.212, 0.3), m["oak"], bevel=0.008))
    for sx in (-0.78, 0.78):
        for sy in (-0.16, 0.16):
            o.append(cyl(f"Leg {sx}{sy}", 0.018, 0.1, (cx + sx, cy + sy, 0.05), m["walnut"], verts=16))
    # TV.
    o.append(soft("TV", (0.92, 0.04, 0.54), (cx - 0.35, cy + 0.08, top + 0.36), m["tv"], bevel=0.01))
    o.append(soft("TV stand", (0.3, 0.16, 0.02), (cx - 0.35, cy + 0.06, top + 0.01), m["tv"], bevel=0.008))
    o.append(soft("TV neck", (0.05, 0.03, 0.08), (cx - 0.35, cy + 0.08, top + 0.05), m["tv"], bevel=0.008))
    # Books and a small plant on the console.
    for i, (mat, h) in enumerate(((m["book_a"], 0.2), (m["book_b"], 0.17), (m["book_c"], 0.22))):
        o.append(soft(f"Console book {i}", (0.035, 0.15, h), (cx - 0.9 + 0.04 * i, cy - 0.02, top + h / 2), mat,
                      bevel=0.006))
    o += potted_plant(m, (cx + 0.82, cy - 0.02, top), 0.6, "Console plant")  # clear of the cords

    # Sofa facing the TV, its back to the open front.
    sx, sy = -1.15, -0.85
    o.append(soft("Sofa base", (1.9, 0.85, 0.24), (sx, sy, 0.2), m["sofa"], bevel=0.06, segments=5))
    o.append(soft("Sofa back", (1.9, 0.22, 0.48), (sx, sy - 0.33, 0.52), m["sofa"], bevel=0.09, segments=6))
    for side in (-1, 1):
        o.append(soft(f"Sofa arm {side}", (0.22, 0.85, 0.5), (sx + side * 0.86, sy, 0.38), m["sofa"], bevel=0.09,
                      segments=6))
    for i in (-1, 1):
        o.append(soft(f"Seat {i}", (0.74, 0.62, 0.14), (sx + i * 0.38, sy + 0.08, 0.38), m["sofa"], bevel=0.06,
                      segments=6))
    o.append(soft("Pillow 1", (0.4, 0.13, 0.36), (sx - 0.55, sy - 0.17, 0.62), m["mustard"], bevel=0.06, segments=6,
                  rot=(0.2, 0.0, 0.15)))
    o.append(soft("Pillow 2", (0.38, 0.13, 0.34), (sx + 0.58, sy - 0.17, 0.62), m["coral"], bevel=0.06, segments=6,
                  rot=(0.2, 0.0, -0.2)))
    # A blanket draped over the arm.
    o.append(soft("Blanket", (0.3, 0.55, 0.07), (sx + 0.87, sy + 0.05, 0.64), m["terracotta"], bevel=0.03,
                  segments=5, rot=(0.0, 0.25, 0.08)))
    o.append(soft("Blanket fall", (0.05, 0.5, 0.35), (sx + 0.98, sy + 0.06, 0.45), m["terracotta"], bevel=0.02,
                  segments=4))
    for lx in (-0.85, 0.85):
        for ly in (-0.35, 0.35):
            o.append(cyl(f"Sofa leg {lx}{ly}", 0.02, 0.08, (sx + lx, sy + ly, 0.04), m["walnut"], verts=12))

    # Rug and a round coffee table, with a mug and a phone.
    o.append(soft("Rug border", (2.3, 1.55, 0.012), (-0.8, 0.35, 0.016), m["rug_border"], bevel=0.005))
    o.append(soft("Rug", (2.1, 1.35, 0.014), (-0.8, 0.35, 0.02), m["rug"], bevel=0.005))
    tx, ty = -1.05, 0.38
    o.append(cyl("Table top", 0.38, 0.04, (tx, ty, 0.42), m["oak"], verts=48, bevel=0.012))
    for i in range(3):
        a = i / 3 * math.tau
        o.append(cyl(f"Table leg {i}", 0.018, 0.4, (tx + math.cos(a) * 0.24, ty + math.sin(a) * 0.24, 0.2),
                     m["walnut"], verts=12))
    o.append(cyl("Mug", 0.04, 0.09, (tx + 0.14, ty - 0.08, 0.485), m["mug"], verts=32, bevel=0.006))
    o.append(cyl("Coffee", 0.034, 0.002, (tx + 0.14, ty - 0.08, 0.525), m["walnut"], verts=32))
    handle = curve_tube("Mug handle", [(tx + 0.18, ty - 0.08, 0.51), (tx + 0.215, ty - 0.08, 0.485),
                                       (tx + 0.18, ty - 0.08, 0.46)], 0.007, m["mug"])
    o.append(handle)
    phone = soft("Phone", (0.075, 0.15, 0.009), (tx - 0.12, ty - 0.05, 0.445), m["phone"], bevel=0.008,
                 rot=(0, 0, 0.35))
    o.append(phone)
    screen = soft("Phone screen", (0.066, 0.138, 0.002), (tx - 0.12, ty - 0.05, 0.4505), m["screen"], bevel=0.006,
                  rot=(0, 0, 0.35))
    o.append(screen)
    # A small stack of toy blocks on the rug.
    for i, (mat, dz) in enumerate(((m["coral"], 0.0), (m["mustard"], 0.07), (m["book_a"], 0.14))):
        o.append(soft(f"Block {i}", (0.07, 0.07, 0.07), (-0.05 + 0.01 * i, 0.75, 0.06 + dz), mat, bevel=0.012,
                      rot=(0, 0, 0.3 * i)))

    # An armchair by the window.
    ax, ay = 1.45, -0.3
    o.append(soft("Chair seat", (0.75, 0.75, 0.3), (ax, ay, 0.28), m["mustard"], bevel=0.08, segments=6))
    o.append(soft("Chair back", (0.18, 0.75, 0.55), (ax + 0.3, ay, 0.6), m["mustard"], bevel=0.08, segments=6))
    for side in (-1, 1):
        o.append(soft(f"Chair arm {side}", (0.7, 0.14, 0.42), (ax + 0.03, ay + side * 0.33, 0.42), m["mustard"],
                      bevel=0.06, segments=6))
    o.append(soft("Chair cushion", (0.5, 0.5, 0.1), (ax - 0.04, ay, 0.47), m["mustard"], bevel=0.05, segments=5))
    for lx in (-0.3, 0.3):
        for ly in (-0.3, 0.3):
            o.append(cyl(f"Chair leg {lx}{ly}", 0.02, 0.14, (ax + lx, ay + ly, 0.07), m["walnut"], verts=12))
    o += floor_plant(m, (1.85, 1.35, 0))

    # Floor lamp between the console and the window, on in the evenings.
    lx, ly = 0.02, 1.45
    o.append(cyl("Lamp base", 0.12, 0.025, (lx, ly, 0.0125), m["brass"], verts=32, bevel=0.008))
    o.append(cyl("Lamp pole", 0.012, 1.35, (lx, ly, 0.69), m["brass"], verts=16))
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.13, depth=0.26, vertices=48, end_fill_type="NOTHING",
                                    location=(lx, ly, 1.42))
    shade = bpy.context.active_object
    shade.name = "Lamp shade"
    B["assign"](shade, m["shade"])
    shade.modifiers.new("thick", "SOLIDIFY").thickness = 0.006
    smooth(shade)
    o.append(shade)
    lamp_data = bpy.data.lights.new("Lamp bulb", "POINT")
    lamp_data.energy = 0.0
    lamp_data.color = srgb("#FFB868")
    lamp_data.shadow_soft_size = 0.06
    lamp = bpy.data.objects.new("Lamp bulb", lamp_data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = (lx, ly, 1.38)
    return o, {"lamp": lamp, "screen": screen}


def wall_decor(m):
    o = []
    # A shelf of photos and books on the brick wall, above the sofa.
    x = X0 + 0.02
    o.append(soft("Shelf", (0.22, 1.3, 0.035), (x + 0.11, -0.85, 1.55), m["oak"], bevel=0.008))
    for i, (mat, h) in enumerate(((m["book_c"], 0.22), (m["book_a"], 0.2), (m["book_b"], 0.24), (m["coral"], 0.18))):
        o.append(soft(f"Shelf book {i}", (0.16, 0.04, h), (x + 0.1, -1.4 + 0.045 * i, 1.57 + h / 2), mat, bevel=0.006))
    o += potted_plant(m, (x + 0.1, -0.3, 1.57), 0.7, "Shelf plant")
    # Family photos: framed prints in two sizes.
    photos = [((-0.95, 1.85), (0.03, 0.26, 0.2), "#E7B88E"), ((-0.62, 1.9), (0.03, 0.2, 0.26), "#9EC1D9"),
              ((-1.2, 2.15), (0.03, 0.2, 0.16), "#F0D3A0"), ((-0.85, 2.2), (0.03, 0.3, 0.22), "#B9CFA9")]
    for i, ((y, z), size, color) in enumerate(photos):
        o.append(soft(f"Photo frame {i}", size, (x + 0.015, y, z), m["frame_dark"], bevel=0.005))
        o.append(soft(f"Photo {i}", (0.01, size[1] - 0.05, size[2] - 0.05), (x + 0.032, y, z),
                      material(f"Photo {i}", color, rough=0.4), bevel=0.002))
    # A child's drawing taped to the wall by the console: a house and a sun.
    dy, dz = 0.9, 1.3
    o.append(soft("Drawing", (0.006, 0.3, 0.22), (x + 0.004, dy, dz), m["paper"], bevel=0.0, rot=(0.06, 0, 0)))
    o.append(soft("House", (0.004, 0.1, 0.08), (x + 0.009, dy - 0.03, dz - 0.04), m["coral"], bevel=0.0))
    bpy.ops.mesh.primitive_cone_add(radius1=0.075, depth=0.004, vertices=3, location=(x + 0.009, dy - 0.03, dz + 0.025),
                                    rotation=(0, math.pi / 2, 0))
    roof = bpy.context.active_object
    roof.name = "Roof"
    roof.rotation_euler = (math.pi / 2 + math.pi / 6, math.pi / 2, 0)
    roof.rotation_euler = (0, math.pi / 2, math.pi / 2)
    B["assign"](roof, m["sky_blue"])
    o.append(roof)
    o.append(cyl("Drawn sun", 0.03, 0.004, (x + 0.009, dy + 0.09, dz + 0.06), m["sun_yellow"], axis=0, verts=24))
    return o


# ---------------------------------------------------------------- devices

def router(m, cable_mat):
    rx, ry = ROUTER
    top = CONSOLE[2]
    o = [rounded("Router", (0.075, 0.2, 0.26), (rx, ry, top + 0.13), 0.03, axis=0, mat=m["router"], edge=0.006)]
    smooth(o[0])
    for i in range(4):
        o.append(soft(f"Router light {i}", (0.004, 0.004, 0.004), (rx - 0.012 + i * 0.008, ry - 0.101, top + 0.2),
                      m["router_light"], bevel=0.0015))
    # Its own cord leaves the back and drops behind the console.
    pts = fillet([(rx, ry + 0.09, top + 0.04), (rx, GAP_Y, top + 0.04), (rx, GAP_Y, top - 0.3)], 0.03)
    o.append(cord("Router cord", pts, 0.0032, cable_mat)[0])
    return o


def the_box(bm):
    """The measuring box from build_box.py, closed, on the console."""
    board = B["raspberry_pi"](bm)
    base = B["case_base"](bm)
    shell = B["case_shell"](bm)
    for o in (base, shell):
        smooth(o)
    parts = [board, base, shell]
    B["to_metres"](parts)
    holder = bpy.data.objects.new("Box", None)
    bpy.context.collection.objects.link(holder)
    holder.location = (BOX_AT[0], BOX_AT[1], CONSOLE[2])
    holder.scale = (BOX_SCALE,) * 3
    bpy.context.view_layer.update()
    for p in parts:
        p.parent = holder
    bpy.context.view_layer.update()
    cw = B["CASE_W"]
    return {"holder": holder, "shell": shell, "parts": parts,
            "led_world": holder.matrix_world @ (Vector((B["LED"][0], -cw / 2 - 1.5, B["LED"][1])) * 0.001)}


def plug_heads(bm, holder):
    """The two plug heads, built like build_box.py's cables but without
    cords. Each has the point where its cord joins at the origin and points
    along -X, the way it travels into its socket. Returns the heads and,
    for each, where that cord joint sits once plugged in."""
    ef, ey, ez = B["ETH_FRONT"], B["ETH_Y"], B["ETH_Z"]
    plug_front = ef - 8.5
    plug_len, plug_w, plug_h = 21.0, 11.6, 8.2
    plug_z = ez - 0.5
    boot_start = plug_front + plug_len
    tail_x = boot_start + 14
    eth = [rounded("Plug", (plug_len, plug_w, plug_h), (plug_front + plug_len / 2 - tail_x, 0, 0), 0.6, axis=0,
                   mat=bm["plug"])]
    for i in range(8):
        eth.append(box(f"contact{i}", (3.5, 0.5, 0.4), (plug_front + 2 - tail_x, (i - 3.5) * 1.1, plug_h / 2 - 0.1),
                       bm["gold"]))
    eth.append(rounded("Boot", (14, 13, 10), (-7, 0, 0), 3.0, axis=0, mat=bm["rubber"], edge=1.0))
    eth = join(eth, "Network plug")

    ux, uz, cw = B["USBC_X"], B["USBC_Z"], B["CASE_W"]
    mold_front = -cw / 2 - 0.6
    pwr = join([
        rounded("USB-C tip", (6.5, 8.3, 2.5), (-16.0 - 3.25, 0, 0), 1.2, axis=0, mat=bm["metal"]),
        rounded("USB-C plug", (16.0, 10.5, 6.2), (-8.0, 0, 0), 3.0, axis=0, mat=bm["rubber"], edge=1.2),
    ], "Power plug")
    B["to_metres"]([eth, pwr])
    for o in (eth, pwr):
        o.scale = (BOX_SCALE,) * 3
        o.rotation_mode = "QUATERNION"
    w = holder.matrix_world
    eth_home = w @ (Vector((tail_x, ey, plug_z)) * 0.001)
    pwr_home = w @ (Vector((ux, mold_front - 16.0, uz)) * 0.001)
    return eth, pwr, eth_home, pwr_home


def fillet(points, radius, step=0.004):
    """A dense polyline through `points` with every corner rounded."""
    pts = [Vector(p) for p in points]
    out = [pts[0]]

    def line_to(end):
        start = out[-1]
        n = max(1, int((end - start).length / step))
        out.extend(start.lerp(end, k / n) for k in range(1, n + 1))

    for a, b, c in zip(pts, pts[1:], pts[2:]):
        d1, d2 = b - a, c - b
        r = min(radius, d1.length * 0.5, d2.length * 0.5)
        A, C = b - d1.normalized() * r, b + d2.normalized() * r
        line_to(A)
        n = max(6, int(3 * r / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((1 - t) ** 2 * A + 2 * (1 - t) * t * b + t * t * C)
    line_to(pts[-1])
    return out


def cord(name, pts, radius, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 4
    data.use_fill_caps = True
    sp = data.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        p.co = (v.x, v.y, v.z, 1.0)
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    return o, pts, cum


def cords(cable_mat, eth_home, pwr_home):
    """Both cords start hidden behind the console, rise over its back edge,
    run along the top and end in a straight run into their sockets."""
    top = CONSOLE[2]
    lie = top + 0.0035  # resting on the console
    e = eth_home
    eth = fillet([(-0.56, GAP_Y, top - 0.24), (-0.56, GAP_Y, lie), (-0.56, e.y, lie), (-0.585, e.y, lie),
                  (e.x + 0.075, e.y, e.z), e], 0.035)
    p = pwr_home
    pwr = fillet([(-0.95, GAP_Y, top - 0.24), (-0.95, GAP_Y, lie), (-0.95, p.y - 0.085, lie),
                  (p.x - 0.03, p.y - 0.085, lie), (p.x, p.y - 0.06, p.z), p], 0.035)
    return cord("Network cable", eth, 0.0035, cable_mat), cord("Power cord", pwr, 0.0028, cable_mat)


# ---------------------------------------------------------------- the cards

def chart_card(m):
    """A floating card: measured download speed beside the promise."""
    card = bpy.data.objects.new("Chart card", None)
    bpy.context.collection.objects.link(card)
    W, H = 1.0, 0.66
    panel = rounded("Chart panel", (W, H, 0.02), (0, 0, 0), 0.06, axis=2, mat=m["card"], edge=0.008)
    smooth(panel)
    panel.parent = card
    z = 0.012
    text("Chart title", "Measured download speed", 0.058, (-0.44, 0.255, z), m["ink"], "SemiBold", parent=card)
    text("Chart note", "Example results", 0.034, (-0.44, 0.195, z), m["ink_soft"], "Regular", parent=card)
    # Chart area.
    cx0, cx1, cy0, cy1 = -0.42, 0.42, -0.2, 0.13
    def y_of(mbps):
        return cy0 + (cy1 - cy0) * mbps / 560
    # The promise, as a dashed line.
    py = y_of(500)
    for i in range(22):
        x = cx0 + (i + 0.25) * (cx1 - cx0) / 22
        d = soft(f"Dash {i}", (0.022, 0.006, 0.004), (x, py, z), m["promise"], bevel=0.0)
        d.parent = card
    text("Promise label", "Promised: up to 500 Mbps", 0.04, (cx1, py + 0.03, z), m["pill"], "Medium", "RIGHT", parent=card)
    soft("Axis", (cx1 - cx0, 0.004, 0.003), ((cx0 + cx1) / 2, cy0, z), m["ink_soft"], bevel=0.0).parent = card
    values = [462, 188, 481, 455, 163, 476, 470, 214, 488]
    bars = []
    for i, v in enumerate(values):
        group, k = divmod(i, 3)
        x = cx0 + 0.09 + group * 0.28 + k * 0.075
        h = y_of(v) - cy0
        bar = rounded(f"Bar {i}", (0.05, h, 0.012), (0, h / 2, 0), 0.012, axis=2, mat=m["good"] if v > 300 else m["dip"])
        smooth(bar)
        holder = bpy.data.objects.new(f"Bar holder {i}", None)
        bpy.context.collection.objects.link(holder)
        holder.parent = card
        holder.location = (x, cy0 + 0.002, z)
        bar.parent = holder
        bars.append(holder)
    for d, name in enumerate(("Mon", "Tue", "Wed")):
        text(f"Day {d}", name, 0.04, (cx0 + 0.165 + d * 0.28, cy0 - 0.04, z), m["ink_soft"], "Medium", "CENTER",
             parent=card)
    return card, bars


def wifi_card(m):
    card = bpy.data.objects.new("Wi-Fi card", None)
    bpy.context.collection.objects.link(card)
    W, H = 0.9, 0.42
    panel = rounded("Wi-Fi panel", (W, H, 0.02), (0, 0, 0), 0.06, axis=2, mat=m["card"], edge=0.008)
    smooth(panel)
    panel.parent = card
    z = 0.012
    text("Wi-Fi title", "Wi-Fi", 0.07, (-0.39, 0.13, z), m["ink"], "SemiBold", parent=card)
    # Matches the website's "Coming later" badge. Advice is planned, not built.
    pill = rounded("Soon pill", (0.32, 0.08, 0.01), (0.25, 0.13, z - 0.004), 0.03, axis=2, mat=m["pill"])
    smooth(pill)
    pill.parent = card
    text("Soon text", "Coming later", 0.04, (0.25, 0.13, z + 0.004), m["white_text"], "SemiBold", "CENTER",
         parent=card)
    rows = {}
    # Advice, not an automatic change: the website promises recommendations.
    # Whole sentences, and nothing that suggests looking at anyone else's
    # network: the card talks only about the channel.
    for key, mat, line1, line2 in (("before", m["dip"], "Channel 6 is busy", "A busy channel can slow your Wi-Fi."),
                                   ("after", m["good"], "Try channel 11", "Your Wi-Fi may be steadier there.")):
        row = bpy.data.objects.new(f"Row {key}", None)
        bpy.context.collection.objects.link(row)
        row.parent = card
        row.location = (0, -0.06, 0)
        dot = cyl(f"Dot {key}", 0.022, 0.008, (-0.37, 0.03, z), mat, verts=24)
        dot.parent = row
        text(f"Row {key} 1", line1, 0.055, (-0.32, 0.03, z), m["ink"], "SemiBold", parent=row)
        text(f"Row {key} 2", line2, 0.04, (-0.32, -0.04, z), m["ink_soft"], "Regular", parent=row)
        rows[key] = row
    return card, rows


def wifi_icon():
    """A floating Wi-Fi symbol over the router: a dot and three arcs."""
    rx, ry = ROUTER
    icon = bpy.data.objects.new("Wi-Fi icon", None)
    bpy.context.collection.objects.link(icon)
    icon.location = (rx, ry - 0.02, CONSOLE[2] + 0.37)
    parts = [blob("Wi-Fi dot", 0.017, (0, 0, 0), glow_material("Wi-Fi dot", "#F2A43A", 3.0, 0.0), subdiv=3)]
    for i, r in enumerate((0.055, 0.095, 0.135)):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.011, major_segments=96, minor_segments=10)
        arc = bpy.context.active_object
        arc.name = f"Wi-Fi arc {i}"
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for v in arc.data.vertices:
            v.select = abs(math.atan2(v.co.x, v.co.y)) > math.radians(46)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="VERT")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.shade_smooth()
        arc.data.materials.append(glow_material(f"Wi-Fi arc {i}", "#F2A43A", 3.0, 0.0))
        parts.append(arc)
    for o in parts:
        o.parent = icon
        o.visible_shadow = False
    return icon, parts


def steam_puffs():
    """Soft wisps rising from the mug."""
    tx, ty = -1.05, 0.38
    mx, my, mz = tx + 0.14, ty - 0.08, 0.535
    puffs = []
    for i in range(5):
        mat = bpy.data.materials.new(f"Steam {i}")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
        dif.inputs["Color"].default_value = (1, 1, 1, 1)
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.name = "Alpha"
        mix.inputs["Fac"].default_value = 0.0
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(dif.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        p = blob(f"Steam {i}", 0.009, (mx, my, mz), mat, subdiv=2)
        p.visible_shadow = False
        puffs.append(p)
    return puffs, Vector((mx, my, mz))


# ---------------------------------------------------------------- lighting

def lights():
    def sun_lamp(name, color):
        data = bpy.data.lights.new(name, "SUN")
        data.color = color
        data.angle = math.radians(3)
        o = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(o)
        return o
    sun = sun_lamp("Sun", srgb("#FFE2B8"))
    moon = sun_lamp("Moonlight", srgb("#9DB4FF"))
    moon.data.angle = math.radians(6)
    # A big soft fill from the open side, standing in for light bouncing
    # around the room, so the miniature reads at night too.
    data = bpy.data.lights.new("Fill", "AREA")
    data.shape = "DISK"
    data.size = 6.0
    fill = bpy.data.objects.new("Fill", data)
    bpy.context.collection.objects.link(fill)
    fill.location = (5.5, -6.0, 6.0)
    fill.rotation_euler = (Vector((0, 0.5, 0.8)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    return sun, moon, fill


def world():
    """Camera sees a soft studio colour; everything else is lit by a dim sky."""
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    seen = nt.nodes.new("ShaderNodeBackground")
    seen.name = "Backdrop"
    env = nt.nodes.new("ShaderNodeBackground")
    env.name = "Ambient"
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs[0], mix.inputs[1])
    nt.links.new(seen.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    bpy.context.scene.world = w
    return seen, env


# ---------------------------------------------------------------- motion

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def hour_at(frame):
    """Clock time in hours for a frame; it keeps counting past 24."""
    keys = [(1, 8.6), (DAYS[0], 9.5), (DAYS[1], 81.5), (CALM[1], 82.2), (WIFI[1], 86.0), (FRAMES, 89.2)]
    for (f0, h0), (f1, h1) in zip(keys, keys[1:]):
        if frame <= f1:
            return lerp(h0, h1, (frame - f0) / (f1 - f0))
    return keys[-1][1]


def daylight(h):
    """0 at night, 1 at midday, from the sun's height."""
    s = ((h % 24) - 6.0) / 12.0
    return max(0.0, math.sin(math.pi * s)) if 0 <= s <= 1 else 0.0


def warmth(h):
    """1 near sunrise and sunset, for golden light and a peach sky."""
    hh = h % 24
    return max(math.exp(-((hh - 6.6) / 1.1) ** 2), math.exp(-((hh - 18.0) / 1.2) ** 2))


SKY = {"day_top": srgb("#86BFE8"), "day_low": srgb("#D9EEF7"), "warm_top": srgb("#E8A99A"),
       "warm_low": srgb("#FFD3A1"), "night_top": srgb("#141B36"), "night_low": srgb("#2B3561")}
BACKDROP = {"day": srgb("#F5EDE2"), "warm": srgb("#F2D9C4"), "night": srgb("#1D2338")}


def key(target, path, value, frame, index=-1):
    setattr(target, path, value) if index < 0 else getattr(target, path).__setitem__(index, value)
    target.keyframe_insert(path, frame=frame, index=index)


def set_interpolation(kind):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = kind


def animate_time(sun, moon, fill, sky, sun_disc, moon_disc, stars, backdrop, ambient, lamp, shade, lit_mat):
    """Bake the day-night cycle into keys every other frame."""
    set_interpolation("LINEAR")
    em = sky.node_tree.nodes["Sky Emission"]
    sky_mix = sky.node_tree.nodes["Sky Mix"]
    star_em = stars.node_tree.nodes["Emission"]
    lit_em = principled(lit_mat).inputs["Emission Strength"]
    shade_em = principled(shade).inputs["Emission Strength"]
    yw = Y1 + WALL_T + 0.66
    for f in range(1, FRAMES + 2, 2):
        h = hour_at(f)
        d, w = daylight(h), warmth(h)
        # Twilight: eases from night to full day over the first hours of
        # sunlight, so dawn and dusk are gradual fades rather than snaps.
        dl = ease(d / 0.6)
        night = 1 - dl
        hh = h % 24
        # Sun: rises right, sets left, always behind the window wall.
        s = (hh - 6.0) / 12.0
        a = math.pi * s
        # An arc that drops the window's light onto the floor in front of it.
        sun_dir = Vector((math.cos(a) * 0.9 + 0.55, 1.0, max(0.1, math.sin(a)) * 1.6)).normalized()
        # Keep each key's euler compatible with the last one: otherwise an
        # angle wraps from +pi to -pi between keys and the frame between them
        # swings the light right round, a one-frame flash.
        sun.rotation_euler = (-sun_dir).to_track_quat("-Z", "Y").to_euler("XYZ", sun.rotation_euler)
        sun.keyframe_insert("rotation_euler", frame=f)
        key(sun.data, "energy", 7.0 * dl, f)
        sun.data.color = mix_color(srgb("#FFF1DC"), srgb("#FFB070"), w)
        sun.data.keyframe_insert("color", frame=f)
        # Moon: the night's arc, from 18:00 to 06:00.
        ms = ((hh - 18.0) % 24) / 12.0
        # By day, while it's out of sight, the moonlight eases back to where
        # its arc starts, so its direction never jumps.
        ma = math.pi * (ms if ms <= 1 else ease(2 - ms))
        moon_dir = Vector((math.cos(ma), 1.3, max(0.2, math.sin(ma)) * 1.1)).normalized()
        moon.rotation_euler = (-moon_dir).to_track_quat("-Z", "Y").to_euler("XYZ", moon.rotation_euler)
        moon.keyframe_insert("rotation_euler", frame=f)
        key(moon.data, "energy", 0.5 * night, f)
        key(fill.data, "energy", lerp(230, 800, d) + 150 * w, f)
        fill.data.color = mix_color(srgb("#9FB0E0"), srgb("#FFF4E6"), dl)
        fill.data.keyframe_insert("color", frame=f)
        # Sky and backdrop colours.
        top = mix_color(mix_color(SKY["night_top"], SKY["day_top"], dl), SKY["warm_top"], w * 0.8)
        low = mix_color(mix_color(SKY["night_low"], SKY["day_low"], dl), SKY["warm_low"], w * 0.9)
        sky_mix.inputs["B"].default_value = (*top, 1)
        sky_mix.inputs["B"].keyframe_insert("default_value", frame=f)
        sky_mix.inputs["A"].default_value = (*low, 1)
        sky_mix.inputs["A"].keyframe_insert("default_value", frame=f)
        bd = mix_color(mix_color(BACKDROP["night"], BACKDROP["day"], dl), BACKDROP["warm"], w * 0.6)
        backdrop.inputs["Color"].default_value = (*bd, 1)
        backdrop.inputs["Color"].keyframe_insert("default_value", frame=f)
        ambient.inputs["Color"].default_value = (*mix_color(srgb("#3A4670"), srgb("#E9F0F8"), dl), 1)
        ambient.inputs["Color"].keyframe_insert("default_value", frame=f)
        key(ambient.inputs["Strength"], "default_value", lerp(0.22, 0.55, d), f)
        # Discs cross the window.
        def arc(t):
            return Vector((1.45 - 1.4 * t, yw, 0.95 + 0.85 * math.sin(math.pi * t)))
        sun_disc.location = arc(min(1, max(0, s))) if 0 <= s <= 1 else Vector((0.5, yw, -1))
        sun_disc.keyframe_insert("location", frame=f)
        moon_disc.location = arc(ms) if ms <= 1 else Vector((0.5, yw, -1))
        moon_disc.keyframe_insert("location", frame=f)
        key(star_em.inputs["Strength"], "default_value", 3.0 * night, f)
        # Evening life: the lamp on from dusk until bedtime, neighbours too.
        # Fades over two hours (about half a second) at dusk and at bedtime;
        # the fade out ends by midnight, where hh wraps back to 0.
        evening = ease((hh - 17.0) / 2.0) * (1 - ease((hh - 22.0) / 2.0))
        key(lamp.data, "energy", 55.0 * evening, f)
        key(shade_em, "default_value", 1.6 * evening, f)
        key(lit_em, "default_value", 2.2 * max(night, evening * 0.6), f)
    set_interpolation("BEZIER")


def smoother(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


def animate_box_arrival(bx):
    """The box grows into view as it is set down, then settles with a soft
    squash, like a toy placed on a shelf."""
    holder = bx["holder"]
    rest = holder.location.copy()
    s = BOX_SCALE
    f0, f1 = DROP
    key(holder, "location", rest + Vector((0, 0, 0.12)), 1)
    key(holder, "scale", (s * 0.001,) * 3, 1)
    key(holder, "location", rest + Vector((0, 0, 0.12)), f0)
    key(holder, "scale", (s * 0.001,) * 3, f0)
    key(holder, "scale", (s,) * 3, f0 + 14)
    key(holder, "location", rest, f1)
    key(holder, "scale", (s * 1.04, s * 1.04, s * 0.9), f1 + 4)
    key(holder, "scale", (s * 0.99, s * 0.99, s * 1.025), f1 + 11)
    key(holder, "scale", (s,) * 3, f1 + 18)
    for o in [holder] + bx["parts"]:
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=1)
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=f0)


def animate_cord(cord_info, plug, f0, f1):
    """Grow a cord along its path, its plug leading, at an unhurried pace
    that slows as the plug slides home."""
    o, pts, cum = cord_info
    total, n = cum[-1], len(pts)
    tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    # Orientation exact at the socket, carried back along the path so the
    # plug turns smoothly through every bend.
    quats = [None] * n
    quats[-1] = tang[-1].to_track_quat("-X", "Z")
    for i in range(n - 2, -1, -1):
        quats[i] = tang[i + 1].rotation_difference(tang[i]) @ quats[i + 1]

    def at(dist):
        import bisect
        i = min(max(bisect.bisect_right(cum, dist) - 1, 0), n - 2)
        seg = cum[i + 1] - cum[i]
        t = 0.0 if seg == 0 else (dist - cum[i]) / seg
        return pts[i].lerp(pts[i + 1], t), quats[i].slerp(quats[i + 1], t)

    o.data.bevel_factor_mapping_end = "SPLINE"
    set_interpolation("LINEAR")
    prev = None
    for f in [1] + list(range(f0, f1 + 1)):
        e = 0.0 if f <= f0 else smoother((f - f0) / (f1 - f0))
        key(o.data, "bevel_factor_end", e, f)
        loc, q = at(total * e)
        if prev is not None and prev.dot(q) < 0:
            q = -q
        prev = q
        plug.location = loc
        plug.keyframe_insert("location", frame=f)
        plug.rotation_quaternion = q
        plug.keyframe_insert("rotation_quaternion", frame=f)
    set_interpolation("BEZIER")
    for ob in (o, plug):
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=1)
        ob.hide_render = False
        ob.keyframe_insert("hide_render", frame=f0)


def animate_light(m, glow):
    """The status light fades on, glows a touch brighter, then settles."""
    led = principled(m["led"]).inputs["Emission Strength"]
    f0, f1 = LIGHT
    for f, v in ((f0, 0.0), (f1, 10.0), (f1 + 10, 16.0), (f1 + 34, 11.0)):
        key(led, "default_value", v, f)
    for f, v in ((f0, 0.0), (f1, 0.25), (f1 + 10, 0.4), (f1 + 34, 0.28)):
        key(glow, "energy", v, f)


def pop(o, f_in, f_out=None, size=1.0):
    """Scale an object up with a little overshoot, and back down."""
    key(o, "scale", (0.0001,) * 3, 1)
    key(o, "scale", (0.0001,) * 3, f_in)
    key(o, "scale", (size * 1.06,) * 3, f_in + 9)
    key(o, "scale", (size,) * 3, f_in + 15)
    if f_out:
        key(o, "scale", (size,) * 3, f_out - 10)
        key(o, "scale", (0.0001,) * 3, f_out)


def animate_cards(chart, bars, wifi, rows, aspect):
    card_in = DAYS[0] + 62  # once the camera has settled
    pop(chart, card_in, CALM[0] + 6, size=1.25)
    for i, b in enumerate(bars):
        group, k = divmod(i, 3)
        slot_hour = (13.0, 20.5, 26.0)[k] + 24 * group
        f = max(card_in + 14 + 6 * i, int(DAYS[0] + (slot_hour - 9.5) / (72.0 / (DAYS[1] - DAYS[0]))))
        key(b, "scale", (1, 0.0001, 1), 1)
        key(b, "scale", (1, 0.0001, 1), f)
        key(b, "scale", (1, 1, 1), f + 10)
    pop(wifi, WIFI[0] + 30, END[0] + 10, size=1.15)
    pop(rows["before"], WIFI[0] + 40, SWITCH + 4)
    pop(rows["after"], SWITCH + 4)


def animate_icon(icon, parts):
    """Crowded: the arcs stutter, the outer ones barely holding. After the
    switch they turn green and ripple outward, calm and even."""
    start, stop = WIFI[0] + 30, END[0] + 5
    pop(icon, start, stop, size=1.0)
    set_interpolation("LINEAR")
    amber, green = srgb("#F2A43A"), srgb("#34C77B")
    for f in [1, start - 1] + list(range(start, stop + 1, 2)):
        live = start <= f <= stop
        blend = smoother((f - SWITCH) / 20)
        for k, o in enumerate(parts):
            nt = o.active_material.node_tree
            crowded = (1.0, 0.85, 0.35 + 0.35 * max(0.0, math.sin(f * 0.31)),
                       0.12 + 0.3 * max(0.0, math.sin(f * 0.19 + 1.7)))[k]
            ripple = 0.72 + 0.28 * math.sin(2 * math.pi * f / 40 - k * 0.9)
            a = lerp(crowded, ripple, blend) if live else 0.0
            key(nt.nodes["Alpha"].inputs["Fac"], "default_value", a, f)
            em = nt.nodes["Emission"].inputs["Color"]
            em.default_value = (*mix_color(amber, green, blend), 1)
            em.keyframe_insert("default_value", frame=f)
    set_interpolation("BEZIER")


def animate_steam(puffs, origin):
    set_interpolation("LINEAR")
    period = 70
    for f in range(1, FRAMES + 2, 2):
        for i, p in enumerate(puffs):
            t = ((f + i * period / len(puffs)) % period) / period
            p.location = origin + Vector((0.012 * math.sin(t * 5 + i), 0.008 * math.cos(t * 4 + i), 0.16 * t))
            p.keyframe_insert("location", frame=f)
            sc = 0.6 + 1.8 * t
            p.scale = (sc, sc, sc * 1.3)
            p.keyframe_insert("scale", frame=f)
            key(p.active_material.node_tree.nodes["Alpha"].inputs["Fac"], "default_value",
                0.12 * math.sin(math.pi * t) ** 1.5, f)
    set_interpolation("BEZIER")


def animate_phone(screen_mat):
    s = principled(screen_mat).inputs["Emission Strength"]
    key(s, "default_value", 0.0, SWITCH - 2)
    key(s, "default_value", 2.2, SWITCH + 6)
    key(s, "default_value", 2.2, SWITCH + 60)
    key(s, "default_value", 0.0, SWITCH + 80)


# ---------------------------------------------------------------- camera

# Shots: (frame, target, azimuth from -Y toward +X in degrees, elevation in
# degrees, distance in metres, f-stop). Tall framing pulls back further.
SHOTS = {
    "wide": [
        (1, (-0.05, 0.15, 0.85), 54, 33, 12.8, 11),
        (SETUP, (-0.1, 0.25, 0.85), 47, 31, 11.8, 11),
        (DROP[0] + 20, (BOX_AT[0] + 0.14, BOX_AT[1] + 0.02, CONSOLE[2] + 0.06), 32, 25, 2.15, 4.5),
        (LIGHT[1] + 6, (BOX_AT[0] + 0.12, BOX_AT[1] + 0.02, CONSOLE[2] + 0.06), 25, 22, 1.95, 4.5),
        (DAYS[0] + 60, (-0.3, 0.9, 1.35), 34, 24, 6.6, 8),
        (DAYS[1] - 20, (-0.25, 0.9, 1.35), 44, 25, 6.2, 8),
        (CALM[0] + 60, (BOX_AT[0] + 0.1, BOX_AT[1], CONSOLE[2] + 0.06), 30, 20, 2.3, 4.5),
        (CALM[1], (BOX_AT[0] + 0.1, BOX_AT[1], CONSOLE[2] + 0.06), 35, 20, 2.15, 4.5),
        (WIFI[0] + 70, (-0.5, 1.1, 1.2), 31, 25, 4.7, 6),
        (WIFI[1] - 10, (-0.45, 1.05, 1.2), 37, 25, 4.4, 6),
        (FRAMES, (-0.05, 0.15, 0.85), 50, 32, 13.2, 11),
    ],
}
# Portrait framing: same moments, further back and a little higher.
SHOTS["tall"] = [(f, t, az, el + 2, dist * (1.2 if dist > 8 else 1.5 if dist > 3 else 1.3), fs)
                 for f, t, az, el, dist, fs in SHOTS["wide"]]


def camera(aspect):
    scene = bpy.context.scene
    data = bpy.data.cameras.new("Camera")
    data.lens = 50
    data.sensor_width = 36
    data.clip_start = 0.05
    data.clip_end = 100
    cam = bpy.data.objects.new("Camera", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    target = bpy.data.objects.new("Camera target", None)
    scene.collection.objects.link(target)
    c = cam.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    data.dof.use_dof = True
    data.dof.focus_object = target
    for f, t, az, el, dist, fstop in SHOTS[aspect]:
        t = Vector(t)
        a, e = math.radians(az), math.radians(el)
        offset = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        key(target, "location", t, f)
        key(cam, "location", t + offset, f)
        key(data.dof, "aperture_fstop", fstop, f)
    return cam


def face_camera(objs, cam):
    for o in objs:
        c = o.constraints.new("TRACK_TO")
        c.target = cam
        c.track_axis = "TRACK_Z"
        c.up_axis = "UP_Y"


# ---------------------------------------------------------------- render

def configure(opts):
    scene = bpy.context.scene
    r = scene.render
    short = opts["res"] or (720 if opts["draft"] else 1080)
    long_side = round(short * 16 / 9 / 2) * 2
    r.resolution_x, r.resolution_y = (long_side, short) if opts["aspect"] == "wide" else (short, long_side)
    r.resolution_percentage = 100
    r.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.frame_step = 2 if opts["draft"] else 1
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = 0.0
    if opts["draft"]:
        for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                r.engine = engine
                break
            except TypeError:
                continue
        ee = scene.eevee
        for attr, value in (("taa_render_samples", 32), ("use_raytracing", True), ("use_shadows", True),
                            ("shadow_ray_count", 2), ("use_gtao", True)):
            if hasattr(ee, attr):
                setattr(ee, attr, value)
    else:
        r.engine = "CYCLES"
        # Keep the scene loaded between frames: about half the time per frame.
        r.use_persistent_data = True
        # Camera motion blur, for smooth, filmic movement.
        r.use_motion_blur = True
        r.motion_blur_shutter = 0.5
        # 16-bit frames, so the soft sky and backdrop gradients don't band.
        r.image_settings.color_depth = "16"
        c = scene.cycles
        c.denoiser = "OPENIMAGEDENOISE"
        for attr, value in (("denoising_use_gpu", True), ("denoising_prefilter", "ACCURATE"),
                            ("denoising_input_passes", "RGB_ALBEDO_NORMAL"), ("denoising_quality", "HIGH")):
            if hasattr(c, attr):
                setattr(c, attr, value)
        scene.cycles.samples = opts["samples"]
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.transparent_max_bounces = 16
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.kernel_optimization_level = "OFF"  # see build_box.py
            prefs.get_devices()
            # GPU only: adding the CPU barely speeds Apple silicon up and
            # runs every core flat out, fans and all.
            for d in prefs.devices:
                d.use = d.type != "CPU"
            scene.cycles.device = "GPU"
        except Exception as e:
            print("GPU unavailable, rendering on CPU:", e)


def bloom():
    """A soft glow around lights, through the compositor."""
    scene = bpy.context.scene
    try:
        ng = bpy.data.node_groups.new("Compositor", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        glare = ng.nodes.new("CompositorNodeGlare")
        out = ng.nodes.new("NodeGroupOutput")
        settings = {"Type": "Bloom", "Quality": "High", "Threshold": 1.0, "Strength": 0.35, "Size": 0.6}
        for name, value in settings.items():
            sock = glare.inputs.get(name)
            if sock is not None:
                sock.default_value = value
        ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
        ng.links.new(glare.outputs["Image"], out.inputs[0])
        scene.compositing_node_group = ng
    except Exception as e:  # older Blender: no bloom, still renders
        print("bloom unavailable:", e)


def options():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"aspect": "wide", "draft": False, "stills": [], "animation": False, "res": 0, "samples": 64}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--draft":
            opts["draft"] = True
        elif a == "--animation":
            opts["animation"] = True
        elif a == "--aspect":
            i += 1
            opts["aspect"] = argv[i]
            if opts["aspect"] not in ("wide", "tall"):
                raise SystemExit("--aspect must be wide or tall")
        elif a == "--stills":
            i += 1
            opts["stills"] = [int(f) for f in argv[i].split(",")]
        elif a in ("--res", "--samples"):
            i += 1
            opts[a[2:]] = int(argv[i])
        else:
            raise SystemExit(f"unknown option {a}")
        i += 1
    return opts


def main():
    opts = options()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_set(1)

    m = palette()
    bm = B["materials"]()
    B["materials_dark"] = bm["dark"]
    m["cable"] = bm["rubber"]
    m["led"] = bm["led"]

    room(m)
    window(m)
    view = outside(m)
    _, life = furniture(m)
    wall_decor(m)
    router(m, m["cable"])
    bx = the_box(bm)
    eth_plug, pwr_plug, eth_home, pwr_home = plug_heads(bm, bx["holder"])
    eth_cord, pwr_cord = cords(m["cable"], eth_home, pwr_home)
    chart, bars = chart_card(m)
    wifi, rows = wifi_card(m)
    icon, icon_parts = wifi_icon()
    puffs, steam_origin = steam_puffs()

    # Cards float where they don't hide the box: the chart over the TV, the
    # Wi-Fi card beside the router.
    chart.location = (-1.2, CONSOLE[1] - 0.3, 1.9)
    wifi.location = (-0.75, CONSOLE[1] - 0.45, 1.72)
    for card in (chart, wifi):
        card.scale = (0.0001,) * 3

    # LED glow: a small green light just in front of the status light.
    glow = bpy.data.lights.new("LED glow", "POINT")
    glow.color = srgb("#2CFF6E")
    glow.shadow_soft_size = 0.01
    glow.energy = 0.0
    glow.specular_factor = 0.0
    glow.shadow_soft_size = 0.03
    glow_o = bpy.data.objects.new("LED glow", glow)
    scene.collection.objects.link(glow_o)
    glow_o.location = bx["led_world"] + Vector((0, -0.015, 0))

    sun, moon, fill = lights()
    backdrop, ambient = world()
    animate_time(sun, moon, fill, view["sky"], view["sun"], view["moon"], view["stars"], backdrop, ambient,
                 life["lamp"], m["shade"], m["window_lit"])
    animate_box_arrival(bx)
    animate_cord(eth_cord, eth_plug, *ETH)
    animate_cord(pwr_cord, pwr_plug, *POWER)
    animate_light(m, glow)
    cam = camera(opts["aspect"])
    face_camera([chart, wifi, icon], cam)
    animate_cards(chart, bars, wifi, rows, opts["aspect"])
    animate_icon(icon, icon_parts)
    animate_steam(puffs, steam_origin)
    animate_phone(m["screen"])

    configure(opts)
    bloom()
    quality = "draft" if opts["draft"] else "final"
    out = os.path.join(OUT, f"{opts['aspect']}-{quality}")
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"demo-{opts['aspect']}.blend"))

    for frame in opts["stills"]:
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(out, f"still-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    if opts["animation"]:
        scene.render.filepath = os.path.join(out, "frames", "")
        scene.render.use_overwrite = False  # resume after an interruption
        bpy.ops.render.render(animation=True)
    print("built demo", opts)


main()
