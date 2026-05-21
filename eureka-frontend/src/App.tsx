import { Canvas } from '@react-three/fiber'
import { OrbitControls, Sphere, MeshDistortMaterial } from '@react-three/drei'
import './App.css'

function Atom() {
  return (
    <Sphere visible args={[1, 100, 200]} scale={2}>
      <MeshDistortMaterial
        color="#8352FD"
        attach="material"
        distort={0.3}
        speed={1.5}
        roughness={0}
      />
    </Sphere>
  )
}

function App() {
  return (
    <div style={{ width: '100vw', height: '100vh', backgroundColor: '#111', margin: 0, padding: 0 }}>
      <div style={{ position: 'absolute', top: 20, left: 20, color: 'white', fontFamily: 'sans-serif', zIndex: 10 }}>
        <h1>EUREKA Phase 1</h1>
        <p>Interactive 3D Canvas Initialized.</p>
      </div>
      <Canvas>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        <OrbitControls />
        <Atom />
      </Canvas>
    </div>
  )
}

export default App
