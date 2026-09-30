import { useEffect, useMemo, useRef, type RefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { cn } from "@/lib/utils";
import { fmt } from "./format";
import { arc, FACES, type Instant, type Track, type Vec3 } from "./orbit-profile";

/**
 * 3D scene of one orbit (docs/etapas/environment.md, «Órbita 3D»): a result profile or the preview
 * of a draft. Draws the orbit as the API computed it; the only arithmetic is placing it in the
 * scene (Earth radii, three.js axes).
 *
 * Units: 1 = Earth radius. Axes: the inertial frame has z to the north; three.js has y up, so
 * inertial (x, y, z) is drawn at (x, z, -y) — a rotation of -90° about x.
 */

export type CameraMode = "global" | "local";

const EARTH_RADIUS_M = 6_378_137;
const FRAME = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);

function world(v: Vec3 | number[] | undefined): THREE.Vector3 {
  const [x = 0, y = 0, z = 0] = v ?? [];
  return new THREE.Vector3(x / EARTH_RADIUS_M, z / EARTH_RADIUS_M, -y / EARTH_RADIUS_M);
}

function direction(v: Vec3 | number[]): THREE.Vector3 {
  const [x = 0, y = 0, z = 0] = v;
  return new THREE.Vector3(x, z, -y).normalize();
}

/** Colors of the Graphite tokens (styles.css), read once. */
function token(name: string, fallback: string): THREE.Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return new THREE.Color(value || fallback);
}

type Palette = Record<
  "bg" | "earth" | "grid" | "sun" | "shade" | "primary" | "cold" | "hot" | "text",
  THREE.Color
>;

function palette(): Palette {
  return {
    bg: token("--bg", "#0f1216"),
    earth: token("--surface-2", "#1d222a"),
    grid: token("--border-strong", "#38404b"),
    sun: token("--warn", "#d9a441"),
    shade: token("--idle", "#7c8594"),
    primary: token("--primary", "#5b8def"),
    cold: token("--cold", "#5aa0ee"),
    hot: token("--hot", "#ec7a48"),
    text: token("--subtle-foreground", "#667080"),
  };
}

/** Flux color: cold (0) to hot (max). */
function fluxColor(colors: Palette, value: number, max: number): THREE.Color {
  const f = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
  return colors.cold.clone().lerp(colors.hot, f);
}

// ---------------------------------------------------------------- pieces

