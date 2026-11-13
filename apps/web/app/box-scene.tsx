"use client";

import { ContactShadows, Environment, Lightformer, PerformanceMonitor, SoftShadows, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { type RefObject, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  AnimationMixer,
  Color,
  type Material,
  type Mesh,
  type MeshPhysicalMaterial,
  type MeshStandardMaterial,
  MeshDepthMaterial,
  NeutralToneMapping,
  type Object3D,
  Vector3,
} from "three";

// Built by design/box/build_box.py. Its motion runs over 180 frames at 30 fps.
const MODEL = "/box/box.glb";
const FPS = 30;
const LIGHT_ON = [140, 150]; // frames over which the status light turns on
const SHELL_FADE = [33, 54]; // frames over which the shell and its shadow ease in as it drops

// Blender's Z-up millimetres become three.js Y-up metres: (x, y, z) -> (x, z, -y).
const TARGET = new Vector3(0.006, 0.014, 0.004);
const VIEW_HEIGHT = 0.175; // metres of scene visible across the shorter side
const LIGHT_OFF = new Color("#fbfaf8"); // unlit: case-white, invisible until it turns on
const LIGHT_GREEN = new Color("#22c55e");

type Props = {
  frame: RefObject<number>; // fractional animation frame, 0 to 179
  onInvalidate: (redraw: () => void) => void;
  onReady: () => void;
};

export default function BoxScene({ frame, onInvalidate, onReady }: Props) {
  // Phones get a lighter scene: fewer pixels, a smaller shadow map and no
  // contact-hardening shadows. If frames still drop, the resolution falls.
  const [phone] = useState(() => window.matchMedia("(pointer: coarse)").matches || navigator.maxTouchPoints > 0);
  const [dpr, setDpr] = useState<number | [number, number]>([1, phone ? 1.5 : 2]);
  return (
    <Canvas
      orthographic
      shadows
      frameloop="demand"
      dpr={dpr}
      gl={{ antialias: true, alpha: true }}
      camera={{ position: TARGET.clone().add(new Vector3(1, 1, 1)), near: 0.01, far: 10 }}
      onCreated={({ gl }) => {
        // Neutral keeps white white; AgX would gray it.
        gl.toneMapping = NeutralToneMapping;
        gl.toneMappingExposure = 1.05;
      }}
    >
      <PerformanceMonitor onDecline={() => setDpr(1)} />
      <Isometric />
      <Redraw onInvalidate={onInvalidate} />
      <Lighting phone={phone} />
      <Box frame={frame} onReady={onReady} />
      {/* Nudged toward the viewer so the shadow shows past the base. */}
      <ContactShadows
        position={[0.004, 0.0002, 0.006]}
        scale={0.3}
        resolution={phone ? 256 : 512}
        blur={3.2}
        far={0.05}
        opacity={0.6}
        color="#101622"
      />
    </Canvas>
  );
}

// Keep the isometric view framed to the canvas.
function Isometric() {
  const get = useThree((state) => state.get);
  const size = useThree((state) => state.size);
  useLayoutEffect(() => {
    const camera = get().camera;
    camera.zoom = Math.min(size.width, size.height) / VIEW_HEIGHT;
    camera.lookAt(TARGET);
    camera.updateProjectionMatrix();
  }, [get, size]);
  return null;
}

// Hand the parent a way to request a redraw when the scroll position changes.
function Redraw({ onInvalidate }: Pick<Props, "onInvalidate">) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => onInvalidate(invalidate), [invalidate, onInvalidate]);
  return null;
}

