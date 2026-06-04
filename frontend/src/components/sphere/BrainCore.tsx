import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface BrainCoreProps {
  engagement: number;
  emotion: number;
  cognitiveLoad: number;
  isPlaying?: boolean;
}

export default function BrainCore({
  engagement,
  emotion,
  cognitiveLoad,
  isPlaying = true,
}: BrainCoreProps) {
  const outerRef = useRef<THREE.Mesh>(null!);
  const innerRef = useRef<THREE.Mesh>(null!);
  const matRef = useRef<THREE.MeshStandardMaterial>(null!);
  const localTime = useRef(0);

  useFrame((_, rawDelta) => {
    if (!isPlaying) return;
    const delta = Math.min(rawDelta, 0.1);
    localTime.current += delta;
    const t = localTime.current;
    const speed = 0.4 + engagement * 1.5;
    const scale = 1 + Math.sin(t * speed) * 0.05;

    if (outerRef.current) {
      outerRef.current.scale.setScalar(scale);
      outerRef.current.rotation.y += 0.002;
    }

    if (innerRef.current) {
      innerRef.current.rotation.y -= 0.001;
      innerRef.current.rotation.x += 0.0005;
    }

    if (matRef.current) {
      matRef.current.emissiveIntensity =
        0.3 + Math.sin(t * (1 + cognitiveLoad * 4)) * 0.2;
    }
  });

  const hue = 0.6 - emotion * 0.3;
  const wireColor = new THREE.Color().setHSL(hue, 0.7, 0.4);
  const emissiveColor = new THREE.Color().setHSL(hue, 0.9, 0.3);

  return (
    <>
      {/* Outer wireframe sphere */}
      <mesh ref={outerRef}>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial
          ref={matRef}
          wireframe
          color={wireColor}
          emissive={emissiveColor}
          emissiveIntensity={0.3}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* Inner solid sphere */}
      <mesh ref={innerRef}>
        <sphereGeometry args={[1.78, 32, 32]} />
        <meshStandardMaterial
          color="#0a0e27"
          emissive={emissiveColor}
          emissiveIntensity={0.1}
          transparent
          opacity={0.22}
        />
      </mesh>
    </>
  );
}
