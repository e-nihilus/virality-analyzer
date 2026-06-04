import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { intensityToColor } from "./sphereUtils";

interface AnalysisRegionProps {
  name: string;
  intensity: number;
  position: [number, number, number];
  isPlaying?: boolean;
}

export default function AnalysisRegion({
  name,
  intensity,
  position,
  isPlaying = true,
}: AnalysisRegionProps) {
  const groupRef = useRef<THREE.Group>(null!);
  const ringRef = useRef<THREE.Mesh>(null!);
  const localTime = useRef(0);

  const color = intensityToColor(intensity);
  const size = 0.1 + intensity * 0.22;

  useFrame((_, rawDelta) => {
    if (!isPlaying) return;
    const delta = Math.min(rawDelta, 0.1);
    localTime.current += delta;
    const t = localTime.current;

    if (groupRef.current) {
      const pulse = 1 + Math.sin(t * (2 + intensity * 3)) * 0.15;
      groupRef.current.scale.setScalar(pulse);
    }

    if (ringRef.current) {
      const ringScale = 1 + ((t * (0.5 + intensity)) % 2);
      ringRef.current.scale.setScalar(ringScale);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity =
        Math.max(0, 1 - ((t * (0.5 + intensity)) % 2) / 2) * 0.4;
    }
  });

  return (
    <group position={position}>
      <group ref={groupRef}>
        {/* Core dot */}
        <mesh>
          <sphereGeometry args={[size, 16, 16]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={0.8}
          />
        </mesh>

        {/* Halo */}
        <mesh>
          <sphereGeometry args={[size * 1.6, 16, 16]} />
          <meshBasicMaterial color={color} transparent opacity={0.15} />
        </mesh>
      </group>

      {/* Expanding pulse ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[size * 1.2, size * 1.4, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.3}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Label (visible only for active regions) */}
      {intensity > 0.45 && (
        <Html
          position={[0, size * 2.5, 0]}
          center
          style={{ pointerEvents: "none" }}
        >
          <div className="region-label">
            {name} <span>{Math.round(intensity * 100)}%</span>
          </div>
        </Html>
      )}
    </group>
  );
}
