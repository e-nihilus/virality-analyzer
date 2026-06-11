/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { MetricState, METRICS_LIST } from "../types";
import { AlertCircle, RotateCcw, ZoomIn, ZoomOut, Maximize2, Move } from "lucide-react";

interface MetricsCanvasProps {
  metrics: MetricState;
  autoPlayBeat: boolean;
  hoveredMetricKey: keyof MetricState | null;
}

// Map of 3D virtual direction poles matching the shader exactly for overlay projection
const POLES_CONFIG: Record<string, { name: string; color: string; dir: THREE.Vector3 }> = {
  valence: { name: "Valence", color: "#00F2FF", dir: new THREE.Vector3(-0.52,  0.60, 0.61) },
  virality: { name: "Virality", color: "#FF00E5", dir: new THREE.Vector3( 0.52,  0.60, 0.61) },
  arousal: { name: "Arousal", color: "#FF3D00", dir: new THREE.Vector3( 0.85,  0.12, 0.51) },
  pacing: { name: "Pacing", color: "#AD00FF", dir: new THREE.Vector3(-0.85,  0.12, 0.51) },
  retention: { name: "Retention", color: "#FF00E5", dir: new THREE.Vector3(-0.52, -0.68, 0.52) },
  emotion: { name: "Emotion", color: "#14FF00", dir: new THREE.Vector3( 0.52, -0.68, 0.52) },
  hook: { name: "Hook", color: "#FFD600", dir: new THREE.Vector3( 0.00, -0.90, 0.44) }
};

// Sphere Vertex Shader
const SPHERE_VERTEX_SHADER = `
varying vec3 vLocalPosition;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
    // Pass local position to fragment shader for localized raymarching
    vLocalPosition = position;
    
    // Calculate normal and view direction for Fresnel edge glow
    vNormal = normalize(normalMatrix * normal);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;
    
    gl_Position = projectionMatrix * mvPosition;
}
`;

