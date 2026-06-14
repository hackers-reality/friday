import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function Orb({ pulse = 0 }) {
  const meshRef = useRef();
  const glowRef = useRef();
  const ringRef1 = useRef();
  const ringRef2 = useRef();
  const ringRef3 = useRef();
  const particlesRef = useRef();

  const particleGeometry = useMemo(() => {
    const count = 200;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.5 + Math.random() * 0.5;
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geom;
  }, []);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const p = 1 + pulse * 0.3;

    if (meshRef.current) {
      meshRef.current.rotation.y = t * 0.2;
      meshRef.current.rotation.x = Math.sin(t * 0.3) * 0.1;
      const scale = p * (1 + Math.sin(t * 2) * 0.05);
      meshRef.current.scale.setScalar(scale);
    }

    if (glowRef.current) {
      glowRef.current.rotation.y = -t * 0.1;
      const glowScale = p * (1.3 + Math.sin(t * 1.5) * 0.1);
      glowRef.current.scale.setScalar(glowScale);
    }

    if (ringRef1.current) {
      ringRef1.current.rotation.x = t * 0.5;
      ringRef1.current.rotation.z = t * 0.3;
    }
    if (ringRef2.current) {
      ringRef2.current.rotation.y = t * 0.4;
      ringRef2.current.rotation.x = t * 0.2;
    }
    if (ringRef3.current) {
      ringRef3.current.rotation.z = t * 0.6;
      ringRef3.current.rotation.y = -t * 0.3;
    }

    if (particlesRef.current) {
      particlesRef.current.rotation.y = t * 0.05;
      particlesRef.current.rotation.x = t * 0.03;
    }
  });

  return (
    <group>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1, 8]} />
        <meshStandardMaterial
          color="#00d4ff"
          emissive="#0066ff"
          emissiveIntensity={0.8 + pulse * 0.5}
          wireframe
          transparent
          opacity={0.6}
        />
      </mesh>

      <mesh ref={glowRef}>
        <icosahedronGeometry args={[1, 4]} />
        <meshStandardMaterial
          color="#0088ff"
          emissive="#0044aa"
          emissiveIntensity={1.2 + pulse * 0.8}
          transparent
          opacity={0.15}
          side={THREE.BackSide}
        />
      </mesh>

      <mesh ref={ringRef1}>
        <torusGeometry args={[1.8, 0.01, 16, 100]} />
        <meshStandardMaterial color="#00d4ff" emissive="#00d4ff" emissiveIntensity={1} transparent opacity={0.4} />
      </mesh>

      <mesh ref={ringRef2}>
        <torusGeometry args={[2.0, 0.008, 16, 100]} />
        <meshStandardMaterial color="#0088ff" emissive="#0088ff" emissiveIntensity={0.8} transparent opacity={0.3} />
      </mesh>

      <mesh ref={ringRef3}>
        <torusGeometry args={[2.2, 0.005, 16, 100]} />
        <meshStandardMaterial color="#0044ff" emissive="#0044ff" emissiveIntensity={0.6} transparent opacity={0.2} />
      </mesh>

      <points ref={particlesRef} geometry={particleGeometry}>
        <pointsMaterial color="#00d4ff" size={0.02} transparent opacity={0.6} sizeAttenuation />
      </points>

      <pointLight position={[0, 0, 0]} color="#0088ff" intensity={2 + pulse * 3} distance={10} />
      <pointLight position={[0, 0, 0]} color="#00d4ff" intensity={1 + pulse * 2} distance={8} />
    </group>
  );
}
