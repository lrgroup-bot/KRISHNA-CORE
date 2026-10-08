import { Canvas, useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';

type CoreMotionState = 'idle' | 'thinking' | 'working' | 'speaking' | 'healing' | 'blocked';

function OmCore({ state }: { state: CoreMotionState }) {
  const group = useRef<THREE.Group>(null);
  const ringA = useRef<THREE.Mesh>(null);
  const ringB = useRef<THREE.Mesh>(null);
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 768;
    canvas.height = 768;
    const context = canvas.getContext('2d');
    if (!context) return null;
    const glow = context.createRadialGradient(384, 384, 60, 384, 384, 360);
    glow.addColorStop(0, 'rgba(120,223,243,.25)');
    glow.addColorStop(.48, 'rgba(237,203,131,.12)');
    glow.addColorStop(1, 'rgba(0,0,0,0)');
    context.fillStyle = glow;
    context.fillRect(0, 0, 768, 768);
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.font = '700 470px "Noto Sans Devanagari", "Segoe UI Symbol", sans-serif';
    context.shadowColor = '#78DFF3';
    context.shadowBlur = 54;
    context.fillStyle = '#FFF5D8';
    context.fillText('ॐ', 384, 398);
    context.shadowColor = '#EDCB83';
    context.shadowBlur = 26;
    context.strokeStyle = '#EDCB83';
    context.lineWidth = 7;
    context.strokeText('ॐ', 384, 398);
    const output = new THREE.CanvasTexture(canvas);
    output.minFilter = THREE.LinearMipmapLinearFilter;
    output.generateMipmaps = true;
    output.colorSpace = THREE.SRGBColorSpace;
    return output;
  }, []);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    const speed = state === 'thinking' ? .012 : state === 'working' ? .009 : state === 'healing' ? .01 : state === 'blocked' ? .004 : .005;
    if (group.current) {
      group.current.rotation.y = Math.sin(elapsed * .33) * .09;
      group.current.position.y = Math.sin(elapsed * .9) * .035;
    }
    if (ringA.current) ringA.current.rotation.z += speed;
    if (ringB.current) ringB.current.rotation.z -= speed * 1.45;
  });

  const tone = state === 'healing' ? 0xf4b860 : state === 'blocked' ? 0xfa7e85 : state === 'working' ? 0x53e7a3 : state === 'thinking' ? 0x45bdf5 : 0xedcb83;
  return <group ref={group}>
    <mesh>
      <planeGeometry args={[2.65, 2.65]} />
      <meshBasicMaterial map={texture ?? undefined} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
    <mesh ref={ringA} rotation={[0, 0, .2]}>
      <torusGeometry args={[1.55, .012, 8, 120]} />
      <meshBasicMaterial color={tone} transparent opacity={.68} blending={THREE.AdditiveBlending} />
    </mesh>
    <mesh ref={ringB} rotation={[0, 0, -.4]}>
      <torusGeometry args={[1.83, .009, 8, 120]} />
      <meshBasicMaterial color={0x78dff3} transparent opacity={.48} blending={THREE.AdditiveBlending} />
    </mesh>
  </group>;
}

