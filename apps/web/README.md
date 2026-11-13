# The website

The site at [bigappleconnect.com](https://www.bigappleconnect.com), in
[Next.js](https://nextjs.org). It shows the box coming together as you scroll.
For the project as a whole, start with the [main README](../../README.md).

From the repository root:

```sh
pnpm install
pnpm dev      # run the website at http://localhost:3000
```

## The 3D model and frames

The box's 3D model is made by a script, not by hand. With
[Blender](https://www.blender.org) installed, rebuild it and compress it from
the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b -P design/box/build_box.py
npx @gltf-transform/cli meshopt apps/web/public/box/box.glb apps/web/public/box/box.glb
```

The website doesn't run the 3D scene for visitors. It plays image frames
rendered from it, so the story scrolls smoothly on any phone and connection.
After changing the model or the scene in `app/capture/`, render the frames
again (needs Google Chrome):

```sh
pnpm --filter web build:frames
```
