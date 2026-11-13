"""Build the showcase animation of the measuring box.

A Raspberry Pi 4 drops onto its base, a white shell lowers over it, an
Ethernet cable and a power cable plug in, and a status light turns on.

Run from the repository root:

    BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
    $BLENDER -b -P design/box/build_box.py                          # model, .blend, .glb
    $BLENDER -b -P design/box/build_box.py -- --stills 1,60,120,180  # preview frames
    $BLENDER -b -P design/box/build_box.py -- --animation            # every frame

Options after `--`: --res N (square, default 1080), --samples N (default 64).

Writes the model and its motion to apps/web/public/box/box.glb, which the
website plays as you scroll, and box.blend, still-NNN.png and frames/NNNN.png
(transparent background) to design/box/out/. Compress the model before
committing it (about 1.2 MB down to about 0.3 MB):

    npx @gltf-transform/cli meshopt apps/web/public/box/box.glb apps/web/public/box/box.glb

Built in millimetres, scaled to metres before export. X runs along the
board's long side, Y along its short side, Z up. The isometric camera sees
the top, the +X end (Ethernet) and the -Y side (USB-C power).
"""

import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
# The website loads the model from here and plays it as you scroll.
WEB_GLB = os.path.join(HERE, "..", "..", "apps", "web", "public", "box", "box.glb")
FPS = 30
FRAMES = 180

# Raspberry Pi 4 Model B: 85 x 56 mm board, centred on the origin.
BOARD_L, BOARD_W, PCB = 85.0, 56.0, 1.4
BOARD_Z = 7.0  # underside of the board, on standoffs above the base
TOP = BOARD_Z + PCB  # top of the board


def pi_xy(x, y):
    """Convert Raspberry Pi drawing coordinates, from the board's corner
    by the USB-C port, to model coordinates."""
    return x - BOARD_L / 2, y - BOARD_W / 2


# Case.
CASE_L, CASE_W = 96.0, 66.0
BASE_H = 4.0
CASE_TOP = 29.0
CORNER = 18.0
SQUIRCLE = 0.68  # bevel profile for continuous-curvature corners
WALL = 2.0

# Ports, in model coordinates.
ETH_Y = pi_xy(0, 45.75)[1]
ETH_FRONT = BOARD_L / 2 + 2.0  # the jack overhangs the board edge
ETH_Z = TOP + 6.75
USBC_X = pi_xy(11.2, 0)[0]
USBC_Z = TOP + 1.65
LED = (30.0, 17.0)  # status light on the -Y face: x, z


# ---------------------------------------------------------------- materials