// Volumetric raymarching glass fractal shader
const SPHERE_FRAGMENT_SHADER = `
uniform float uTime;
uniform vec3 uLocalCamPos;
uniform vec3 uPrimaryColor;
uniform vec3 uSecondaryColor;
uniform float uDensity;

// Individual metric values [0.0 - 1.0] for localized spatial color scaling
uniform float uValence;
uniform float uVirality;
uniform float uArousal;
uniform float uPacing;
uniform float uRetention;
uniform float uEmotion;
uniform float uHook;

// Fractal Specific Uniforms
uniform float uFractalIters;
uniform float uFractalScale;
uniform float uFractalDecay;
uniform float uInternalAnim;
uniform float uSmoothness;
uniform float uAsymmetry;

varying vec3 vLocalPosition;
varying vec3 vNormal;
varying vec3 vViewPosition;

// Evaluates the internal volume structure
float evaluateStructure(vec3 pos) {
    float densityAcc = 0.0;
    vec3 anchor = pos;
    
    // Calculate rotation for internal animation
    float animTime = uTime * uInternalAnim;
    float s = sin(animTime);
    float c = cos(animTime);
    mat2 rotAnim = mat2(c, s, -s, c);

    // Static rotations based on asymmetry parameter to break mirror planes
    float a = 0.5 * uAsymmetry;
    mat2 rotAsym1 = mat2(cos(a), sin(a), -sin(a), cos(a));
    float b = 0.3 * uAsymmetry;
    mat2 rotAsym2 = mat2(cos(b), sin(b), -sin(b), cos(b));
    
    // Iterative space folding (bound to safe performance limit 10)
    for (int step = 0; step < 10; ++step) {
        if (float(step) >= uFractalIters) break;
        
        // 1. Internal animation: smoothly rotate space over time
        pos.xy *= rotAnim;
        pos.yz *= rotAnim;
        
        // 2. Break exact global mirroring completely
        pos.xz *= rotAsym1;
        pos.yz *= rotAsym2;
        pos += vec3(0.05, -0.02, 0.03) * uAsymmetry;
        
        // 3. Smooth Fold Space (Replaces harsh abs() function)
        vec3 foldedPos = sqrt(pos * pos + uSmoothness);
        float magnitudeSq = dot(foldedPos, foldedPos);
        magnitudeSq = max(magnitudeSq, 0.00001); 
        
        pos = (uFractalScale * foldedPos / magnitudeSq) - uFractalScale;
        
        // Complex square transformation on YZ plane mapped to variables
        float ySq = pos.y * pos.y;
        float zSq = pos.z * pos.z;
        float yz2 = 2.0 * pos.y * pos.z;
        pos.yz = vec2(ySq - zSq, yz2);
        
        // Safe axes swizzle
        pos = vec3(pos.z, pos.x, pos.y);
        
        // Accumulate field strength
        densityAcc += exp(uFractalDecay * abs(dot(pos, anchor)));
    }
    
    return densityAcc * 0.5;
}

// Boundary intersection calculation
vec2 getVolumeBounds(vec3 origin, vec3 dir, float radius) {
    float b = dot(origin, dir);
    float c = dot(origin, origin) - radius * radius;
    float discriminant = b * b - c;
    
    if (discriminant < 0.0) {
        return vec2(-1.0);
    }
    
    float root = sqrt(discriminant);
    return vec2(-b - root, -b + root);
}

// Raymarch through the defined volume
vec3 traceEnergy(vec3 origin, vec3 dir, vec2 limits) {
    float currentDepth = limits.x;
    float marchStep = 0.03;
    vec3 finalEnergy = vec3(0.0);
    float fieldVal = 0.0;
    
    // Pole Directions matching POLES_CONFIG precisely in local space
    vec3 pDir[7];
    pDir[0] = vec3(-0.52,  0.60, 0.61); // valence
    pDir[1] = vec3( 0.52,  0.60, 0.61); // virality
    pDir[2] = vec3( 0.85,  0.12, 0.51); // arousal
    pDir[3] = vec3(-0.85,  0.12, 0.51); // pacing
    pDir[4] = vec3(-0.52, -0.68, 0.52); // retention
    pDir[5] = vec3( 0.52, -0.68, 0.52); // emotion
    pDir[6] = vec3( 0.00, -0.90, 0.44); // hook

    // Pole Colors
    vec3 pCol[7];
    pCol[0] = vec3(0.0, 1.0, 1.0);    // Highly vibrant Teal #00F2FF
    pCol[1] = vec3(1.0, 0.0, 0.9);    // Highly vibrant Pink #FF00E5
    pCol[2] = vec3(1.0, 0.18, 0.0);   // Highly vibrant Lava Orange #FF3D00
    pCol[3] = vec3(0.7, 0.0, 1.0);    // Highly vibrant Indigo #AD00FF
    pCol[4] = vec3(1.0, 0.0, 0.5);    // Vibrant Crimson/Pink
    pCol[5] = vec3(0.0, 1.0, 0.1);    // Highly vibrant Lime #14FF00
    pCol[6] = vec3(1.1, 0.85, 0.0);   // Highly vibrant Amber Yellow #FFD600

    float pVal[7];
    pVal[0] = uValence;
    pVal[1] = uVirality;
    pVal[2] = uArousal;
    pVal[3] = uPacing;
    pVal[4] = uRetention;
    pVal[5] = uEmotion;
    pVal[6] = uHook;
    
    for(int i = 0; i < 48; i++) { // Optimized steps for high web performance in iframes
        // Adaptive stepping based on density
        currentDepth += marchStep * exp(-2.0 * fieldVal);
        if(currentDepth > limits.y) break;
        
        vec3 samplePoint = origin + currentDepth * dir;
        fieldVal = evaluateStructure(samplePoint);
        
        // Calculate color emission for this step
        float vSq = fieldVal * fieldVal;
        
        // Inverse matrix-free rotation of uTime twist to match static POLES_CONFIG indicators precisely
        float t = uTime * 0.1;
        float s = sin(-t);
        float c = cos(-t);
        mat2 invRotXZ = mat2(c, s, -s, c);
        vec3 untwistedPoint = samplePoint;
        untwistedPoint.xz *= invRotXZ;
        
        vec3 N = normalize(untwistedPoint);
        
        // Multi-color proportional blending
        vec3 blendedColor = vec3(0.01, 0.02, 0.06); // Deep space background glow fallback
        float totalWeight = 0.05;
        float localIntensity = 0.0;
        
        for (int j = 0; j < 7; ++j) {
            float cosTheta = dot(N, normalize(pDir[j]));
            // Proximity influence: use pow max(cosTheta, 0.0) for razor-sharp, localized sectors
            // This ensures each pointer points EXACTLY at their respective color sector,
            // with zero cross-bleeding to the opposite side of the sphere.
            float influence = pow(max(cosTheta, 0.0), 6.5);
            
            // Weight is proportional to both proximity and the metric value (plus base)
            float weight = influence * (pVal[j] * 0.95 + 0.05);
            
            // Add custom peak luminescence factor for active metrics to raise color vividness
            vec3 poleColorBoost = pCol[j] * (1.2 + pVal[j] * 2.5);
            blendedColor += poleColorBoost * weight;
            totalWeight += weight;
            
            // Local intensity based on active values nearby
            localIntensity += influence * pVal[j];
        }
        
        vec3 currentGradient = blendedColor / totalWeight;
        
        // Scale emission zone by the active metric intensity locally (substantially boosted for vividness)
        float activeScalar = mix(0.4, 2.5, localIntensity);
        vec3 emission = currentGradient * (fieldVal * 2.8 + vSq * 2.2) * activeScalar;
        
        // Accumulate color
        finalEnergy = 0.99 * finalEnergy + (0.08 * uDensity) * emission;
    }
    
    return finalEnergy;
}

void main() {
    // Ray setup in local object space
    vec3 rayOrig = uLocalCamPos;
    vec3 rayDir = normalize(vLocalPosition - uLocalCamPos);
    
    // Add internal time-based twisting to the ray path
    float t = uTime * 0.1;
    float s = sin(t);
    float c = cos(t);
    mat2 rotXZ = mat2(c, s, -s, c);
    rayOrig.xz *= rotXZ;
    rayDir.xz *= rotXZ;

    // Sphere intersection (Radius 2.0 to match original fractal scale)
    vec2 limits = getVolumeBounds(rayOrig, rayDir, 2.0);
    
    if (limits.x < 0.0) {
        discard; // Missed the bounding volume completely
    }
    
    // Accumulate volumetric data
    vec3 volumeColor = traceEnergy(rayOrig, rayDir, limits);
    
    // Get facing ratio to soften the hard geometric edge of the fractal
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewPosition);
    float facingRatio = max(dot(normal, viewDir), 0.0);
    
    // Anti-aliasing fade to completely erase the polygonal edge
    float edgeAA = smoothstep(0.0, 0.05, facingRatio);
    
    // Exponential exposure tonemapping for rich HDR response and ultra-vivid peaks
    vec3 finalColor = 1.0 - exp(-volumeColor * 2.2);
    
    // Apply the anti-aliasing fade
    finalColor *= edgeAA;
    
    // Opacity is tied to luminosity so empty space is fully transparent
    float maxLuma = max(finalColor.r, max(finalColor.g, finalColor.b));
    float alpha = clamp(maxLuma * 1.8, 0.0, 1.0) * edgeAA;
    
    gl_FragColor = vec4(finalColor * alpha, alpha);
}
`;