// Studio lighting chosen so white faces read as a solid on a white page: the
// top brightest, the front face (screen left) lit, the end (screen right) in
// shade. The environment is built from local light panels, so nothing is
// downloaded.
function Lighting({ phone }: { phone: boolean }) {
  return (
    <>
      <ambientLight intensity={0.15} />
      {/* Soft shadows let parts shade the board and the case shade the ground.
          The contact-hardening filter costs too much on phones. */}
      {!phone && <SoftShadows size={26} samples={16} focus={0.4} />}
      {/* Soft neutral light from the top left of the frame, with a sky-to-ground
          fill so shaded sides stay gentle. */}
      <hemisphereLight args={["#ffffff", "#e9e4dc", 0.55]} />
      <directionalLight
        position={[-0.2, 0.6, 0.22]}
        intensity={1.9}
        castShadow
        shadow-mapSize={phone ? [1024, 1024] : [4096, 4096]}
        shadow-camera-left={-0.11}
        shadow-camera-right={0.11}
        shadow-camera-top={0.11}
        shadow-camera-bottom={-0.11}
        shadow-camera-near={0.05}
        shadow-camera-far={1.2}
        shadow-normalBias={0.0004}
      />
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={[0.6, 0.6]} />
        <shadowMaterial opacity={0.12} />
      </mesh>
      <Environment resolution={256} frames={1}>
        {/* A light gray surround, so metal parts reflect gray, not black. */}
        <color attach="background" args={["#cfd4dc"]} />
        <Lightformer form="rect" intensity={2.2} position={[0, 1, 0]} scale={[1.5, 1.5, 1]} target={[0, 0, 0]} />
        <Lightformer form="rect" intensity={1.1} position={[-0.2, 0.3, 1]} scale={[1.2, 0.5, 1]} target={[0, 0, 0]} />
        <Lightformer form="rect" intensity={0.05} position={[1, 0.2, 0]} scale={[0.6, 0.4, 1]} target={[0, 0, 0]} />
        <Lightformer form="rect" intensity={0.6} position={[-1, 0.4, -0.6]} scale={[0.8, 0.4, 1]} target={[0, 0, 0]} />
        {/* Thin strips overhead: crisp highlights that make metal read as metal. */}
        <Lightformer form="rect" intensity={2} position={[0.3, 0.9, 0.3]} scale={[1.6, 0.05, 1]} target={[0, 0, 0]} />
        <Lightformer form="rect" intensity={1.5} position={[-0.3, 0.9, 0.5]} scale={[0.05, 1.6, 1]} target={[0, 0, 0]} />
        <Lightformer form="rect" intensity={1.2} position={[0.6, 0.5, 0.8]} scale={[1.2, 0.04, 1]} target={[0, 0, 0]} />
      </Environment>
    </>
  );
}

function materialsOf(mesh: Mesh): Material[] {
  return Array.isArray(mesh.material) ? mesh.material : [mesh.material];
}

function clamp(value: number) {
  return Math.min(1, Math.max(0, value));
}

// Fade three.js materials; transparency is switched off once fully opaque
// so the finished case sorts and renders like any solid.
function fadeMaterials(materials: Material[], opacity: number) {
  for (const material of materials) {
    material.opacity = opacity;
    material.transparent = opacity < 1 && !(material as MeshDepthMaterial).isMeshDepthMaterial;
  }
}

function smoothstep(value: number) {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
}