function Graticule({ color }: { color: THREE.Color }) {
  const geometry = useMemo(() => {
    const points: number[] = [];
    const r = 1.001;
    const add = (a: THREE.Vector3, b: THREE.Vector3) => points.push(a.x, a.y, a.z, b.x, b.y, b.z);
    const at = (lat: number, lon: number) =>
      world([
        r * EARTH_RADIUS_M * Math.cos(lat) * Math.cos(lon),
        r * EARTH_RADIUS_M * Math.cos(lat) * Math.sin(lon),
        r * EARTH_RADIUS_M * Math.sin(lat),
      ]);
    const step = Math.PI / 36;
    for (let lat = -60; lat <= 60; lat += 30) {
      const phi = (lat * Math.PI) / 180;
      for (let lon = 0; lon < 2 * Math.PI - 1e-9; lon += step)
        add(at(phi, lon), at(phi, lon + step));
    }
    for (let lon = 0; lon < 360; lon += 30) {
      const lambda = (lon * Math.PI) / 180;
      for (let lat = -Math.PI / 2; lat < Math.PI / 2 - 1e-9; lat += step) {
        add(at(lat, lambda), at(lat + step, lambda));
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    return g;
  }, []);
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color={color} />
    </lineSegments>
  );
}

function Earth({ rotation, colors }: { rotation: number; colors: Palette }) {
  // Rotation about the inertial z axis (three.js y).
  return (
    <group rotation={[0, rotation, 0]}>
      <mesh>
        <sphereGeometry args={[1, 64, 32]} />
        <meshBasicMaterial color={colors.earth} />
      </mesh>
      <Graticule color={colors.grid} />
    </group>
  );
}

function OrbitLine({ track, colors }: { track: Track; colors: Palette }) {
  const geometry = useMemo(() => {
    const n = track.position.length;
    const positions: number[] = [];
    const vertexColors: number[] = [];
    // Each span between samples is drawn as a smooth arc, colored by the interpolated sunlight.
    for (let k = 0; k < n; k++) {
      const from = track.position[k] ?? [];
      const to = track.position[(k + 1) % n] ?? [];
      const litFrom = track.sunlit[k] ?? 1;
      const litTo = track.sunlit[(k + 1) % n] ?? 1;
      for (let m = 0; m < ARC_STEPS; m++) {
        const a = world(arc(from, to, m / ARC_STEPS));
        const b = world(arc(from, to, (m + 1) / ARC_STEPS));
        const lit = litFrom + ((litTo - litFrom) * (m + 0.5)) / ARC_STEPS;
        const color = lit > 0.5 ? colors.primary : colors.shade;
        positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
        vertexColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(vertexColors, 3));
    return g;
  }, [track, colors]);
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial vertexColors />
    </lineSegments>
  );
}

/** A vector drawn as a shaft and a head (solid geometry, so it is visible at any zoom). */
function Arrow({
  origin,
  dir,
  length,
  color,
}: {
  origin: THREE.Vector3;
  dir: THREE.Vector3;
  length: number;
  color: THREE.Color;
}) {
  const quaternion = new THREE.Quaternion().setFromUnitVectors(UP, dir);
  const head = length * ARROW_HEAD;
  const radius = length * ARROW_RADIUS;
  return (
    <group position={origin} quaternion={quaternion}>
      <mesh position={[0, (length - head) / 2, 0]}>
        <cylinderGeometry args={[radius, radius, length - head, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, length - head / 2, 0]}>
        <coneGeometry args={[radius * 3, head, 12]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

function ShadowCylinder({ sun, colors }: { sun: THREE.Vector3; colors: Palette }) {
  const length = 4;
  const quaternion = useMemo(
    () =>
      new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), sun.clone().negate()),
    [sun],
  );
  const position = useMemo(() => sun.clone().multiplyScalar(-length / 2), [sun]);
  return (
    <mesh quaternion={quaternion} position={position}>
      <cylinderGeometry args={[1, 1, length, 48, 1, true]} />
      <meshBasicMaterial
        color={colors.shade}
        transparent
        opacity={0.06}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

/** The envelope, not to scale, with its faces colored by the total incident flux (neutral without
 * fluxes); a plain marker without an attitude. */
function Spacecraft({
  instant,
  size,
  dims,
  maxFlux,
  colors,
  onOpen,
}: {
  instant: Instant;
  /** Largest side (the marker's diameter without an attitude). */
  size: number;
  /** Sides along the body axes x, y, z. */
  dims: Vec3;
  maxFlux: number;
  colors: Palette;
  onOpen?: () => void;
}) {
  const position = world(instant.position);
  const attitude = bodyToWorld(instant);
  if (!attitude) {
    return (
      <mesh position={position}>
        <sphereGeometry args={[size / 2, 16, 8]} />
        <meshBasicMaterial color={colors.primary} />
      </mesh>
    );
  }
  const { faces } = instant;
  // BoxGeometry material groups are +X, -X, +Y, -Y, +Z, -Z: the order of FACES.
  const materials = FACES.map((face) =>
    faces ? fluxColor(colors, faces[face].total, maxFlux) : colors.grid,
  );
  return (
    <group position={position} quaternion={attitude}>
      <mesh
        onDoubleClick={(event) => {
          event.stopPropagation();
          onOpen?.();
        }}
      >
        <boxGeometry args={dims} />
        {materials.map((color, k) => (
          <meshBasicMaterial key={FACES[k]} attach={`material-${k}`} color={color} />
        ))}
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(...dims)]} />
        <lineBasicMaterial color={colors.bg} />
      </lineSegments>
    </group>
  );
}

/** Rotation body → scene of an instant with an attitude. */
function bodyToWorld(instant: Instant): THREE.Quaternion | null {
  if (!instant.quaternion) return null;
  const [w, x, y, z] = instant.quaternion;
  return FRAME.clone().multiply(new THREE.Quaternion(x, y, z, w));
}

/** Each face: its outward normal in body axes and the body axis across it (0, 1, 2 = x, y, z). */
const FACE_GEOMETRY: Record<(typeof FACES)[number], { normal: THREE.Vector3; axis: 0 | 1 | 2 }> = {
  "+X": { normal: new THREE.Vector3(1, 0, 0), axis: 0 },
  "-X": { normal: new THREE.Vector3(-1, 0, 0), axis: 0 },
  "+Y": { normal: new THREE.Vector3(0, 1, 0), axis: 1 },
  "-Y": { normal: new THREE.Vector3(0, -1, 0), axis: 1 },
  "+Z": { normal: new THREE.Vector3(0, 0, 1), axis: 2 },
  "-Z": { normal: new THREE.Vector3(0, 0, -1), axis: 2 },
};

/** The envelope's sides in the scene: the mission's proportions with the largest side ``size``
 * (not to scale next to the Earth); a cube without them. */
function boxSides(size: number, envelope: Vec3 | null | undefined): Vec3 {
  if (!envelope) return [size, size, size];
  const largest = Math.max(...envelope);
  return envelope.map((side) => (size * side) / largest) as Vec3;
}

// ---------------------------------------------------------------- cameras

type View = { azimuth: number; elevation: number; distance: number };

/** Drag to rotate and wheel to zoom a camera that orbits a target (the Earth or the satellite).
 * Every change asks for a new frame (the canvas only draws on demand). */
function useOrbitControls(initial: View, limits: { min: number; max: number }) {
  const { gl, invalidate } = useThree();
  const view = useRef(initial);
  useEffect(() => {
    const element = gl.domElement;
    let dragging: { x: number; y: number } | null = null;
    const down = (e: PointerEvent) => {
      dragging = { x: e.clientX, y: e.clientY };
    };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      view.current.azimuth -= (e.clientX - dragging.x) * DRAG_RAD_PER_PX;
      view.current.elevation = Math.max(
        -MAX_ELEVATION,
        Math.min(
          MAX_ELEVATION,
          view.current.elevation + (e.clientY - dragging.y) * DRAG_RAD_PER_PX,
        ),
      );
      dragging = { x: e.clientX, y: e.clientY };
      invalidate();
    };
    const up = () => {
      dragging = null;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      view.current.distance = Math.max(
        limits.min,
        Math.min(limits.max, view.current.distance * (1 + e.deltaY * ZOOM_PER_WHEEL_STEP)),
      );
      invalidate();
    };
    element.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      element.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      element.removeEventListener("wheel", wheel);
    };
  }, [gl, invalidate, limits.min, limits.max]);
  return view;
}

