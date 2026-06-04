import { Suspense, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";

import type { AnalysisResult } from "../../types/analysis";
import { analysisToSphereData } from "./sphereUtils";
import BrainCore from "./BrainCore";
import AnalysisRegion from "./AnalysisRegion";
import NeuralConnections from "./NeuralConnections";
import NeuralParticles from "./NeuralParticles";

/** Stops/starts the THREE clock so elapsed time doesn't accumulate during pause. */
function ClockController({ isPlaying }: { isPlaying: boolean }) {
  const clock = useThree((s) => s.clock);
  useEffect(() => {
    if (isPlaying) {
      clock.start();
    } else {
      clock.stop();
    }
  }, [isPlaying, clock]);
  return null;
}

interface BrainSphereProps {
  analysis: AnalysisResult;
  currentTime: number;
  isPlaying?: boolean;
}

export default function BrainSphere({
  analysis,
  currentTime,
  isPlaying = true,
}: BrainSphereProps) {
  const sphereData = analysisToSphereData(analysis, currentTime);

  return (
    <div className="relative w-full h-full min-h-[300px]">
      <Canvas
        camera={{ position: [0, 0, 6.5], fov: 55 }}
        dpr={[1, 2]}
        frameloop="always"
        style={{ background: "transparent" }}
      >
        <ClockController isPlaying={isPlaying} />
        <color attach="background" args={["#050816"]} />
        <fog attach="fog" args={["#050816", 8, 20]} />

        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1.2} />
        <pointLight position={[-10, -10, -5]} intensity={0.6} color="#4f8cff" />
        <pointLight position={[0, 0, 6]} intensity={0.4} color="#ff6b9d" />

        <Suspense fallback={null}>
          <Stars
            radius={50}
            depth={50}
            count={1500}
            factor={4}
            fade
            speed={0.5}
          />

          <BrainCore
            engagement={sphereData.engagement}
            emotion={sphereData.emotion}
            cognitiveLoad={sphereData.cognitiveLoad}
            isPlaying={isPlaying}
          />

          {sphereData.regions.map((region) => (
            <AnalysisRegion
              key={region.id}
              name={region.name}
              intensity={region.intensity}
              position={region.position}
              isPlaying={isPlaying}
            />
          ))}

          <NeuralConnections regions={sphereData.regions} isPlaying={isPlaying} />
          <NeuralParticles engagement={sphereData.engagement} count={400} isPlaying={isPlaying} />

          <EffectComposer>
            <Bloom
              intensity={1.4}
              luminanceThreshold={0.15}
              luminanceSmoothing={0.6}
              mipmapBlur
            />
          </EffectComposer>
        </Suspense>

        <OrbitControls
          enablePan={false}
          minDistance={3.5}
          maxDistance={12}
          autoRotate={isPlaying}
          autoRotateSpeed={0.6}
        />
      </Canvas>

      {/* Title overlay */}
      <div className="absolute top-3 left-4 pointer-events-none">
        <p className="text-label-sm uppercase tracking-widest text-primary">
          Neural Analysis
        </p>
        <p className="text-mono-metric text-on-surface-variant/50 mt-0.5">
          Real-time metric activation
        </p>
      </div>
    </div>
  );
}