function Box({ frame, onReady }: Pick<Props, "frame" | "onReady">) {
  const { scene, animations } = useGLTF(MODEL, false);
  const rig = useRef<{
    mixer: AnimationMixer;
    light: MeshStandardMaterial | null;
    shell: Object3D | null;
    shellMaterials: Material[];
    shellShadow: MeshDepthMaterial;
    end: number;
  } | null>(null);
  const shown = useRef<number | null>(null); // the frame on screen, easing toward the scroll position

  // Set up the motion and the materials once the model has loaded. three.js
  // objects are mutable by design, so they live in a ref, not in render.
  useLayoutEffect(() => {
    const mixer = new AnimationMixer(scene);
    animations.forEach((clip) => mixer.clipAction(clip).play());
    const end = Math.min(...animations.map((clip) => clip.duration));
    // The shell fades in as it drops. It gets its own materials so the fade
    // doesn't touch the rest of the model, and a dithered depth material so
    // its shadow fades with it; shadow maps otherwise ignore opacity.
    const shell = scene.getObjectByName("Shell") ?? null;
    const shellShadow = new MeshDepthMaterial({ alphaHash: true });
    const shellMaterials: Material[] = [];
    shell?.traverse((object) => {
      const mesh = object as Mesh;
      if (!mesh.isMesh) return;
      const own = materialsOf(mesh).map((material) => material.clone());
      mesh.material = Array.isArray(mesh.material) ? own : own[0];
      mesh.customDepthMaterial = shellShadow;
      shellMaterials.push(...own);
    });

    let light: MeshStandardMaterial | null = null;
    scene.traverse((object) => {
      if (!(object as Mesh).isMesh) return;
      object.castShadow = true;
      object.receiveShadow = true;
      for (const material of materialsOf(object as Mesh)) {
        if (material.name === "Status Light") {
          // A clean, solid power indicator: no halo, since quality plastic
          // doesn't let light bleed around it.
          light = material as MeshStandardMaterial;
          light.color.copy(LIGHT_OFF);
          light.emissive.copy(LIGHT_GREEN);
          light.emissiveIntensity = 0;
        } else if (material.name === "Case White" || material.name === "Cable White") {
          // Soft, matte white plastic, like a small collectible model.
          const white = material as MeshPhysicalMaterial;
          white.color.set("#fbfaf8");
          white.roughness = 0.58;
          white.clearcoat = 0.12;
          white.clearcoatRoughness = 0.4;
        } else if (material.name === "Board Green") {
          const board = material as MeshPhysicalMaterial;
          board.color.set("#2c9a60");
          board.roughness = 0.6;
          board.clearcoat = 0.1;
        } else if (material.name === "Metal") {
          // Satin, not mirror: soft highlights without harsh contrast.
          const metal = material as MeshStandardMaterial;
          metal.color.set("#d6dade");
          metal.roughness = 0.42;
        } else if (material.name === "Foot Gray") {
          // A darker, thinner-looking foot, so the case floats crisply above it.
          (material as MeshStandardMaterial).color.set("#767b83");
        } else if (material.name === "Plug Clear") {
          // Real transmission costs an extra render pass; a frosted look is enough.
          const plug = material as MeshPhysicalMaterial;
          plug.transmission = 0;
          plug.transparent = true;
          plug.opacity = 0.9;
        }
      }
    });
    rig.current = { mixer, light, shell, shellMaterials, shellShadow, end };
    onReady();
    return () => {
      mixer.stopAllAction();
      shellShadow.dispose();
      shellMaterials.forEach((material) => material.dispose());
      rig.current = null;
    };
  }, [scene, animations, onReady]);

  useFrame((state, delta) => {
    if (!rig.current) return;
    const { mixer, light, shell, shellMaterials, shellShadow, end } = rig.current;
    // Ease toward the scroll position instead of jumping to it. Phones send
    // scroll updates unevenly, and jumps between them read as lag. The ease
    // is time-based, so it feels the same at any frame rate.
    const target = frame.current;
    const previous = shown.current ?? target;
    let f = previous + (target - previous) * (1 - Math.exp(-delta * 14));
    if (Math.abs(target - f) < 0.01) f = target;
    else state.invalidate(); // keep drawing until it catches up
    shown.current = f;
    // Clips loop, so a time exactly at the end would jump back to the start.
    mixer.setTime(Math.min((f + 1) / FPS, end - 0.001));
    // Ease the shell and its shadow in together as it starts to drop.
    const fade = smoothstep((f - SHELL_FADE[0]) / (SHELL_FADE[1] - SHELL_FADE[0]));
    if (shell) shell.visible = fade > 0;
    fadeMaterials([...shellMaterials, shellShadow], fade);

    const on = clamp((f - LIGHT_ON[0]) / (LIGHT_ON[1] - LIGHT_ON[0]));
    if (light) {
      light.color.copy(LIGHT_OFF).lerp(LIGHT_GREEN, on);
      light.emissiveIntensity = on * 0.9;
    }
  });

  return (
<primitive object={scene} />
  );
}

useGLTF.preload(MODEL, false);