/** Offset of a camera orbiting at ``view`` in a frame given by its up, forward and side axes. */
function orbitOffset(view: View, up: THREE.Vector3, forward: THREE.Vector3, side: THREE.Vector3) {
  const { azimuth, elevation, distance } = view;
  return new THREE.Vector3()
    .addScaledVector(side, Math.cos(elevation) * Math.cos(azimuth))
    .addScaledVector(forward, Math.cos(elevation) * Math.sin(azimuth))
    .addScaledVector(up, Math.sin(elevation))
    .multiplyScalar(distance);
}

/** Cameras move before anything reads them in the frame (the labels project with them). A
 * negative priority keeps the automatic render. */
const CAMERA_FIRST = -1;

const GLOBAL_LIMITS = { min: 1.3, max: 40 };

function GlobalCamera({ radius }: { radius: number }) {
  const { camera } = useThree();
  const view = useOrbitControls(
    { azimuth: 0.6, elevation: 0.35, distance: radius * 3.2 },
    GLOBAL_LIMITS,
  );
  useFrame(() => {
    camera.up.set(0, 1, 0);
    camera.position.copy(
      orbitOffset(
        view.current,
        new THREE.Vector3(0, 1, 0),
        new THREE.Vector3(1, 0, 0),
        new THREE.Vector3(0, 0, 1),
      ),
    );
    camera.lookAt(0, 0, 0);
  }, CAMERA_FIRST);
  return null;
}

const LOCAL_LIMITS = { min: 0.008, max: 0.3 };

/** Orbits the satellite in its local frame (local vertical up, velocity forward), so the horizon
 * stays level while dragging; it starts from the side of the orbit. */