// Atmosphere Halo Shaders for beautiful blurred glass contour outline
const ATMOSPHERE_VERTEX_SHADER = `
varying vec3 vNormal;
varying vec3 vViewPosition;
void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;
    gl_Position = projectionMatrix * mvPosition;
}
`;

const ATMOSPHERE_FRAGMENT_SHADER = `
uniform vec3 uColor;
uniform float uGlow;
uniform float uLevel;
varying vec3 vNormal;
varying vec3 vViewPosition;
void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewPosition);
    float vdn = max(dot(normal, viewDir), 0.0);
    
    // Soften the absolute outer edge to prevent geometric aliasing (blur effect)
    float edgeFade = smoothstep(0.0, 0.15, vdn);
    
    // Fade out the center completely to keep it hollow.
    // uLevel controls how thick the halo is.
    float innerFadePoint = clamp(1.0 - uLevel, 0.0, 0.99);
    float centerFade = smoothstep(1.0, innerFadePoint, vdn);
    
    // Combine to create a soft, blurred ring stroke
    float alpha = edgeFade * centerFade * uGlow;
    
    gl_FragColor = vec4(uColor, alpha);
}
`;

export default function MetricsCanvas({ metrics, autoPlayBeat, hoveredMetricKey }: MetricsCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const particlesMatRef = useRef<THREE.ShaderMaterial | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const sphereRef = useRef<THREE.Mesh | null>(null);
  const particlesRef = useRef<THREE.Points | null>(null);
  
  // Interactive navigation states
  const [zoom, setZoom] = useState<number>(1);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [webglError, setWebglError] = useState<string | null>(null);

  const composerRef = useRef<EffectComposer | null>(null);
  const atmosphereMaterialRef = useRef<THREE.ShaderMaterial | null>(null);
  const atmosphereMeshRef = useRef<THREE.Mesh | null>(null);

  // Mouse drag tracking
  const mouseRef = useRef({ x: 0, y: 0 });
  const rotationTargetRef = useRef({ x: 0, y: 0 });
  const rotationCurrentRef = useRef({ x: 0, y: 0 });

  // Uniform target values for fluid interpolation
  const currentUniformsRef = useRef({
    valence: 0.5,
    virality: 0.5,
    arousal: 0.5,
    pacing: 0.5,
    retention: 0.5,
    emotion: 0.5,
    hook: 0.5,
    valenceHover: 0.0,
    viralityHover: 0.0,
    arousalHover: 0.0,
    pacingHover: 0.0,
    retentionHover: 0.0,
    emotionHover: 0.0,
    hookHover: 0.0,
  });

  const interpolatedMetricsRef = useRef({
    valence: 0.5,
    virality: 0.5,
    arousal: 0.5,
    pacing: 0.5,
    retention: 0.5,
    emotion: 0.5,
    hook: 0.5,
  });

  // Zoom handlers
  const handleZoomIn = () => setZoom(z => Math.min(z + 0.15, 2.0));
  const handleZoomOut = () => setZoom(z => Math.max(z - 0.15, 0.6));
  const handleResetCamera = () => {
    setZoom(1);
    rotationTargetRef.current = { x: 0, y: 0 };
    rotationCurrentRef.current = { x: 0, y: 0 };
    if (sphereRef.current) {
      sphereRef.current.rotation.set(0, 0, 0);
    }
  };

  // Convert key percentages to [0.0 - 1.0] uniforms
  useEffect(() => {
    // Smooth interpolations managed directly on the requestAnimationFrame for supreme fluidity
    // But we write down targeted values here
    currentUniformsRef.current.valence = metrics.valence / 100;
    currentUniformsRef.current.virality = metrics.virality / 100;
    currentUniformsRef.current.arousal = metrics.arousal / 100;
    currentUniformsRef.current.pacing = metrics.pacing / 100;
    currentUniformsRef.current.retention = metrics.retention / 100;
    currentUniformsRef.current.emotion = metrics.emotion / 100;
    currentUniformsRef.current.hook = metrics.hook / 100;
  }, [metrics]);

  // Handle hovered metrics highlights
  useEffect(() => {
    currentUniformsRef.current.valenceHover = hoveredMetricKey === "valence" ? 1.0 : 0.0;
    currentUniformsRef.current.viralityHover = hoveredMetricKey === "virality" ? 1.0 : 0.0;
    currentUniformsRef.current.arousalHover = hoveredMetricKey === "arousal" ? 1.0 : 0.0;
    currentUniformsRef.current.pacingHover = hoveredMetricKey === "pacing" ? 1.0 : 0.0;
    currentUniformsRef.current.retentionHover = hoveredMetricKey === "retention" ? 1.0 : 0.0;
    currentUniformsRef.current.emotionHover = hoveredMetricKey === "emotion" ? 1.0 : 0.0;
    currentUniformsRef.current.hookHover = hoveredMetricKey === "hook" ? 1.0 : 0.0;
  }, [hoveredMetricKey]);

  // Mouse interaction handlers (Orbital dragging)
  const handleMouseDown = (e: React.MouseEvent) => {
    setDragActive(true);
    mouseRef.current = {
      x: e.clientX,
      y: e.clientY
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragActive) return;
    const deltaX = e.clientX - mouseRef.current.x;
    const deltaY = e.clientY - mouseRef.current.y;

    rotationTargetRef.current.y += deltaX * 0.007;
    rotationTargetRef.current.x += deltaY * 0.007;

    rotationTargetRef.current.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, rotationTargetRef.current.x));

    mouseRef.current = {
      x: e.clientX,
      y: e.clientY
    };
  };

  const handleMouseUp = () => {
    setDragActive(false);
  };

  // Support Mobile Touch Controls
  const handleTouchStart = (e: React.TouchEvent) => {
    setDragActive(true);
    if (e.touches[0]) {
      mouseRef.current = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY
      };
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!dragActive || !e.touches[0]) return;
    const deltaX = e.touches[0].clientX - mouseRef.current.x;
    const deltaY = e.touches[0].clientY - mouseRef.current.y;

    rotationTargetRef.current.y += deltaX * 0.009;
    rotationTargetRef.current.x += deltaY * 0.009;
    rotationTargetRef.current.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, rotationTargetRef.current.x));

    mouseRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY
    };
  };

  // Setup WebGL Scene
  useEffect(() => {
    if (!containerRef.current) return;

    // WebGL capability check
    try {
      const testCanvas = document.createElement("canvas");
      const testContext = testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl");
      if (!testContext) {
        throw new Error("Su navegador o tarjeta gráfica no soporta WebGL.");
      }
    } catch (err: any) {
      setWebglError(err.message || "WebGL no disponible.");
      return;
    }

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight || 500;

    // Create Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Create Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 50);
    camera.position.set(0, 0, 8);
    cameraRef.current = camera;

    // Create Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Lock index to 2 for performance
    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Setup Postprocessing
    const composer = new EffectComposer(renderer);
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);

    const ChromaticAberrationShader = {
      uniforms: {
        "tDiffuse": { value: null },
        "uAmount": { value: 0.012 }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float uAmount;
        varying vec2 vUv;
        void main() {
          vec4 baseColor = texture2D(tDiffuse, vUv);
          float luma = max(baseColor.r, max(baseColor.g, baseColor.b));
          float mask = smoothstep(0.01, 0.1, luma);
          vec2 offset = (vUv - 0.5) * uAmount;
          float r = texture2D(tDiffuse, vUv + offset).r;
          float g = texture2D(tDiffuse, vUv).g;
          float b = texture2D(tDiffuse, vUv - offset).b;
          vec3 aberratedColor = vec3(r, g, b);
          gl_FragColor = vec4(mix(baseColor.rgb, aberratedColor, mask), baseColor.a);
        }
      `
    };

    const chromaPass = new ShaderPass(ChromaticAberrationShader);
    composer.addPass(chromaPass);
    composerRef.current = composer;

    // Create Sphere Geometry (High density for crystal smooth silhouette and atmospheric halo)
    const geometry = new THREE.SphereGeometry(2.0, 128, 128);

    // Initial values for shader interpolation
    const shaderUniforms = {
      uTime: { value: 0.0 },
      uLocalCamPos: { value: new THREE.Vector3() },
      uPrimaryColor: { value: new THREE.Color("#00b3ff") },
      uSecondaryColor: { value: new THREE.Color("#2e9aff") },
      uDensity: { value: 3.0 },
      uFractalIters: { value: 4.0 },
      uFractalScale: { value: 0.97 },
      uFractalDecay: { value: -16.7 },
      uInternalAnim: { value: 0.43 },
      uSmoothness: { value: 0.031 },
      uAsymmetry: { value: 0.55 },
      // Individual metric values registered for custom pixel shaders
      uValence: { value: 0.5 },
      uVirality: { value: 0.5 },
      uArousal: { value: 0.5 },
      uPacing: { value: 0.5 },
      uRetention: { value: 0.5 },
      uEmotion: { value: 0.5 },
      uHook: { value: 0.5 }
    };

    // Create custom Sphere material
    const material = new THREE.ShaderMaterial({
      vertexShader: SPHERE_VERTEX_SHADER,
      fragmentShader: SPHERE_FRAGMENT_SHADER,
      uniforms: shaderUniforms,
      transparent: true,
      blending: THREE.AdditiveBlending, // Use additive blending so there is absolutely no dark transparent alpha overlay mask blocking the colors
      depthWrite: false, // Prevents black outlines in overlapping surfaces
      side: THREE.DoubleSide
    });
    materialRef.current = material;

    // Create Mesh
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);
    sphereRef.current = sphere;

    // Create Atmosphere Halo Mesh and link as child to auto spin/rotate
    const atmosphereUniforms = {
      uColor: { value: new THREE.Color("#00b3ff") },
      uGlow: { value: 0.15 },
      uLevel: { value: 1.0 }
    };
    const atmosphereMaterial = new THREE.ShaderMaterial({
      vertexShader: ATMOSPHERE_VERTEX_SHADER,
      fragmentShader: ATMOSPHERE_FRAGMENT_SHADER,
      uniforms: atmosphereUniforms,
      transparent: true,
      blending: THREE.AdditiveBlending,
      side: THREE.FrontSide,
      depthWrite: false
    });
    atmosphereMaterialRef.current = atmosphereMaterial;

    const atmosphereMesh = new THREE.Mesh(geometry, atmosphereMaterial);
    atmosphereMesh.scale.set(1.03, 1.03, 1.03); // CodePen ratio
    sphere.add(atmosphereMesh);
    atmosphereMeshRef.current = atmosphereMesh;

    // Assemble orbiting particle system
    const numParticles = 320;
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(numParticles * 3);
    const particleSizes = new Float32Array(numParticles);
    const particlePhases = new Float32Array(numParticles);

    for (let i = 0; i < numParticles; i++) {
      // Position particles in a medium shell shell around the sphere
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      const r = 2.4 + Math.random() * 2.2; // Spacing distance from 2.4 to 4.6

      particlePositions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = r * Math.cos(phi);
      particlePositions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      particleSizes[i] = 1.0 + Math.random() * 2.5; // Size distribution
      particlePhases[i] = Math.random() * Math.PI * 2; // Random rotation phases
    }

    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    particleGeometry.setAttribute("aSize", new THREE.BufferAttribute(particleSizes, 1));
    particleGeometry.setAttribute("aPhase", new THREE.BufferAttribute(particlePhases, 1));

    // Custom Particle Shaders
    const particleUniforms = {
      uTime: { value: 0.0 },
      uSpeed: { value: 0.2 },
      uIntensity: { value: 0.5 },
      uColor1: { value: new THREE.Color("#0ea5e9") }, // Cyan
      uColor2: { value: new THREE.Color("#ec4899") }  // Pink
    };

    const particlesMaterial = new THREE.ShaderMaterial({
      vertexShader: `
        uniform float uTime;
        uniform float uSpeed;
        attribute float aSize;
        attribute float aPhase;
        varying float vPhase;

        void main() {
          vPhase = aPhase;
          
          float angle = uTime * uSpeed + aPhase;
          float dist = length(position.xz);
          
          vec3 animatedPos = position;
          // Slowly orbit the particles around Y axis
          animatedPos.x = cos(angle) * dist;
          animatedPos.z = sin(angle) * dist;
          
          // Subtle vertical wave
          animatedPos.y += sin(uTime * 0.4 + aPhase * 8.0) * 0.20;

          vec4 mvPosition = modelViewMatrix * vec4(animatedPos, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          
          // Smooth depth sized attenuation
          gl_PointSize = (aSize * 15.0) / -mvPosition.z;
        }
      `,
      fragmentShader: `
        varying float vPhase;
        uniform float uTime;
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        uniform float uIntensity;

        void main() {
          // Circular particle boundary
          vec2 coord = gl_PointCoord - vec2(0.5);
          if (dot(coord, coord) > 0.25) {
            discard;
          }
          
          float dist = length(coord);
          float alpha = smoothstep(0.5, 0.08, dist) * uIntensity;
          
          // Mix colors dynamically
          vec3 mixedColor = mix(uColor1, uColor2, sin(vPhase + uTime * 0.2) * 0.5 + 0.5);
          gl_FragColor = vec4(mixedColor, alpha);
        }
      `,
      uniforms: particleUniforms,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    particlesMatRef.current = particlesMaterial;

    const particles = new THREE.Points(particleGeometry, particlesMaterial);
    scene.add(particles);
    particlesRef.current = particles;

    // Resize observer
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight || 500;
      rendererRef.current.setSize(w, h);
      if (composerRef.current) {
        composerRef.current.setSize(w, h);
      }
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);

    // Dynamic rendering Loop
    const clock = new THREE.Clock();
    let prevTime = 0;

    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();
      const deltaTime = elapsedTime - prevTime;
      prevTime = elapsedTime;

      // Real-time audio reactive pulse simulation (when activated)
      let beatFrequency = 1.0;
      let beatAmplitude = 1.0;
      if (autoPlayBeat) {
        // Synthesizes a beautiful layered organic pulse reflecting audio tempo
        beatFrequency = 1.0 + Math.sin(elapsedTime * 6.0) * 0.15;
        // Periodic kick jump (impacts size slightly)
        const kickBase = Math.max(0.0, Math.sin(elapsedTime * 3.14 - 0.2));
        beatAmplitude = 1.0 + Math.pow(kickBase, 4.0) * 0.12;
      }

      // Transform world camera position into local space of the sphere for raymarching
      if (sphere && cameraRef.current) {
        sphere.updateMatrixWorld();
        const localCam = new THREE.Vector3().copy(cameraRef.current.position);
        sphere.worldToLocal(localCam);
        if (material.uniforms.uLocalCamPos) {
          material.uniforms.uLocalCamPos.value.copy(localCam);
        }
      }

      // Interpolate the metric states inside requestAnimationFrame for fluid transitions
      const lerpHero = Math.min(6.0 * deltaTime, 1.0);
      const mInt = interpolatedMetricsRef.current;
      mInt.valence += (currentUniformsRef.current.valence - mInt.valence) * lerpHero;
      mInt.virality += (currentUniformsRef.current.virality - mInt.virality) * lerpHero;
      mInt.arousal += (currentUniformsRef.current.arousal - mInt.arousal) * lerpHero;
      mInt.pacing += (currentUniformsRef.current.pacing - mInt.pacing) * lerpHero;
      mInt.retention += (currentUniformsRef.current.retention - mInt.retention) * lerpHero;
      mInt.emotion += (currentUniformsRef.current.emotion - mInt.emotion) * lerpHero;
      mInt.hook += (currentUniformsRef.current.hook - mInt.hook) * lerpHero;

      // Smoothly update uniform states
      if (material.uniforms) {
        const u = material.uniforms;
        u.uTime.value = elapsedTime;
        
        // Map 7 interpolated metrics to 7 distinct fractal parameters
        u.uInternalAnim.value = THREE.MathUtils.lerp(0.1, 1.2, mInt.pacing);
        u.uDensity.value = THREE.MathUtils.lerp(0.5, 3.2, mInt.arousal * beatAmplitude);
        u.uSmoothness.value = THREE.MathUtils.lerp(0.005, 0.12, mInt.emotion);
        u.uAsymmetry.value = THREE.MathUtils.lerp(0.0, 0.85, mInt.virality);
        u.uFractalIters.value = Math.round(THREE.MathUtils.lerp(3.0, 6.0, mInt.retention));
        u.uFractalScale.value = THREE.MathUtils.lerp(0.6, 1.3, mInt.valence);
        u.uFractalDecay.value = THREE.MathUtils.lerp(-22.0, -9.0, mInt.hook * beatFrequency);

        // Update real-time individual metrics passed to proportional volume shader
        u.uValence.value = mInt.valence;
        u.uVirality.value = mInt.virality;
        u.uArousal.value = mInt.arousal * beatAmplitude;
        u.uPacing.value = mInt.pacing;
        u.uRetention.value = mInt.retention;
        u.uEmotion.value = mInt.emotion;
        u.uHook.value = mInt.hook * beatFrequency;

        // Organic color weights mapping based on metrics
        const colorMap = {
          valence: new THREE.Color("#00F2FF"), // Teal
          virality: new THREE.Color("#FF00E5"), // Pink
          arousal: new THREE.Color("#FF3D00"), // Lava Orange
          pacing: new THREE.Color("#AD00FF"), // Indigo
          retention: new THREE.Color("#FF00E5"), // Crimson
          emotion: new THREE.Color("#14FF00"), // Lime
          hook: new THREE.Color("#FFD600"), // Amber Yellow
        };

        const sortedMetrics = Object.entries(mInt) as [keyof typeof mInt, number][];
        sortedMetrics.sort((a, b) => b[1] - a[1]); // Descending order of normalized values (0 to 1)

        const pColor = new THREE.Color();
        const sColor = new THREE.Color();

        const highestMetric = sortedMetrics[0];
        const secondHighestMetric = sortedMetrics[1];

        if (highestMetric && highestMetric[1] > 0.05) {
          pColor.copy(colorMap[highestMetric[0]]);
        } else {
          pColor.set("#00b3ff"); // Default cyan
        }

        if (secondHighestMetric && secondHighestMetric[1] > 0.05) {
          sColor.copy(colorMap[secondHighestMetric[0]]);
        } else {
          sColor.copy(pColor).multiplyScalar(0.4).add(new THREE.Color("#0033ff")); // Default blue-shifted background
        }

        u.uPrimaryColor.value.copy(pColor);
        u.uSecondaryColor.value.copy(sColor);

        // Map atmosphere (halo) color to primary color
        if (atmosphereMaterialRef.current && atmosphereMaterialRef.current.uniforms) {
          const atmU = atmosphereMaterialRef.current.uniforms;
          atmU.uColor.value.copy(pColor);
          atmU.uGlow.value = THREE.MathUtils.lerp(0.12, 0.28, mInt.arousal * beatAmplitude);
        }
      }

      // Sync Particle Uniforms
      if (particlesMaterial.uniforms) {
        particlesMaterial.uniforms.uTime.value = elapsedTime;
        
        // Particles orbit faster if pacing is high
        const particleSpeed = 0.12 + (currentUniformsRef.current.pacing * 0.45);
        particlesMaterial.uniforms.uSpeed.value = particleSpeed;

        // Particle count glow increases if virality/arousal is intense
        const particleGlow = 0.35 + (currentUniformsRef.current.virality * 0.5) + (currentUniformsRef.current.arousal * 0.15);
        particlesMaterial.uniforms.uIntensity.value = particleGlow;

        // Shift particle colors matches active metrics
        const primaryColor = new THREE.Color("#00F2FF"); // default cyan
        if (currentUniformsRef.current.hook > 0.6) {
          primaryColor.set("#0057FF"); // Royal Blue
        } else if (currentUniformsRef.current.arousal > 0.6) {
          primaryColor.set("#FF3D00"); // Lava Orange-Red
        } else if (currentUniformsRef.current.virality > 0.6) {
          primaryColor.set("#FF00E5"); // Hyper Pink
        }
        particlesMaterial.uniforms.uColor1.value.lerp(primaryColor, 0.05);

        const secondaryColor = new THREE.Color("#AD00FF"); // default violet
        if (currentUniformsRef.current.pacing > 0.6) {
          secondaryColor.set("#FFD600"); // Yellow
        } else if (currentUniformsRef.current.emotion > 0.6) {
          secondaryColor.set("#14FF00"); // Electric Lime
        } else if (currentUniformsRef.current.valence > 0.6) {
          secondaryColor.set("#00F2FF"); // Cyan
        }
        particlesMaterial.uniforms.uColor2.value.lerp(secondaryColor, 0.05);
      }

      // Camera zooming
      if (cameraRef.current) {
        const targetZ = 8.5 / zoom;
        cameraRef.current.position.z += (targetZ - cameraRef.current.position.z) * 0.1;
      }

      // Orbital rotation lag calculation (Interpolating drag rotation speeds)
      rotationCurrentRef.current.x += (rotationTargetRef.current.x - rotationCurrentRef.current.x) * 0.1;
      rotationCurrentRef.current.y += (rotationTargetRef.current.y - rotationCurrentRef.current.y) * 0.1;

      if (sphere) {
        // Base auto rotating speed scales with pacing
        const autoSpeedY = autoRotate ? (0.16 + currentUniformsRef.current.pacing * 0.45) * deltaTime : 0;
        
        // Apply manual rotations and incremental auto spin
        rotationTargetRef.current.y += autoSpeedY;
        
        sphere.rotation.x = rotationCurrentRef.current.x;
        sphere.rotation.y = rotationCurrentRef.current.y;
      }

      if (particles) {
        // Particles counter rotate slowly
        particles.rotation.x = -rotationCurrentRef.current.x * 0.45;
        particles.rotation.y = -rotationCurrentRef.current.y * 0.45 + elapsedTime * 0.05;
      }

      // 3D HUD Callout Projector Overlay
      if (sphere && cameraRef.current && containerRef.current) {
        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight || 500;
        const keys = Object.keys(POLES_CONFIG);
        keys.forEach((key) => {
          const config = POLES_CONFIG[key];
          
          // Get the dynamic world-space coordinate of the rotating pole on the sphere (scaled to surface radius 2.0)
          const worldPos = config.dir.clone().multiplyScalar(2.0);
          worldPos.applyMatrix4(sphere.matrixWorld);
          
          // Project 3D vector to Normalized Device Coordinates (NDC)
          const projectedVec = worldPos.clone().project(cameraRef.current!);
          
          // Determine if the pole is on the facing surface of the sphere (scaled to 2.0 radius boundary)
          const isFacing = worldPos.z > -0.44;
          
          // Convert NDC (-1 to 1) to screen space coordinates relative to container
          const x = (projectedVec.x * 0.5 + 0.5) * width;
          const y = (-projectedVec.y * 0.5 + 0.5) * height;
          
          const labelEl = document.getElementById(`hud-label-${key}`);
          const pathEl = document.getElementById(`hud-path-${key}`) as unknown as SVGPathElement;
          const dotEl = document.getElementById(`hud-dot-${key}`);
          
          if (labelEl || pathEl || dotEl) {
            const activeVal = metrics[key as keyof typeof metrics] || 0;
            const opacityVal = isFacing ? (activeVal > 15 ? 1.0 : 0.35) : 0.08;
            const showHUD = activeVal > 5;
            
            let bx = x;
            let by = y;
            let lx = x;
            let ly = y;
            
            const isLeft = key === "valence" || key === "pacing" || key === "retention";
            
            if (isLeft) {
              bx = x - 35;
              by = y - 22;
              lx = x - 105;
              ly = y - 22;
            } else if (key === "virality" || key === "arousal" || key === "emotion") {
              bx = x + 35;
              by = y - 22;
              lx = x + 105;
              ly = y - 22;
            } else { // hook (bottom)
              bx = x;
              by = y + 35;
              lx = x + 55;
              ly = y + 35;
            }
            
            bx = Math.max(12, Math.min(width - 12, bx));
            by = Math.max(12, Math.min(height - 12, by));
            lx = Math.max(12, Math.min(width - 12, lx));
            ly = Math.max(12, Math.min(height - 12, ly));
            
            if (dotEl) {
              dotEl.style.transform = `translate(${x}px, ${y}px)`;
              dotEl.style.opacity = showHUD ? opacityVal.toString() : "0";
              dotEl.style.display = showHUD ? "block" : "none";
            }
            
            if (pathEl) {
              pathEl.setAttribute("d", `M ${lx} ${ly} L ${bx} ${by} L ${x} ${y}`);
              pathEl.style.opacity = showHUD ? opacityVal.toString() : "0";
              pathEl.style.display = showHUD ? "block" : "none";
            }
            
            if (labelEl) {
              labelEl.style.transform = `translate(${lx}px, ${ly}px)`;
              labelEl.style.opacity = showHUD ? opacityVal.toString() : "0";
              labelEl.style.display = showHUD ? "block" : "none";
              
              const textValNode = labelEl.querySelector(".hud-val-num");
              if (textValNode) {
                textValNode.textContent = `${Math.round(activeVal)}%`;
              }
            }
          }
        });
      }

      if (composerRef.current) {
        composerRef.current.render();
      } else {
        renderer.render(scene, camera);
      }
    };

    animate();

    // Clean up
    return () => {
      cancelAnimationFrame(animationFrameRef.current || 0);
      resizeObserver.disconnect();
      geometry.dispose();
      material.dispose();
      particleGeometry.dispose();
      particlesMaterial.dispose();
      if (rendererRef.current && rendererRef.current.domElement) {
        rendererRef.current.dispose();
      }
    };
  }, [autoPlayBeat]); // Reset scene logic when autoPlayBeat shifts since it alters the loop configuration

  return (
    <div className="relative w-full h-[330px] sm:h-[480px] lg:h-[520px] rounded-2xl overflow-hidden bg-black border border-white/5 shadow-2xl flex items-center justify-center">
      {/* Absolute visual ambient backing */}
      <div className="absolute inset-0 bg-radial-[circle_at_center,rgba(5,5,15,0.7)_0%,rgba(0,0,0,1)_100%] pointer-events-none" />

      {/* Grid lines simulating a viewport laboratory scanner */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      {/* Diagnostics / Compass interface corners */}
      <div className="absolute top-4 left-6 pointer-events-none font-mono text-[9px] text-[#00F2FF] tracking-widest flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-[#00F2FF] animate-pulse" />
        <span className="opacity-80">CORE.SHADERS_SPECTROMETER // STATUS: ONLINE</span>
      </div>
      <div className="absolute top-4 right-6 pointer-events-none font-mono text-[9px] text-zinc-500 tracking-widest">
        <span>FRMT // 60FPS ATTACHED</span>
      </div>

      <div className="absolute bottom-4 left-6 pointer-events-none font-mono text-[9px] text-zinc-500 tracking-widest hidden sm:flex flex-col gap-0.5">
        <span>X-RAD // {rotationCurrentRef.current.x.toFixed(3)} RAD</span>
        <span>Y-RAD // {rotationCurrentRef.current.y.toFixed(3)} RAD</span>
      </div>

      {/* Dynamic 3D projected HUD callouts matching the design illustration perfectly */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        <defs>
          {METRICS_LIST.map((m) => {
            const cfg = POLES_CONFIG[m.key];
            return (
              <marker
                key={m.key}
                id={`arrow-${m.key}`}
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="5"
                markerHeight="5"
                orient="auto-start-reverse"
              >
                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill={cfg?.color || "#fff"} />
              </marker>
            );
          })}
        </defs>
        {METRICS_LIST.map((m) => {
          const cfg = POLES_CONFIG[m.key];
          return (
            <path
              key={m.key}
              id={`hud-path-${m.key}`}
              fill="none"
              stroke={cfg?.color || "#fff"}
              strokeWidth="1.2"
              strokeDasharray="2 2"
              markerEnd={`url(#arrow-${m.key})`}
              className="transition-all duration-100 ease-out pointer-events-none"
              style={{ opacity: 0 }}
            />
          );
        })}
      </svg>

      {/* Sphere anchor point glow dots */}
      <div className="absolute inset-0 w-full h-full pointer-events-none overflow-hidden z-10">
        {METRICS_LIST.map((m) => {
          const cfg = POLES_CONFIG[m.key];
          return (
            <div
              key={m.key}
              id={`hud-dot-${m.key}`}
              className="absolute -left-1 -top-1 w-2 h-2 rounded-full pointer-events-none transition-all duration-100 ease-out"
              style={{
                backgroundColor: cfg?.color || "#fff",
                boxShadow: `0 0 10px ${cfg?.color || "#fff"}, 0 0 4px #fff`,
                opacity: 0,
              }}
            />
          );
        })}
      </div>

      {/* 3D-attached floating label containers */}
      <div className="absolute inset-0 w-full h-full pointer-events-none overflow-hidden z-20">
        {METRICS_LIST.map((m) => {
          const cfg = POLES_CONFIG[m.key];
          const isLeft = m.key === "valence" || m.key === "pacing" || m.key === "retention";
          return (
            <div
              key={m.key}
              id={`hud-label-${m.key}`}
              className="absolute -top-4.5 pointer-events-none transition-all duration-100 ease-out font-mono text-[10px]"
              style={{
                opacity: 0,
                color: cfg?.color || "#fff",
                left: 0,
                transform: "translate(0px, 0px)",
              }}
            >
              <div 
                className={`flex items-center gap-2 bg-black/60 backdrop-blur-md px-2 py-1 border border-white/10 rounded-lg shadow-lg ${
                  isLeft ? "-translate-x-full pr-2" : "pl-2"
                } transition-colors duration-200 hover:bg-black/90`}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cfg?.color }} />
                <span className="text-white font-medium tracking-wider uppercase text-[9px]">{m.name}</span>
                <span className="opacity-80 px-1 font-bold text-white bg-white/10 rounded px-1 text-[8px] hud-val-num">--%</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Core interactive viewport container (threejs) */}
      {webglError ? (
        <div className="flex flex-col items-center gap-4 text-center max-w-sm px-6">
          <AlertCircle className="w-12 h-12 text-[#FF3D00]" />
          <h3 className="text-white font-medium text-sm">Error de WebGL</h3>
          <p className="text-zinc-500 text-xs leading-relaxed">{webglError}</p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleMouseUp}
        />
      )}

      {/* Compact, glossy floating utility controls HUD */}
      <div className="absolute bottom-4 right-4 flex items-center bg-white/[0.03] backdrop-blur-md rounded-xl border border-white/10 p-1 gap-1 shadow-lg pointer-events-auto">
        <button
          onClick={() => setAutoRotate(!autoRotate)}
          className={`p-1.5 rounded-lg transition ${autoRotate ? "text-[#00F2FF] bg-white/5" : "text-zinc-500 hover:text-zinc-300"}`}
          title={autoRotate ? "Pausar Rotación Automática" : "Iniciar Rotación Automática"}
        >
          <RotateCcw className={`w-3.5 h-3.5 ${autoRotate ? "animate-[spin_20s_linear_infinite]" : ""}`} />
        </button>
        <div className="w-[1px] h-4 bg-white/10 mx-0.5" />
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition"
          title="Zoom +"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition"
          title="Zoom -"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleResetCamera}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition"
          title="Reajustar Cámara"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Floating hints */}
      <div className="absolute bottom-16 left-6 pointer-events-none hidden md:flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
        <Move className="w-3 h-3 text-zinc-400" />
        <span>Arrastra con el ratón para orbitar o explorar el shader</span>
      </div>
    </div>
  );
}
