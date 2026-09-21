import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function EarthCanvas3D({ selectedCoordinates }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 5, 14);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Earth Sphere
    const earthRadius = 4.5;
    const earthGeo = new THREE.SphereGeometry(earthRadius, 64, 64);

    // Create procedural high-contrast tactical Earth texture
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    // Deep ocean
    ctx.fillStyle = '#0a1426';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid latitude/longitude lines
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.15)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += 32) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Stylized landmasses (India & Eurasian land silhouette)
    ctx.fillStyle = '#142a4a';
    // India Subcontinent triangle representation
    ctx.beginPath();
    ctx.moveTo(680, 210); // North
    ctx.lineTo(730, 310); // East
    ctx.lineTo(660, 340); // South Kanyakumari
    ctx.lineTo(630, 260); // West Gujarat
    ctx.closePath();
    ctx.fill();

    // General Eurasia / Himalayas land mass
    ctx.beginPath();
    ctx.ellipse(650, 180, 180, 70, 0, 0, Math.PI * 2);
    ctx.fill();

    const earthTexture = new THREE.CanvasTexture(canvas);
    const earthMat = new THREE.MeshPhongMaterial({
      map: earthTexture,
      bumpScale: 0.05,
      specular: new THREE.Color('#00e5ff'),
      shininess: 15,
      wireframe: false
    });

    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    // Orient globe towards Indian subcontinent
    earthMesh.rotation.y = -1.2;
    earthMesh.rotation.x = 0.3;
    scene.add(earthMesh);

    // Atmospheric Glow Outer Shell
    const atmoGeo = new THREE.SphereGeometry(earthRadius * 1.05, 48, 48);
    const atmoMat = new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
          gl_FragColor = vec4(0.0, 0.89, 1.0, 1.0) * intensity * 0.7;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true
    });
    const atmoMesh = new THREE.Mesh(atmoGeo, atmoMat);
    scene.add(atmoMesh);

    // Orbital Path Ring
    const orbitRadius = 6.2;
    const orbitCurve = new THREE.EllipseCurve(0, 0, orbitRadius, orbitRadius * 0.7, 0, 2 * Math.PI, false, 0);
    const orbitPoints = orbitCurve.getPoints(100);
    const orbitGeo = new THREE.BufferGeometry().setFromPoints(
      orbitPoints.map(p => new THREE.Vector3(p.x, p.y * 0.4, p.y))
    );
    const orbitMat = new THREE.LineBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.45
    });
    const orbitLine = new THREE.Line(orbitGeo, orbitMat);
    orbitLine.rotation.x = Math.PI / 4;
    scene.add(orbitLine);

    // Reconnaissance Satellite Object
    const satGroup = new THREE.Group();
    // Satellite main bus
    const satBusGeo = new THREE.BoxGeometry(0.3, 0.3, 0.5);
    const satBusMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.8, roughness: 0.2 });
    const satBus = new THREE.Mesh(satBusGeo, satBusMat);
    satGroup.add(satBus);

    // Solar panels
    const panelGeo = new THREE.BoxGeometry(1.2, 0.02, 0.35);
    const panelMat = new THREE.MeshStandardMaterial({ color: 0x0055ff, metalness: 0.9, roughness: 0.1 });
    const panels = new THREE.Mesh(panelGeo, panelMat);
    satGroup.add(panels);

    // Antenna dish
    const dishGeo = new THREE.ConeGeometry(0.18, 0.1, 16);
    const dishMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.position.set(0, 0.2, 0);
    dish.rotation.x = Math.PI;
    satGroup.add(dish);

    scene.add(satGroup);

    // Tactical Target Pins on Globe
    const pins = [
      { name: "Galwan", lat: 34.2, lng: 77.8, color: 0x00e5ff },
      { name: "Doklam", lat: 27.3, lng: 88.9, color: 0x10b981 },
      { name: "Sir Creek", lat: 23.7, lng: 68.1, color: 0xf59e0b }
    ];

    pins.forEach(pin => {
      const phi = (90 - pin.lat) * (Math.PI / 180);
      const theta = (pin.lng + 180) * (Math.PI / 180);
      const x = -(earthRadius * Math.sin(phi) * Math.cos(theta));
      const z = earthRadius * Math.sin(phi) * Math.sin(theta);
      const y = earthRadius * Math.cos(phi);

      const pinGeo = new THREE.SphereGeometry(0.12, 12, 12);
      const pinMat = new THREE.MeshBasicMaterial({ color: pin.color });
      const pinMesh = new THREE.Mesh(pinGeo, pinMat);
      pinMesh.position.set(x, y, z);
      earthMesh.add(pinMesh);

      // Pulse ring around pin
      const ringGeo = new THREE.RingGeometry(0.16, 0.22, 24);
      const ringMat = new THREE.MeshBasicMaterial({ color: pin.color, side: THREE.DoubleSide, transparent: true, opacity: 0.7 });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.set(x * 1.01, y * 1.01, z * 1.01);
      ringMesh.lookAt(x * 2, y * 2, z * 2);
      earthMesh.add(ringMesh);
    });

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 2.2);
    sunLight.position.set(12, 8, 10);
    scene.add(sunLight);

    const cyanRimLight = new THREE.PointLight(0x00e5ff, 3, 20);
    cyanRimLight.position.set(-8, -4, 5);
    scene.add(cyanRimLight);

    // Interactive Drag Rotation
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const onMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      earthMesh.rotation.y += deltaX * 0.005;
      earthMesh.rotation.x += deltaY * 0.005;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => { isDragging = false; };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Animation Loop
    let angle = 0;
    let reqId;

    const animate = () => {
      reqId = requestAnimationFrame(animate);

      // Slow idle planetary rotation
      if (!isDragging) {
        earthMesh.rotation.y += 0.0012;
      }

      // Orbiting satellite translation
      angle += 0.015;
      const sx = Math.cos(angle) * orbitRadius;
      const sz = Math.sin(angle) * (orbitRadius * 0.7);
      const sy = Math.sin(angle) * 1.5;

      satGroup.position.set(sx, sy, sz);
      satGroup.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(reqId);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('resize', onResize);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div className="relative w-full h-[450px] sm:h-[520px] rounded-sm overflow-hidden bg-[#070e1b]/80 border border-[#1e293b] flex items-center justify-center">
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
      
      {/* HUD Reticle Overlay */}
      <div className="absolute top-3 left-3 font-mono text-[10px] text-[#00e5ff] bg-[#070e1b]/90 px-2 py-1 border border-[#1e293b] rounded-sm pointer-events-none">
        INTERACTIVE 3D GLOBE // DRAG TO ROTATE
      </div>
      <div className="absolute bottom-3 right-3 font-mono text-[10px] text-[#94a3b8] bg-[#070e1b]/90 px-2 py-1 border border-[#1e293b] rounded-sm pointer-events-none">
        ORBIT VELOCITY: 7.62 KM/S • ALT: 540 KM
      </div>
    </div>
  );
}