function LocalCamera({ instant }: { instant: Instant }) {
  const { camera } = useThree();
  const view = useOrbitControls({ azimuth: -0.35, elevation: 0.3, distance: 0.05 }, LOCAL_LIMITS);
  useFrame(() => {
    const target = world(instant.position);
    const up = target.clone().normalize();
    const forward = direction(instant.velocity);
    const side = new THREE.Vector3().crossVectors(forward, up).normalize();
    camera.up.copy(up);
    camera.position.copy(target).add(orbitOffset(view.current, up, forward, side));
    camera.lookAt(target);
  }, CAMERA_FIRST);
  return null;
}

/** The canvas draws on demand: after every change of what it shows, one frame with everything
 * already updated (no frame with the camera at the new instant and the vectors at the old). */
function Redraw({ deps }: { deps: unknown[] }) {
  const { invalidate } = useThree();
  useEffect(() => {
    invalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- redraw when any of them changes
  }, deps);
  return null;
}

// ---------------------------------------------------------------- labels

type SceneLabel = {
  id: string;
  /** Scene position of the label's centre. */
  at: THREE.Vector3;
  text: string;
  detail?: string;
  tone: string;
  /** Only shown while this normal faces the camera (labels of the envelope's faces). */
  normal?: THREE.Vector3;
};

/** Moves the HTML labels over the canvas to the screen position of their scene points, every
 * frame the canvas draws. */
function LabelProjector({
  labels,
  elements,
}: {
  labels: SceneLabel[];
  elements: RefObject<Map<string, HTMLElement>>;
}) {
  const shown = useRef(new Set<string>());
  useFrame(({ camera, size }) => {
    // The cameras move in this same frame: project with their new matrices, not the last ones.
    camera.updateMatrixWorld();
    for (const label of labels) {
      const element = elements.current.get(label.id);
      if (!element) continue;
      const screen = label.at.clone().project(camera);
      let facing = true;
      if (label.normal) {
        // Hysteresis: a face at the edge of the threshold does not blink.
        const turned = label.normal.dot(camera.position.clone().sub(label.at).normalize());
        facing = turned > (shown.current.has(label.id) ? HIDE_FACE_COS : SHOW_FACE_COS);
      }
      const visible = screen.z < 1 && facing;
      if (visible) shown.current.add(label.id);
      else shown.current.delete(label.id);
      element.style.visibility = visible ? "visible" : "hidden";
      if (!visible) continue;
      const x = Math.round(((screen.x + 1) / 2) * size.width);
      const y = Math.round(((1 - screen.y) / 2) * size.height);
      element.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
    }
  });
  return null;
}

function labelsOf(
  instant: Instant,
  local: boolean,
  dims: Vec3,
  vector: number,
  radius: number,
): SceneLabel[] {
  const satellite = world(instant.position);
  const sun = direction(instant.sun);
  if (!local) {
    return [
      {
        id: "sun",
        at: sun.clone().multiplyScalar(radius * GLOBAL_SUN_LENGTH * LABEL_BEYOND_TIP),
        text: "Sol",
        tone: "text-warn",
      },
    ];
  }
  const tip = (dir: THREE.Vector3) =>
    satellite.clone().addScaledVector(dir, vector * LABEL_BEYOND_TIP);
  const labels: SceneLabel[] = [
    { id: "sun", at: tip(sun), text: "Sol", tone: "text-warn" },
    {
      id: "velocity",
      at: tip(direction(instant.velocity)),
      text: "Velocidad",
      tone: "text-primary",
    },
    {
      id: "nadir",
      at: tip(satellite.clone().normalize().negate()),
      text: "Nadir",
      tone: "text-muted-foreground",
    },
  ];
  const attitude = bodyToWorld(instant);
  if (!attitude) return labels;
  for (const face of FACES) {
    const { normal: bodyNormal, axis } = FACE_GEOMETRY[face];
    const normal = bodyNormal.clone().applyQuaternion(attitude);
    labels.push({
      id: `face:${face}`,
      at: satellite.clone().addScaledVector(normal, (dims[axis] / 2) * FACE_LABEL_OFFSET),
      text: face,
      detail: instant.faces ? fmt(instant.faces[face].total, 0) : undefined,
      tone: "text-foreground",
      normal,
    });
  }
  return labels;
}

