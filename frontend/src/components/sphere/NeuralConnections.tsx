import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { SphereRegion } from "./sphereUtils";
import { intensityToColor } from "./sphereUtils";

interface NeuralConnectionsProps {
  regions: SphereRegion[];
  isPlaying?: boolean;
}

export default function NeuralConnections({ regions, isPlaying = true }: NeuralConnectionsProps) {
  const ref = useRef<THREE.LineSegments>(null!);
  const localTime = useRef(0);

  const { geometry, colors } = useMemo(() => {
    const positions: number[] = [];
    const cols: number[] = [];

    for (let i = 0; i < regions.length; i++) {
      for (let j = i + 1; j < regions.length; j++) {
        const avg = (regions[i].intensity + regions[j].intensity) / 2;
        if (avg > 0.55) {
          positions.push(...regions[i].position, ...regions[j].position);
          const color = intensityToColor(avg);
          cols.push(color.r, color.g, color.b, color.r, color.g, color.b);
        }
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );
    geo.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
    return { geometry: geo, colors: cols };
  }, [regions]);

  useFrame((_, rawDelta) => {
    if (!isPlaying) return;
    const delta = Math.min(rawDelta, 0.1);
    localTime.current += delta;
    if (ref.current) {
      const mat = ref.current.material as THREE.LineBasicMaterial;
      mat.opacity = 0.3 + Math.sin(localTime.current * 2) * 0.15;
    }
  });

  if (colors.length === 0) return null;

  return (
    <lineSegments ref={ref} geometry={geometry}>
      <lineBasicMaterial
        vertexColors
        transparent
        opacity={0.4}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  );
}
