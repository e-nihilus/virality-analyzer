import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface NeuralParticlesProps {
  engagement: number;
  count?: number;
  isPlaying?: boolean;
}

export default function NeuralParticles({
  engagement,
  count = 400,
  isPlaying = true,
}: NeuralParticlesProps) {
  const ref = useRef<THREE.Points>(null!);
  const localTime = useRef(0);

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2.2 + Math.random() * 1.8;
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, [count]);

  useFrame((_, rawDelta) => {
    if (!ref.current || !isPlaying) return;
    const delta = Math.min(rawDelta, 0.1);
    localTime.current += delta;
    const t = localTime.current;
    const speed = 0.1 + engagement * 0.3;
    ref.current.rotation.y = t * speed;

    const pos = ref.current.geometry.attributes.position;
    for (let i = 0; i < count; i++) {
      const baseY = positions[i * 3 + 1];
      (pos.array as Float32Array)[i * 3 + 1] =
        baseY + Math.sin(t * 0.5 + i * 0.1) * 0.05;
    }
    pos.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#4f8cff"
        transparent
        opacity={0.6}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        sizeAttenuation
      />
    </points>
  );
}