// ---------------------------------------------------------------- scene

/** Arrows: head length and shaft radius as fractions of the length. */
const UP = new THREE.Vector3(0, 1, 0);
const ARROW_HEAD = 0.2;
const ARROW_RADIUS = 0.012;
/** Sun direction in the global view, in orbit radii from the Earth's centre. */
const GLOBAL_SUN_LENGTH = 1.6;
/** Labels sit a little past the tip of their arrow and off the centre of their face. */
const LABEL_BEYOND_TIP = 1.12;
const FACE_LABEL_OFFSET = 1.02;
/** Envelope and vectors of the local view, in Earth radii (not to scale: ~50 km and ~115 km). */
const LOCAL_BOX = 0.008;
const LOCAL_VECTOR = 0.018;
/** A face's label shows once the face turns this much to the camera (cos 70°) and hides below
 * the second threshold (cos 78°). */
const SHOW_FACE_COS = 0.34;
const HIDE_FACE_COS = 0.2;
/** Straight pieces drawn per span between two samples of the orbit line. */
const ARC_STEPS = 16;
const DRAG_RAD_PER_PX = 0.008;
const MAX_ELEVATION = 1.4;
const ZOOM_PER_WHEEL_STEP = 0.001;

export function OrbitScene({
  track,
  instant,
  mode,
  maxFlux = 0,
  envelope,
  onOpenLocal,
}: {
  track: Track;
  instant: Instant;
  mode: CameraMode;
  /** Top of the flux color scale, W/m² (a profile with fluxes). */
  maxFlux?: number;
  /** Sizes of the mission's envelope (x, y, z, m): the satellite keeps its proportions. */
  envelope?: Vec3 | null;
  onOpenLocal: () => void;
}) {
  const colors = useMemo(() => palette(), []);
  const radius = world(track.position[0]).length();
  const sun = direction(instant.sun);
  const satellite = world(instant.position);
  const local = mode === "local";
  const size = local ? LOCAL_BOX : 0.05;
  const vector = local ? LOCAL_VECTOR : 0.25;
  const dims = boxSides(size, envelope);
  const labels = labelsOf(instant, local, dims, vector, radius);
  const elements = useRef(new Map<string, HTMLElement>());

  return (
    <div className="relative h-full w-full overflow-hidden">
      <Canvas
        frameloop="demand"
        camera={{ fov: 45, near: 0.0005, far: 200, position: [0, 1, 4] }}
        gl={{ logarithmicDepthBuffer: true }}
        className="h-full w-full"
        dpr={[1, 2]}
      >
        <color attach="background" args={[colors.bg]} />
        <Redraw deps={[instant, mode, track]} />
        {local ? <LocalCamera instant={instant} /> : <GlobalCamera radius={radius} />}
        <Earth rotation={instant.earthRotation} colors={colors} />
        <OrbitLine track={track} colors={colors} />
        {!local && <ShadowCylinder sun={sun} colors={colors} />}
        <Arrow
          origin={local ? satellite : new THREE.Vector3()}
          dir={sun}
          length={local ? vector : radius * GLOBAL_SUN_LENGTH}
          color={colors.sun}
        />
        <Spacecraft
          instant={instant}
          size={size}
          dims={dims}
          maxFlux={maxFlux}
          colors={colors}
          onOpen={onOpenLocal}
        />
        {local && (
          <>
            <Arrow
              origin={satellite}
              dir={satellite.clone().normalize().negate()}
              length={vector}
              color={colors.shade}
            />
            <Arrow
              origin={satellite}
              dir={direction(instant.velocity)}
              length={vector}
              color={colors.primary}
            />
          </>
        )}
        <LabelProjector labels={labels} elements={elements} />
      </Canvas>
      {labels.map((label) => (
        <span
          key={label.id}
          ref={(element) => {
            if (element) elements.current.set(label.id, element);
            else elements.current.delete(label.id);
          }}
          className={cn(
            "pointer-events-none invisible absolute top-0 left-0 flex flex-col items-center font-mono text-2xs leading-tight whitespace-nowrap",
            label.tone,
          )}
        >
          <span>{label.text}</span>
          {label.detail && <span className="tabular-nums">{label.detail}</span>}
        </span>
      ))}
    </div>
  );
}
