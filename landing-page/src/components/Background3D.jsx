import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as random from 'maath/random/dist/maath-random.esm';

const Stars = ({ speed = 0.05 }) => {
  const ref = useRef();
  const [sphere] = useState(() => random.inSphere(new Float32Array(4000), { radius: 1.5 }));
  useFrame((_, delta) => { if (ref.current) { ref.current.rotation.x -= delta * speed; ref.current.rotation.y -= delta * speed * 1.2; } });
  return <group rotation={[0, 0, Math.PI / 4]}><Points ref={ref} positions={sphere} stride={3} frustumCulled={false}><PointMaterial transparent color="#00d4ff" size={0.004} sizeAttenuation depthWrite={false} /></Points></group>;
};

export const Background3D = ({ isRunning }) => (
  <div style={{ position: 'fixed', inset: 0, zIndex: -1, background: '#050505' }}>
    <Canvas camera={{ position: [0, 0, 1] }}><Stars speed={isRunning ? 0.6 : 0.04} /></Canvas>
    <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 0%, transparent 30%, #050505 75%)' }} />
  </div>
);
