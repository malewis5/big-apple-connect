"""Render the small isometric icons for the website, in the same soft,
matte "miniature model" style as the box.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender -b -P design/box/build_icons.py

Writes design/box/out/icon-*.png (transparent). Convert them for the web with:

    for f in record compare home; do
      cwebp -quiet -q 85 -alpha_q 95 design/box/out/icon-$f.png -o apps/web/public/icons/$f.webp
    done
"""

import math
import os

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SIZE = 600


def srgb(hex_color):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def material(name, hex_color, rough=0.6, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*srgb(hex_color), 1.0)
    p.inputs["Roughness"].default_value = rough
    if emit:
        p.inputs["Emission Color"].default_value = (*srgb(emit), 1.0)
        p.inputs["Emission Strength"].default_value = strength
    return m


# One palette for every icon: soft white, mint and emerald, warm gray, and
# a touch of amber.
PALETTE = {}


def palette():
    PALETTE.update({
        "white": material("White", "#F7F6F3"),
        "mint": material("Mint", "#BFEBD3"),
        "green": material("Green", "#34C17B"),
        "deep": material("Deep Green", "#1F9D60"),
        "warm": material("Warm Gray", "#DCD7CF"),
        "charcoal": material("Charcoal", "#41454C", rough=0.5),
        "amber": material("Amber", "#F6B656", emit="#F6B656", strength=0.4),
        "light": material("Light", "#3DDC84", emit="#3DDC84", strength=1.5),
    })


def activate(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def finish(o, mat, bevel):
    if bevel:
        mod = o.modifiers.new("soft", "BEVEL")
        mod.width = bevel
        mod.segments = 6
        mod.limit_method = "ANGLE"
        activate(o)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(PALETTE[mat])
    activate(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def box(size, loc, mat, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    return finish(o, mat, bevel)


def cylinder(radius, depth, loc, mat, bevel=0.0, rot=(0, 0, 0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot, vertices=vertices)
    o = bpy.context.active_object
    bpy.ops.object.transform_apply(rotation=True)
    return finish(o, mat, bevel)


def prism(width, depth, height, loc, mat, bevel=0.0):
    """A roof: a triangular prism running along Y."""
    w, d, h = width / 2, depth / 2, height
    verts = [(-w, -d, 0), (w, -d, 0), (0, -d, h), (-w, d, 0), (w, d, 0), (0, d, h)]
    faces = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    mesh = bpy.data.meshes.new("roof")
    mesh.from_pydata(verts, [], faces)
    o = bpy.data.objects.new("roof", mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc
    return finish(o, mat, bevel)


# ---------------------------------------------------------------- icons

def icon_record():
    """It keeps a record: a little bar chart, with a live green light."""
    box((10, 10, 1.2), (0, 0, 0.6), "white", bevel=0.5)
    for i, h in enumerate((2.6, 4.2, 3.2, 5.8, 4.8)):
        x = -3.4 + i * 1.7
        box((1.1, 1.1, h), (x, 0.6, 1.2 + h / 2), "green" if i == 3 else "mint", bevel=0.45)
    cylinder(0.45, 0.3, (3.2, -3.4, 1.35), "light", bevel=0.1)
    return 19.0


def icon_compare():
    """Results you can compare: a balanced scale, standing on a tile like
    the other icons so its shadows land somewhere."""
    box((11, 11, 1.0), (0, 0, 0.5), "white", bevel=0.5)
    cylinder(2.4, 0.7, (0, 0, 1.35), "warm", bevel=0.3)
    cylinder(0.35, 6.4, (0, 0, 4.6), "warm", bevel=0.1)
    box((8.6, 0.7, 0.6), (0, 0, 7.8), "deep", bevel=0.25)
    cylinder(0.55, 0.5, (0, 0, 8.3), "green", bevel=0.2)
    for x in (-4.0, 4.0):
        cylinder(0.08, 2.4, (x, 0, 6.5), "warm")
        cylinder(1.8, 0.45, (x, 0, 5.1), "mint" if x < 0 else "green", bevel=0.2)
    return 20.0


def icon_home():
    """Tips for your home: a small house on a lawn, with a router."""
    box((11, 11, 1.0), (0, 0, 0.5), "mint", bevel=0.5)
    box((5.2, 4.6, 3.6), (-1.0, 1.0, 2.8), "white", bevel=0.25)
    prism(6.0, 5.2, 2.6, (-1.0, 1.0, 4.6), "green", bevel=0.2)
    box((1.2, 0.2, 2.0), (-0.2, -1.3, 2.0), "amber", bevel=0.1)  # door, lit
    box((1.1, 0.2, 1.0), (-2.4, -1.3, 3.0), "amber", bevel=0.1)  # window, lit
    # The router, out front.
    box((2.6, 1.6, 0.8), (3.1, -2.6, 1.4), "white", bevel=0.3)
    cylinder(0.18, 0.18, (3.1, -3.42, 1.45), "light", rot=(math.pi / 2, 0, 0))
    for x in (2.3, 3.9):
        cylinder(0.12, 1.8, (x, -2.2, 2.6), "white", bevel=0.05)
    return 20.0


# ---------------------------------------------------------------- staging

def aim(o, target):
    c = o.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"


def stage(scale, target_z):
    scene = bpy.context.scene
    target = bpy.data.objects.new("Target", None)
    scene.collection.objects.link(target)
    target.location = (0, 0, target_z)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = scale
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector((0, 0, target_z)) + Vector((1, -1, 1)) * 40
    cam.rotation_euler = (math.radians(54.7356), 0, math.radians(45))
    scene.camera = cam

    # Soft, neutral light from the top left of the frame (the -X, -Y side).
    for name, loc, size, power in (("Key", (-14, -16, 46), 60, 9000), ("Fill", (30, -5, 15), 30, 2000)):
        data = bpy.data.lights.new(name, "AREA")
        data.size = size
        data.energy = power
        if name == "Fill":
            data.use_shadow = False
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        aim(o, target)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    bpy.context.active_object.is_shadow_catcher = True

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Khronos PBR Neutral"
    scene.view_settings.exposure = 1.3
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.kernel_optimization_level = "OFF"  # specialized kernels have crashed Blender 5.1
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception as e:
        print("GPU unavailable, rendering on CPU:", e)


def clear_haze(path, floor=0.06):
    """The shadow catcher keeps a faint shade across the whole frame, which
    shows as a gray square on a white page. Drop it to fully transparent,
    keep the real shadows, and fade them out before the image's edge."""
    image = bpy.data.images.load(path)
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgba = pixels.reshape(-1, 4)
    rgba[:, 3] = np.clip((rgba[:, 3] - floor) / (1 - floor), 0, 1)
    # Fade the outer edge too, so a long soft shadow never ends in a line.
    size = image.size[0]
    ramp = np.abs(np.linspace(-1, 1, size))
    edge = np.clip((1 - np.maximum(ramp[None, :], ramp[:, None])) / 0.12, 0, 1)
    rgba[:, 3] *= edge.ravel()
    image.pixels.foreach_set(rgba.ravel())
    image.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, build, target_z in (("record", icon_record, 2.4), ("compare", icon_compare, 4.4),
                                  ("home", icon_home, 2.6)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        palette()
        scale = build()
        stage(scale, target_z)
        path = os.path.join(OUT, f"icon-{name}.png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        clear_haze(path)
    print("icons written to", OUT)


main()