function CosmicDots({ state, pointer }: { state: CoreMotionState; pointer: { x: number; y: number } }) {
  const count = 96;
  const pointRef = useRef<THREE.Points>(null);
  const lineRef = useRef<THREE.LineSegments>(null);
  const frame = useRef(0);
  const data = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const origins = new Float32Array(count * 3);
    const phase = new Float32Array(count);
    for (let index = 0; index < count; index++) {
      const radius = .3 + Math.pow(Math.random(), .65) * 1.65;
      const angle = Math.random() * Math.PI * 2;
      const z = (Math.random() - .5) * 1.35;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius * .82;
      positions[index * 3] = origins[index * 3] = x;
      positions[index * 3 + 1] = origins[index * 3 + 1] = y;
      positions[index * 3 + 2] = origins[index * 3 + 2] = z;
      phase[index] = Math.random() * Math.PI * 2;
    }
    return { positions, origins, phase };
  }, []);
  const pointGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
    return geometry;
  }, [data.positions]);
  const lineGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(200 * 6), 3));
    return geometry;
  }, []);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    const speed = state === 'thinking' ? 2.25 : state === 'working' ? 1.75 : state === 'healing' ? 1.55 : state === 'blocked' ? .55 : 1;
    const pos = pointGeometry.attributes.position.array as Float32Array;
    for (let index = 0; index < count; index++) {
      const base = index * 3;
      const wave = .035 * Math.sin(elapsed * (1.1 + speed * .4) + data.phase[index]);
      const px = data.origins[base];
      const py = data.origins[base + 1];
      const influence = Math.max(0, 1 - Math.hypot(pointer.x - px / 2.2, pointer.y - py / 2.0) / .8);
      pos[base] = px + wave + pointer.x * influence * .14;
      pos[base + 1] = py + Math.cos(elapsed * 1.2 + data.phase[index]) * .025 + pointer.y * influence * .12;
      pos[base + 2] = data.origins[base + 2] + Math.sin(elapsed * .8 + data.phase[index]) * .04;
    }
    pointGeometry.attributes.position.needsUpdate = true;
    if (pointRef.current) pointRef.current.rotation.z += .0009 * speed;

    frame.current++;
    if (frame.current % 2 !== 0) return;
    const lines = lineGeometry.attributes.position.array as Float32Array;
    let lineCount = 0;
    const maxDistance = state === 'working' || state === 'thinking' ? .64 : .52;
    for (let a = 0; a < count && lineCount < 200; a++) {
      const ai = a * 3;
      for (let b = a + 1; b < count && lineCount < 200; b++) {
        const bi = b * 3;
        const dx = pos[ai] - pos[bi];
        const dy = pos[ai + 1] - pos[bi + 1];
        const dz = pos[ai + 2] - pos[bi + 2];
        if (dx * dx + dy * dy + dz * dz > maxDistance * maxDistance) continue;
        const out = lineCount * 6;
        lines[out] = pos[ai]; lines[out + 1] = pos[ai + 1]; lines[out + 2] = pos[ai + 2];
        lines[out + 3] = pos[bi]; lines[out + 4] = pos[bi + 1]; lines[out + 5] = pos[bi + 2];
        lineCount++;
      }
    }
    lines.fill(0, lineCount * 6);
    lineGeometry.setDrawRange(0, lineCount * 2);
    lineGeometry.attributes.position.needsUpdate = true;
  });

  const dotColor = state === 'healing' ? '#F4B860' : state === 'blocked' ? '#FA7E85' : state === 'working' ? '#53E7A3' : '#78DFF3';
  return <group>
    <points ref={pointRef} geometry={pointGeometry}>
      <pointsMaterial size={.045} color={dotColor} transparent opacity={.92} depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
    </points>
    <lineSegments ref={lineRef} geometry={lineGeometry}>
      <lineBasicMaterial color="#78DFF3" transparent opacity={.22} depthWrite={false} blending={THREE.AdditiveBlending} />
    </lineSegments>
  </group>;
}

export default function CosmicOm({ state = 'idle' }: { state?: CoreMotionState }) {
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const reducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  useEffect(() => {
    if (reducedMotion) return;
    const move = (event: PointerEvent) => setPointer({ x: (event.clientX / window.innerWidth) * 2 - 1, y: -(event.clientY / window.innerHeight) * 2 + 1 });
    window.addEventListener('pointermove', move, { passive: true });
    return () => window.removeEventListener('pointermove', move);
  }, [reducedMotion]);
  return <div className="cosmic-om" aria-label={`KRISHNA cognitive core ${state}`}>
    <Canvas camera={{ position: [0, 0, 5], fov: 44 }} dpr={[1, 1.65]} gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}>
      <ambientLight intensity={.8} />
      <CosmicDots state={reducedMotion ? 'idle' : state} pointer={reducedMotion ? { x: 0, y: 0 } : pointer} />
      <OmCore state={reducedMotion ? 'idle' : state} />
    </Canvas>
    <div className="cosmic-om-vignette" />
  </div>;
}
