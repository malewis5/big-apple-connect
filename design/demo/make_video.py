"""Put the rendered frames and captions together into videos with ffmpeg.

Run from the repository root after build_demo.py --animation and
build_captions.py:

    python3 design/demo/make_video.py --aspect wide --draft   # quick review copy
    python3 design/demo/make_video.py --aspect wide           # the website set

Drafts render every other frame and play at 15 fps; they become
out/big-apple-connect-box-demo-<aspect>-draft.mp4.

Finals play at 30 fps and become a set for the website in out/web/:

    demo-<aspect>.mp4          H.264 with captions: plays everywhere
    demo-<aspect>.webm         AV1 with captions: much smaller, for browsers that support it
    demo-<aspect>-clean.mp4    H.264 without captions, for captions set as page text
    demo-<aspect>-clean.webm   AV1 without captions
    demo-<aspect>.vtt          the captions as WebVTT, for the clean versions
    demo-<aspect>-poster.jpg   a still to show before the video loads

None has an audio track, so browsers will autoplay them muted and loop them.
"""

import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FADE = 0.6  # captions drift in and out
CARD_FADE = 1.2  # the end card arrives slowly
POSTER_FRAME = 560  # a sunny midday, the chart filling in


def frames_input(frames, fps):
    return ["-framerate", str(fps), "-pattern_type", "glob", "-i", os.path.join(frames, "*.png")]


def caption_graph(captions, fps):
    """Inputs and filter graph laying each caption over the video in turn."""
    inputs, graph, last = [], [], "[0:v]"
    for i, c in enumerate(captions, start=1):
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{c['end'] + 0.1:.2f}", "-i", c["file"]]
        fades = f"fade=t=in:st={c['start']}:d={CARD_FADE if c.get('card') else FADE}:alpha=1"
        if not c.get("card"):
            fades += f",fade=t=out:st={c['end'] - FADE:.2f}:d={FADE}:alpha=1"
        graph.append(f"[{i}:v]format=rgba,{fades}[c{i}]")
        graph.append(f"{last}[c{i}]overlay=0:0:enable='between(t,{c['start']},{c['end'] + 0.1:.2f})'[v{i}]")
        last = f"[v{i}]"
    return inputs, graph, last


H264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart"]
# Keyframes every two seconds, so the page can seek and scrub smoothly.
WEB_H264 = ["-c:v", "libx264", "-preset", "veryslow", "-crf", "19", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-g", "60", "-movflags", "+faststart", "-an"]
WEB_AV1 = ["-c:v", "libsvtav1", "-preset", "4", "-crf", "28", "-pix_fmt", "yuv420p10le", "-g", "60",
           "-svtav1-params", "tune=0", "-an"]


def run(cmd):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + cmd, check=True)


def vtt_time(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", choices=("wide", "tall"), default="wide")
    ap.add_argument("--draft", action="store_true")
    args = ap.parse_args()

    quality = "draft" if args.draft else "final"
    res = 720 if args.draft else 1080
    fps = 15 if args.draft else 30
    frames = os.path.join(OUT, f"{args.aspect}-{quality}", "frames")
    with open(os.path.join(OUT, f"captions-{args.aspect}-{res}", "captions.json")) as f:
        captions = json.load(f)
    cap_inputs, graph, last = caption_graph(captions, fps)

    if args.draft:
        out = os.path.join(OUT, f"big-apple-connect-box-demo-{args.aspect}-draft.mp4")
        run(frames_input(frames, fps) + cap_inputs + ["-filter_complex", ";".join(graph), "-map", last]
            + H264 + ["-r", str(fps), out])
        print(out)
        return

    web = os.path.join(OUT, "web")
    os.makedirs(web, exist_ok=True)
    name = os.path.join(web, f"demo-{args.aspect}")
    # A lossless master with captions, then each web encode from it.
    master = os.path.join(OUT, f"master-{args.aspect}.mkv")
    run(frames_input(frames, fps) + cap_inputs + ["-filter_complex", ";".join(graph), "-map", last,
                                                  "-c:v", "ffv1", "-pix_fmt", "yuv444p16le", "-r", str(fps), master])
    clean = os.path.join(OUT, f"master-{args.aspect}-clean.mkv")
    run(frames_input(frames, fps) + ["-c:v", "ffv1", "-pix_fmt", "yuv444p16le", "-r", str(fps), clean])
    for src, suffix in ((master, ""), (clean, "-clean")):
        run(["-i", src] + WEB_H264 + [f"{name}{suffix}.mp4"])
        run(["-i", src] + WEB_AV1 + [f"{name}{suffix}.webm"])
        print(f"{name}{suffix}.mp4", f"{name}{suffix}.webm")
    run(["-i", os.path.join(frames, f"{POSTER_FRAME:04d}.png"), "-frames:v", "1",
         "-q:v", "2", f"{name}-poster.jpg"])
    with open(f"{name}.vtt", "w") as f:
        f.write("WEBVTT\n\n")
        for c in captions:
            if c.get("card"):
                continue
            f.write(f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}\n{c['text']}\n\n")
    print(f"{name}-poster.jpg", f"{name}.vtt")


if __name__ == "__main__":
    main()