def srgb(hex_color):
    """Convert #rrggbb to the linear RGB Blender expects."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def material(name, hex_color, rough=0.5, metal=0.0, coat=0.0, transmission=0.0,
             emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*srgb(hex_color), 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Transmission Weight"].default_value = transmission
    if emit:
        p.inputs["Emission Color"].default_value = (*srgb(emit), 1.0)
        p.inputs["Emission Strength"].default_value = strength
    return m


def materials():
    return {
        "white": material("Case White", "#F4F4F2", rough=0.38, coat=0.15),
        "pcb": material("Board Green", "#126B38", rough=0.45, coat=0.4),
        "metal": material("Metal", "#C9CDD2", rough=0.25, metal=1.0),
        "gold": material("Gold", "#E2B656", rough=0.3, metal=1.0),
        "black": material("Black Plastic", "#18191B", rough=0.5),
        "blue": material("USB 3 Blue", "#1F5FD6", rough=0.45),
        "ivory": material("Connector Ivory", "#E9E2CF", rough=0.5),
        "smd": material("SMD Ceramic", "#A9825A", rough=0.5),
        "silk": material("Silkscreen", "#F3F3EE", rough=0.6),
        "inductor": material("Inductor", "#3E4146", rough=0.45),
        "jack_green": material("Jack Green", "#3FD46E", rough=0.3, emit="#3FD46E", strength=0.6),
        "jack_amber": material("Jack Amber", "#F2A93B", rough=0.3, emit="#F2A93B", strength=0.6),
        "dark": material("Port Interior", "#0E0F10", rough=0.8),
        "plug": material("Plug Clear", "#EEF3F6", rough=0.12, transmission=0.6),
        "rubber": material("Cable White", "#F2F2F0", rough=0.6),
        "foot": material("Foot Gray", "#8E9196", rough=0.55),
        "led": material("Status Light", "#C4C9C6", rough=0.25, emit="#0FD94F", strength=0.0),
    }


# ---------------------------------------------------------------- geometry

def activate(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply_modifiers(o):
    activate(o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def assign(o, mat):
    o.data.materials.clear()
    o.data.materials.append(mat)


def box(name, size, loc, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        assign(o, mat)
    return o


def rounded(name, size, loc, radius, axis, mat=None, segments=8, edge=0.0, profile=0.5, edge_segments=5):
    """A box whose edges parallel to `axis` (0, 1 or 2) are rounded by
    `radius`; `edge` then softens the remaining sharp edges. A `profile`
    above 0.5 gives a continuous-curvature (squircle) corner, not a circle."""
    o = box(name, size, loc, mat)
    mesh = o.data
    weights = mesh.attributes.new("bevel_weight_edge", "FLOAT", "EDGE")
    for e in mesh.edges:
        a, b = (mesh.vertices[i].co for i in e.vertices)
        d = b - a
        weights.data[e.index].value = 1.0 if abs(d[axis]) > 0.99 * d.length else 0.0
    bev = o.modifiers.new("round", "BEVEL")
    bev.limit_method = "WEIGHT"
    bev.width = radius
    bev.segments = segments
    bev.profile = profile
    if edge:
        soft = o.modifiers.new("soften", "BEVEL")
        soft.limit_method = "ANGLE"
        soft.angle_limit = math.radians(40)
        soft.width = edge
        soft.segments = edge_segments
        soft.profile = profile
    apply_modifiers(o)
    return o


def cylinder(name, radius, depth, loc, mat=None, axis=2, vertices=40):
    rotation = {0: (0, math.pi / 2, 0), 1: (math.pi / 2, 0, 0), 2: (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc,
                                        rotation=rotation, vertices=vertices)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.transform_apply(rotation=True)
    if mat:
        assign(o, mat)
    return o


def cut(target, cutter, mat):
    """Subtract cutter from target; the new faces take `mat`."""
    assign(cutter, mat)
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    mod.object = cutter
    apply_modifiers(target)
    bpy.data.objects.remove(cutter, do_unlink=True)


def join(objects, name):
    for o in objects:
        smooth(o)
    activate(objects[0])
    for o in objects[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def smooth(o, angle=35):
    activate(o)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except (AttributeError, RuntimeError):
        bpy.ops.object.shade_smooth()


# ---------------------------------------------------------------- the board

def raspberry_pi(m):
    parts = []
    z = BOARD_Z + PCB / 2

    pcb = rounded("PCB", (BOARD_L, BOARD_W, PCB), (0, 0, z), 3.0, axis=2, mat=m["pcb"])
    holes = [pi_xy(x, y) for x in (3.5, 61.5) for y in (3.5, 52.5)]
    rings = [cylinder(f"ring{i}", 3.0, PCB + 0.1, (x, y, z), m["gold"]) for i, (x, y) in enumerate(holes)]
    for i, (x, y) in enumerate(holes):
        cut(pcb, cylinder(f"hole{i}", 1.35, 4, (x, y, z)), m["gold"])
        cut(rings[i], cylinder(f"hole{i}b", 1.35, 4, (x, y, z)), m["gold"])
    parts += [pcb, *rings]

    # Ethernet jack, opening toward +X.
    jack = rounded("Ethernet jack", (21, 16, 13.5), (ETH_FRONT - 10.5, ETH_Y, TOP + 6.75), 0.8, axis=0,
                   mat=m["metal"])
    cut(jack, rounded("eth_cavity", (12, 12, 9), (ETH_FRONT - 4, ETH_Y, ETH_Z - 0.5), 0.5, axis=0), m["dark"])
    cut(jack, box("eth_latch", (12, 6, 2.2), (ETH_FRONT - 4, ETH_Y, ETH_Z - 5.6)), m["dark"])
    parts.append(jack)
    for dy, lamp in ((-5.9, m["jack_green"]), (5.9, m["jack_amber"])):
        parts.append(box(f"eth_lamp{dy}", (0.3, 2.6, 1.6), (ETH_FRONT + 0.1, ETH_Y + dy, ETH_Z + 5.4), lamp))
    for i in range(8):
        parts.append(box(f"eth_pin{i}", (5, 0.55, 0.4), (ETH_FRONT - 8, ETH_Y + (i - 3.5) * 1.1, ETH_Z + 3.7),
                         m["gold"]))

    # Two USB stacks: USB 3 (blue) and USB 2 (black).
    for name, y_pi, tongue in (("USB 3", 27.0, m["blue"]), ("USB 2", 9.0, m["black"])):
        y = pi_xy(0, y_pi)[1]
        front = BOARD_L / 2 + 2.5
        stack = box(name, (17.5, 13.2, 16), (front - 8.75, y, TOP + 8), m["metal"])
        for k, dz in enumerate((4.2, 11.8)):
            cut(stack, box(f"{name}_slot{k}", (10, 12, 5.4), (front - 2, y, TOP + dz)), m["dark"])
            parts.append(box(f"{name}_tongue{k}", (9, 10.6, 1.8), (front - 5, y, TOP + dz + 0.9), tongue))
        parts.append(stack)
        # A front flange and spring tabs, as on the real metal shells.
        flange = box(f"{name} flange", (0.4, 14.0, 16.8), (front - 0.2, y, TOP + 8), m["metal"])
        for k, dz in enumerate((4.2, 11.8)):
            cut(flange, box(f"{name}_fslot{k}", (2, 12.2, 5.6), (front - 0.2, y, TOP + dz)), m["dark"])
        parts.append(flange)
        for dy in (-3.5, 3.5):
            parts.append(box(f"{name}_tab{dy}", (3, 2.2, 0.25), (front - 6, y + dy, TOP + 16.1), m["metal"]))

    # USB-C power, micro-HDMI and audio along the -Y edge.
    edge = -BOARD_W / 2 - 1.5
    usbc = rounded("USB-C", (9, 7.5, 3.2), (USBC_X, edge + 3.75, USBC_Z), 1.5, axis=1, mat=m["metal"])
    cut(usbc, rounded("usbc_cavity", (8.2, 6, 2.4), (USBC_X, edge + 1.5, USBC_Z), 1.1, axis=1), m["dark"])
    parts.append(usbc)
    for i, x_pi in enumerate((26.0, 39.5)):
        x = pi_xy(x_pi, 0)[0]
        hdmi = box(f"micro-HDMI {i}", (6.5, 7.5, 3), (x, edge + 3.75, TOP + 1.5), m["metal"])
        cut(hdmi, box(f"hdmi_cavity{i}", (5.6, 6, 2.2), (x, edge + 1.5, TOP + 1.5)), m["dark"])
        parts.append(hdmi)
    audio_x = pi_xy(54.0, 0)[0]
    audio = rounded("Audio", (7, 12.5, 6), (audio_x, edge + 6.25, TOP + 3), 1.0, axis=1, mat=m["black"])
    cut(audio, cylinder("audio_hole", 1.75, 6, (audio_x, edge, TOP + 3), axis=1), m["dark"])
    parts.append(audio)

    # GPIO header: 2 x 20 gold pins in a black strip along the far edge.
    gx0, gy = pi_xy(7.1, 52.5)
    parts.append(box("GPIO", (50.8, 5.08, 2.5), (gx0 + 25.4, gy, TOP + 1.25), m["black"]))
    for i in range(20):
        for dy in (-1.27, 1.27):
            parts.append(box(f"pin{i}{dy}", (0.64, 0.64, 8.5), (gx0 + 1.27 + i * 2.54, gy + dy, TOP + 4.25),
                             m["gold"]))

    # Chips.
    soc = rounded("SoC", (15, 15, 2.4), (-13, 4, TOP + 1.2), 1.2, axis=2, mat=m["metal"], edge=0.4)
    parts += [
        soc,
        box("RAM", (10, 14, 1.2), (4, 4, TOP + 0.6), m["black"]),
        box("Wireless", (11, 13, 1.6), (-34, 10, TOP + 0.8), m["metal"]),
        box("USB controller", (7, 7, 1.0), (17, -6, TOP + 0.5), m["black"]),
        box("Ethernet PHY", (6, 6, 0.9), (13, 15, TOP + 0.45), m["black"]),
        box("Power chip", (5, 5, 0.9), (-30, -15, TOP + 0.45), m["black"]),
        box("Camera connector", (3, 22, 5), (2.5, -15, TOP + 2.5), m["ivory"]),
        box("Display connector", (3, 22, 5), (-39, -4, TOP + 2.5), m["ivory"]),
    ]
    parts += board_details(m)
    return join(parts, "Raspberry Pi")


# Areas of the board taken by the large parts, as (x0, x1, y0, y1).
KEEP_OUT = [
    (23.5, 44.5, 9.75, 25.75), (27.5, 45, -7.6, 5.6), (27.5, 45, -25.6, -12.4),  # Ethernet, USB
    (-35.8, -26.8, -29.5, -22), (-19.8, -13.2, -29.5, -22), (-6.3, 0.3, -29.5, -22),  # USB-C, HDMI
    (8, 15, -29.5, -17), (-35.4, 15.4, 21.9, 27.1),  # audio, GPIO
    (-20.5, -5.5, -3.5, 11.5), (-1, 9, -3, 11), (-39.5, -28.5, 3.5, 16.5),  # SoC, RAM, wireless
    (13.5, 20.5, -9.5, -2.5), (10, 16, 12, 18), (-32.5, -27.5, -17.5, -12.5),  # chips
    (1, 4, -26, -4), (-40.5, -37.5, -15, 7), (-30, 0, 14, 19),  # connectors, label
] + [(x - 3.2, x + 3.2, y - 3.2, y + 3.2) for x, y in [pi_xy(a, b) for a in (3.5, 61.5) for b in (3.5, 52.5)]]


def board_details(m):
    """The small things that make a board read as real: surface-mount parts,
    printed outlines and label, test pads and mounting screws."""
    parts = []
    rng = random.Random(7)  # fixed, so every build places parts the same way
    taken = [(x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6) for x0, x1, y0, y1 in KEEP_OUT]
    kinds = [  # (width, depth, height, material, weight)
        (1.0, 0.5, 0.5, "smd", 50), (1.6, 0.8, 0.45, "black", 25), (2.0, 1.25, 0.8, "smd", 15),
        (3.2, 3.2, 1.6, "inductor", 5), (2.6, 2.6, 0.8, "black", 5),
    ]
    weights = [k[4] for k in kinds]
    placed = 0
    for _ in range(1500):
        if placed >= 110:
            break
        w, d, h, mat, _ = rng.choices(kinds, weights)[0]
        if rng.random() < 0.5:
            w, d = d, w
        x, y = rng.uniform(-41, 41), rng.uniform(-26.5, 26.5)
        rect = (x - w / 2 - 0.35, x + w / 2 + 0.35, y - d / 2 - 0.35, y + d / 2 + 0.35)
        if any(r[0] < rect[1] and rect[0] < r[1] and r[2] < rect[3] and rect[2] < r[3] for r in taken):
            continue
        taken.append(rect)
        parts.append(box(f"smd{placed}", (w, d, h), (x, y, TOP + h / 2), m[mat]))
        placed += 1
    for i in range(14):  # gold test pads in the remaining space
        for _ in range(200):
            x, y = rng.uniform(-41, 41), rng.uniform(-26.5, 26.5)
            rect = (x - 0.8, x + 0.8, y - 0.8, y + 0.8)
            if not any(r[0] < rect[1] and rect[0] < r[1] and r[2] < rect[3] and rect[2] < r[3] for r in taken):
                taken.append(rect)
                parts.append(cylinder(f"pad{i}", 0.5, 0.06, (x, y, TOP + 0.03), m["gold"], vertices=16))
                break

    # Printed outlines around the chips, and the board's label.
    def outline(x0, x1, y0, y1, t=0.18):
        z = TOP + 0.015
        return [box("silk", (x1 - x0, t, 0.03), ((x0 + x1) / 2, y, z), m["silk"]) for y in (y0, y1)] + \
               [box("silk", (t, y1 - y0, 0.03), (x, (y0 + y1) / 2, z), m["silk"]) for x in (x0, x1)]
    for x0, x1, y0, y1 in [(-21.3, -4.7, -4.3, 12.3), (-1.8, 9.8, -3.8, 11.8), (12.7, 21.3, -10.3, -1.7),
                           (9.2, 16.8, 11.2, 18.8), (-33.3, -26.7, -18.3, -11.7)]:
        parts += outline(x0, x1, y0, y1)
    curve = bpy.data.curves.new("label", "FONT")
    curve.body = "Raspberry Pi 4 Model B"
    curve.size = 2.1
    curve.extrude = 0.01
    curve.align_x = curve.align_y = "CENTER"
    font = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if os.path.exists(font):
        curve.font = bpy.data.fonts.load(font)
    label = bpy.data.objects.new("label", curve)
    bpy.context.collection.objects.link(label)
    label.location = (-15, 16.5, TOP + 0.02)
    activate(label)
    bpy.ops.object.convert(target="MESH")
    assign(label, m["silk"])
    parts.append(label)

    # Mounting screws, with a cross in each head.
    for i, (x, y) in enumerate(pi_xy(a, b) for a in (3.5, 61.5) for b in (3.5, 52.5)):
        screw = cylinder(f"screw{i}", 2.4, 0.9, (x, y, TOP + 0.45), m["metal"], vertices=32)
        for rot in (0, 90):
            slot = box(f"slot{i}{rot}", (2.6, 0.5, 1.2), (x, y, TOP + 0.9), None)
            slot.rotation_euler = (0, 0, math.radians(rot))
            cut(screw, slot, m["dark"])
        parts.append(screw)
    return parts


# ---------------------------------------------------------------- the case

def case_base(m):
    # Dark and recessed, so a shadow line separates it from the shell.
    inset = 4.0  # tucked well under the shell, so the case seems to float
    base = rounded("Base", (CASE_L - 2 * inset, CASE_W - 2 * inset, BASE_H), (0, 0, BASE_H / 2), CORNER - inset,
                   axis=2, mat=m["foot"], segments=20, edge=1.0, profile=SQUIRCLE)
    posts = [cylinder(f"post{i}", 2.6, BOARD_Z - BASE_H + 0.5, (x, y, (BOARD_Z + BASE_H) / 2 - 0.25),
                      m["foot"])
             for i, (x, y) in enumerate(pi_xy(x, y) for x in (3.5, 61.5) for y in (3.5, 52.5))]
    return join([base, *posts], "Base")


def case_shell(m):
    height = CASE_TOP - BASE_H
    # One soft, continuous form: squircle corners and full top edges that roll
    # into the sides, rather than a box with its corners rounded off.
    shell = rounded("Shell", (CASE_L, CASE_W, height), (0, 0, BASE_H + height / 2), CORNER, axis=2,
                    mat=m["white"], segments=20, edge=5.5, profile=SQUIRCLE, edge_segments=10)
    inner = rounded("inner", (CASE_L - 2 * WALL, CASE_W - 2 * WALL, height),
                    (0, 0, BASE_H + height / 2 - WALL), CORNER - WALL, axis=2, segments=20, edge=3.5,
                    profile=SQUIRCLE, edge_segments=8)
    cut(shell, inner, m["white"])

    x_wall, y_wall = CASE_L / 2, -CASE_W / 2
    # Openings fitted closely to their connectors.
    cut(shell, rounded("eth_hole", (8, 16.6, 14.4), (x_wall, ETH_Y, ETH_Z), 1.6, axis=0), m["white"])
    cut(shell, rounded("usbc_hole", (9.6, 8, 3.8), (USBC_X, y_wall, USBC_Z), 1.9, axis=1), m["white"])
    # A flush USB-C port in the wall. The board's own port sits too far
    # inside to see, which left the opening looking like an empty vent.
    port_depth = 2.2
    port_y = y_wall + 0.15 + port_depth / 2
    port = rounded("Power port", (9.0, port_depth, 3.2), (USBC_X, port_y, USBC_Z), 1.6, axis=1, mat=m["metal"])
    cut(port, rounded("port_cavity", (8.2, 2.5, 2.4), (USBC_X, y_wall - 0.5 + 1.25, USBC_Z), 1.2, axis=1),
        m["dark"])
    tongue = box("Power port tongue", (5.8, 1.6, 0.6), (USBC_X, y_wall + 1.1, USBC_Z), m["black"])

    # Status light: a slim line, case-white when off, so it is invisible
    # until it has something to say.
    led_x, led_z = LED
    cut(shell, rounded("led_hole", (7, 6, 1.6), (led_x, y_wall, led_z), 0.8, axis=1), m["white"])
    led = rounded("Status light", (7, WALL, 1.6), (led_x, y_wall + WALL / 2 - 0.05, led_z), 0.8, axis=1,
                  mat=m["led"])
    return join([shell, led, port, tongue], "Shell")


def ethernet_cable(m):
    """The plug in its plugged-in position, cable trailing toward +X."""
    plug_front = ETH_FRONT - 8.5
    plug_len, plug_w, plug_h = 21.0, 11.6, 8.2
    plug_z = ETH_Z - 0.5
    plug_cx = plug_front + plug_len / 2
    parts = [rounded("Plug", (plug_len, plug_w, plug_h), (plug_cx, ETH_Y, plug_z), 0.6, axis=0, mat=m["plug"])]
    for i in range(8):
        parts.append(box(f"contact{i}", (3.5, 0.5, 0.4),
                         (plug_front + 2, ETH_Y + (i - 3.5) * 1.1, plug_z + plug_h / 2 - 0.1), m["gold"]))
    latch = box("Latch", (12, 3.6, 0.9), (plug_cx + 2, ETH_Y, plug_z - plug_h / 2 - 0.5), m["plug"])
    latch.rotation_euler = (0, math.radians(-6), 0)
    parts.append(latch)
    boot_start = plug_front + plug_len
    parts.append(rounded("Boot", (14, 13, 10), (boot_start + 7, ETH_Y, plug_z), 3.0, axis=0, mat=m["rubber"],
                         edge=1.0))
    parts.append(cylinder("Cable", 2.6, 400, (boot_start + 14 + 200, ETH_Y, plug_z), m["rubber"], axis=0))
    return join(parts, "Ethernet cable")


def power_cable(m):
    """A USB-C power cable in its plugged-in position, trailing toward -Y."""
    y_wall = -CASE_W / 2
    tip_len, mold_len = 6.5, 16.0
    mold_front = y_wall - 0.6
    parts = [
        # The metal tip sits inside the port once plugged in.
        rounded("USB-C tip", (8.3, tip_len, 2.5), (USBC_X, mold_front + tip_len / 2, USBC_Z), 1.2, axis=1,
                mat=m["metal"]),
        rounded("USB-C plug", (10.5, mold_len, 6.2), (USBC_X, mold_front - mold_len / 2, USBC_Z), 3.0, axis=1,
                mat=m["rubber"], edge=1.2),
        cylinder("Power cord", 1.9, 400, (USBC_X, mold_front - mold_len - 200, USBC_Z), m["rubber"], axis=1),
    ]
    return join(parts, "Power cable")


def to_metres(objects):
    to_m = Matrix.Scale(0.001, 4)
    for o in objects:
        o.matrix_world = to_m @ o.matrix_world
        activate(o)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


# ---------------------------------------------------------------- motion

def move(o, keys):
    """Keyframe o at (frame, offset in mm from its resting place)."""
    rest = o.location.copy()
    for frame, offset in keys:
        o.location = rest + Vector(offset) * 0.001
        o.keyframe_insert("location", frame=frame)
    o.location = rest


def animate(board, shell, cable, power, m):
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES

    move(board, [(1, (0, 0, 30)), (26, (0, 0, 0))])  # the Pi settles onto the base
    move(shell, [(34, (0, 0, 170)), (78, (0, 0, 0))])  # the shell closes over it
    move(cable, [(1, (120, 0, 0)), (92, (120, 0, 0)),  # the cable slides in...
                 (128, (4, 0, 0)), (138, (0, 0, 0))])  # ...and clicks home
    move(power, [(1, (0, -120, 0)), (102, (0, -120, 0)),  # then power slides in...
                 (130, (0, -4, 0)), (138, (0, 0, 0))])  # ...so the light can turn on

    light = m["led"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for frame, value in ((140, 0.0), (150, 4.0)):
        light.default_value = value
        light.keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------- staging

def aim(o, target):
    c = o.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"


def area_light(name, loc, size, power, target, color=(1, 1, 1), shadow=True):
    data = bpy.data.lights.new(name, "AREA")
    data.size = size
    data.energy = power
    data.color = color
    data.use_shadow = shadow
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.location = loc
    aim(o, target)
    return o


def stage(res, samples):
    scene = bpy.context.scene
    target = bpy.data.objects.new("Target", None)
    scene.collection.objects.link(target)
    target.location = (0.006, -0.004, 0.014)

    # Isometric camera from +X, -Y, above.
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 0.175
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = target.location + Vector((1, -1, 1))
    cam.rotation_euler = (math.radians(54.7356), 0, math.radians(45))
    scene.camera = cam

    # Product lighting that gives white faces distinct values: the top
    # brightest, the front (-Y, screen left) lit, the end (+X, screen right)
    # in shade. The overhead light also casts a tight contact shadow.
    area_light("Top", (-0.02, -0.04, 0.40), 0.30, 26, target)
    area_light("Front", (-0.12, -0.45, 0.18), 0.30, 16, target)
    area_light("Fill", (0.45, 0.10, 0.12), 0.30, 2.5, target, (0.92, 0.96, 1.0), shadow=False)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.85, 0.87, 0.9, 1)
    bg.inputs["Strength"].default_value = 0.08
    scene.world = world

    # Ground that keeps only the shadow, so frames are transparent.
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Shadow Catcher"
    ground.is_shadow_catcher = True

    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # Khronos PBR Neutral keeps the light green where AgX washes it to white.
    try:
        scene.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -1.8
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        # Specialized kernels compile in the background and have crashed
        # Blender 5.1 mid-render; the generic kernel is stable.
        prefs.kernel_optimization_level = "OFF"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception as e:  # CPU still works, only slower
        print("GPU unavailable, rendering on CPU:", e)


# ---------------------------------------------------------------- main

def options():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"stills": [], "animation": False, "res": 1080, "samples": 64}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--animation":
            opts["animation"] = True
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
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
    os.makedirs(OUT, exist_ok=True)

    m = materials()
    board, base, shell = raspberry_pi(m), case_base(m), case_shell(m)
    cable, power = ethernet_cable(m), power_cable(m)
    for o in (base, shell, cable, power):
        smooth(o)
    model = [board, base, shell, cable, power]
    to_metres(model)
    animate(board, shell, cable, power, m)
    stage(opts["res"], opts["samples"])

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "box.blend"))

    bpy.ops.object.select_all(action="DESELECT")
    for o in model:
        o.select_set(True)
    os.makedirs(os.path.dirname(WEB_GLB), exist_ok=True)
    gltf = dict(filepath=os.path.abspath(WEB_GLB), export_format="GLB", use_selection=True,
                export_apply=True, export_animations=True)
    try:
        bpy.ops.export_scene.gltf(**gltf, export_animation_mode="SCENE")
    except TypeError:
        bpy.ops.export_scene.gltf(**gltf)

    scene = bpy.context.scene
    for frame in opts["stills"]:
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(OUT, f"still-{frame:03d}.png")
        bpy.ops.render.render(write_still=True)
    if opts["animation"]:
        scene.render.filepath = os.path.join(OUT, "frames", "")
        scene.render.use_overwrite = False  # resume after an interruption
        bpy.ops.render.render(animation=True)
    # Where the status light sits in the frame, for the glow on the website.
    from bpy_extras.object_utils import world_to_camera_view
    led = world_to_camera_view(scene, scene.camera, Vector((LED[0], -CASE_W / 2, LED[1])) * 0.001)
    print(f"status light at left {led.x * 100:.1f}%, top {(1 - led.y) * 100:.1f}%")
    print("built", [o.name for o in model], "into", OUT)


main()
