"""Render the demo video's captions and end card as transparent PNGs.

Run from the repository root:

    BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
    $BLENDER -b -P design/demo/build_captions.py -- --aspect wide --res 720

Options after `--`: --aspect wide|tall (default wide), --res N (short side,
default 1080; match the frames). Writes out/captions-<aspect>-<res>/NN.png and
captions.json, which make_video.py reads for timing.

The words here are the demo's script. Keep them calm and plain, because the
box only checks and measures the connection.
"""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT_DIR = os.path.expanduser("~/Library/Fonts")

# (start, end) in seconds, and the line. Beats match build_demo.py at 30 fps.
# The words follow the website (apps/web/app/site.ts): whole, flowing
# sentences rather than clipped fragments, and no promise the site doesn't
# make. The box is still being built, and advice for your home comes later.
# Nothing here may suggest watching, tracking or monitoring a person: the box
# measures the connection, and its results stay on the box.
CAPTIONS = [
    (0.5, 4.7, "We're building a small box that measures your home internet."),
    (5.4, 12.6, "Setting it up only means plugging it into your router."),
    (13.3, 20.8, "It tests your connection every five minutes, day and night."),
    (21.2, 28.8, "Each result stays on the box, so you can show what you really get."),
    (29.3, 32.9, "It measures only your connection, never what you do online."),
    (33.4, 41.0, "Later, we plan to add advice, such as a clearer Wi-Fi channel."),
]
END_CARD = (41.4, 45.0, "Is your internet as good as promised?", "bigappleconnect.com")


def srgb(hex_color):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def flat(name, hex_color, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*srgb(hex_color), 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = alpha
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def text(body, size, weight, mat, y=0.0, z=0.01):
    data = bpy.data.curves.new("t", "FONT")
    data.body = body
    data.font = bpy.data.fonts.load(os.path.join(FONT_DIR, f"Geist-{weight}.otf"), check_existing=True)
    data.size = size
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    o = bpy.data.objects.new("t", data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    o.location = (0, y, z)
    bpy.context.view_layer.update()
    return o


def wrap(words, size, weight, max_w, mat):
    """Break words into lines no wider than max_w, measured in the font."""
    lines, line = [], ""
    probe = text("", size, weight, mat)
    for w in words:
        trial = f"{line} {w}".strip()
        probe.data.body = trial
        bpy.context.view_layer.update()
        if probe.dimensions.x > max_w and line:
            lines.append(line)
            line = w
        else:
            line = trial
    lines.append(line)
    bpy.data.objects.remove(probe)
    return lines


def pill(w, h, r, mat, y=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, y, 0))
    o = bpy.context.active_object
    o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(scale=True)
    bev = o.modifiers.new("round", "BEVEL")
    bev.affect = "VERTICES"
    bev.width = r
    bev.segments = 12
    o.data.materials.append(mat)
    return o


def clear():
    for o in list(bpy.data.objects):
        if o.type != "CAMERA":
            bpy.data.objects.remove(o)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    aspect, res = "wide", 1080
    for i, a in enumerate(argv):
        if a == "--aspect":
            aspect = argv[i + 1]
        elif a == "--res":
            res = int(argv[i + 1])
    long_side = round(res * 16 / 9 / 2) * 2
    W, H = (long_side, res) if aspect == "wide" else (res, long_side)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    # One unit is one pixel at 1080p, so sizes read like CSS.
    u = res / 1080
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(W, H) / u
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 10)
    scene.camera = cam
    half_h = H / u / 2

    ink = flat("Ink", "#171717")
    soft_ink = flat("Soft", "#52525B")
    glass = flat("Pill", "#FFFFFF", 0.93)
    green = flat("Green", "#059669")
    dot = flat("Dot", "#10B981")
    cream = flat("Cream", "#FBF8F3")

    out = os.path.join(OUT, f"captions-{aspect}-{res}")
    os.makedirs(out, exist_ok=True)
    manifest = []

    size = 46 if aspect == "wide" else 50
    max_w = 1300 if aspect == "wide" else 860
    line_h = size * 1.32
    base_y = -half_h + (130 if aspect == "wide" else 420)
    for n, (start, end, line) in enumerate(CAPTIONS):
        clear()
        lines = wrap(line.split(), size, "Medium", max_w, ink)
        widths = []
        for i, l in enumerate(lines):
            y = base_y + (len(lines) - 1 - i) * line_h - (len(lines) - 1) * line_h / 2
            t = text(l, size, "Medium", ink, y)
            widths.append(t.dimensions.x)
        pad_x, pad_y = 44, 30
        pw = max(widths) + 2 * pad_x
        ph = len(lines) * line_h + 2 * pad_y - (line_h - size)
        pill(pw, ph, min(ph / 2, 44) if len(lines) > 1 else ph / 2, glass, base_y)
        path = os.path.join(out, f"{n:02d}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({"file": path, "start": start, "end": end, "text": line})

    # End card: the question, and where to learn more.
    clear()
    start, end, tagline, url = END_CARD
    pill(W / u + 4, H / u + 4, 0, cream).location.z = -0.01
    t_size = 92 if aspect == "wide" else 84
    t_lines = wrap(tagline.split(), t_size, "SemiBold", 1500 if aspect == "wide" else 880, ink)
    gap = t_size * 1.15
    top = (len(t_lines) - 1) * gap / 2 + 30
    brand = text("Big Apple Connect Box", 34, "SemiBold", soft_ink, top + 140)
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=11, fill_type="NGON",
                                      location=(-brand.dimensions.x / 2 - 28, top + 140, 0.01))
    bpy.context.active_object.data.materials.append(dot)
    for i, l in enumerate(t_lines):
        text(l, t_size, "SemiBold", ink, top - i * gap)
    text(url, 46, "Medium", green, top - (len(t_lines) - 1) * gap - 140)
    path = os.path.join(out, "end.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({"file": path, "start": start, "end": end, "text": f"{tagline} {url}", "card": True})

    with open(os.path.join(out, "captions.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("captions written to", out)


main()
