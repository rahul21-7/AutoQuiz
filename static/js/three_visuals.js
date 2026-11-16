/**
 * AutoQuiz 3D Visuals & Interactive Graphics Engine
 * Powered by Three.js & Modern GPU-Accelerated WebGL.
 * Features:
 *  1. Interactive 3D Synaptic Constellation & Floating Knowledge Graph (Background)
 *  2. 3D Holographic AI Core (Hero Widget)
 *  3. 3D Particle Celebration Vortex on 100% Mastery
 *  4. Physics-based 3D Card Hover Tilt with Dynamic Specular Glare
 */

(function () {
  'use strict';

  // Global visual controller namespace
  window.ThreeVisuals = {
    init: initVisuals,
    triggerMasteryExplosion: triggerMasteryExplosion,
    triggerRemediationPulse: triggerRemediationPulse,
    refresh3DTilt: setupCardTilt
  };

  let bgRenderer, bgScene, bgCamera;
  let bgPoints, bgLines, bgDust;
  let heroRenderer, heroScene, heroCamera, heroCoreGroup;
  let mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  let celebrationParticles = null;
  let isTabActive = true;

  document.addEventListener("DOMContentLoaded", () => {
    initVisuals();
  });

  document.addEventListener("visibilitychange", () => {
    isTabActive = !document.hidden;
  });

  function initVisuals() {
    if (typeof THREE === "undefined") {
      console.warn("Three.js not detected; activating CSS 3D fallbacks.");
      setupCardTilt();
      return;
    }

    initBackgroundScene();
    initHeroCore();
    setupCardTilt();
    setupMouseTracking();

    window.addEventListener("resize", onWindowResize);
  }

  // --- 1. Background 3D Synaptic Constellation ---
  function initBackgroundScene() {
    const canvas = document.getElementById("bg-3d-canvas");
    if (!canvas) return;

    bgScene = new THREE.Scene();
    bgScene.fog = new THREE.FogExp2(0x070b14, 0.0018);

    const width = window.innerWidth;
    const height = window.innerHeight;

    bgCamera = new THREE.PerspectiveCamera(55, width / height, 1, 2000);
    bgCamera.position.z = 700;

    bgRenderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance"
    });
    bgRenderer.setSize(width, height);
    bgRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // A. Knowledge Graph Nodes
    const nodeCount = 90;
    const nodeGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(nodeCount * 3);
    const colors = new Float32Array(nodeCount * 3);

    const palette = [
      new THREE.Color(0x38bdf8), // Cyan
      new THREE.Color(0x818cf8), // Indigo
      new THREE.Color(0xc084fc), // Purple
      new THREE.Color(0x34d399)  // Emerald
    ];

    for (let i = 0; i < nodeCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 1200;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 800;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 600;

      const col = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;
    }

    nodeGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    nodeGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const nodeMaterial = new THREE.PointsMaterial({
      size: 5,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });

    bgPoints = new THREE.Points(nodeGeometry, nodeMaterial);
    bgScene.add(bgPoints);

    // B. Synaptic Connecting Lines
    const linePositions = [];
    const lineColors = [];
    const maxDistance = 180;

    for (let i = 0; i < nodeCount; i++) {
      for (let j = i + 1; j < nodeCount; j++) {
        const dx = positions[i * 3] - positions[j * 3];
        const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
        const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < maxDistance) {
          linePositions.push(
            positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
            positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
          );

          // Alpha fade by distance
          const alpha = 1.0 - (dist / maxDistance);
          lineColors.push(
            0.2, 0.6, 0.9, alpha * 0.4,
            0.4, 0.3, 0.8, alpha * 0.4
          );
        }
      }
    }

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));

    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending
    });

    bgLines = new THREE.LineSegments(lineGeometry, lineMaterial);
    bgScene.add(bgLines);

    // C. Deep Atmospheric Dust
    const dustCount = 200;
    const dustGeometry = new THREE.BufferGeometry();
    const dustPositions = new Float32Array(dustCount * 3);

    for (let i = 0; i < dustCount * 3; i += 3) {
      dustPositions[i] = (Math.random() - 0.5) * 1600;
      dustPositions[i + 1] = (Math.random() - 0.5) * 1200;
      dustPositions[i + 2] = (Math.random() - 0.5) * 1000;
    }

    dustGeometry.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3));
    const dustMaterial = new THREE.PointsMaterial({
      size: 2.2,
      color: 0x64748b,
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending
    });

    bgDust = new THREE.Points(dustGeometry, dustMaterial);
    bgScene.add(bgDust);

    animateBackground();
  }

  function animateBackground() {
    requestAnimationFrame(animateBackground);
    if (!isTabActive || !bgRenderer) return;

    // Smooth inertia mouse lerping
    mouse.x += (mouse.targetX - mouse.x) * 0.04;
    mouse.y += (mouse.targetY - mouse.y) * 0.04;

    // Gentle constant rotation + mouse parallax
    if (bgPoints) {
      bgPoints.rotation.y += 0.0006;
      bgPoints.rotation.x = mouse.y * 0.12;
      bgPoints.rotation.y += mouse.x * 0.15;
    }
    if (bgLines) {
      bgLines.rotation.y = bgPoints.rotation.y;
      bgLines.rotation.x = bgPoints.rotation.x;
    }
    if (bgDust) {
      bgDust.rotation.y -= 0.0003;
      bgDust.rotation.x += 0.0001;
    }

    // Camera breathing
    const time = Date.now() * 0.001;
    bgCamera.position.x = mouse.x * 60;
    bgCamera.position.y = -mouse.y * 50 + Math.sin(time * 0.5) * 10;
    bgCamera.lookAt(bgScene.position);

    // Render active celebration particles if any
    updateCelebrationParticles();

    bgRenderer.render(bgScene, bgCamera);
  }

  // --- 2. Hero 3D Holographic AI Core ---
  function initHeroCore() {
    const container = document.getElementById("hero-3d-container");
    if (!container) return;

    heroScene = new THREE.Scene();
    const w = container.clientWidth || 240;
    const h = container.clientHeight || 240;

    heroCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    heroCamera.position.z = 4.2;

    heroRenderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true
    });
    heroRenderer.setSize(w, h);
    heroRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(heroRenderer.domElement);

    heroCoreGroup = new THREE.Group();
    heroScene.add(heroCoreGroup);

    // A. Outer Wireframe Polyhedron (Icosahedron)
    const icoGeo = new THREE.IcosahedronGeometry(1.4, 1);
    const icoWireMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.75
    });
    const icoMesh = new THREE.Mesh(icoGeo, icoWireMat);
    heroCoreGroup.add(icoMesh);

    // B. Inner Glowing Energy Core
    const coreGeo = new THREE.SphereGeometry(0.75, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x818cf8,
      wireframe: false,
      transparent: true,
      opacity: 0.4
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    heroCoreGroup.add(coreMesh);

    // Point Light inside the core
    const light = new THREE.PointLight(0x00f2fe, 2, 10);
    heroCoreGroup.add(light);

    // C. Orbiting Holographic Rings
    const ringGeo1 = new THREE.TorusGeometry(1.85, 0.018, 16, 100);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0xc084fc,
      transparent: true,
      opacity: 0.65
    });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
    ring1.rotation.x = Math.PI / 3;
    heroCoreGroup.add(ring1);

    const ringGeo2 = new THREE.TorusGeometry(2.05, 0.015, 16, 100);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x34d399,
      transparent: true,
      opacity: 0.5
    });
    const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
    ring2.rotation.y = Math.PI / 4;
    ring2.rotation.x = Math.PI / 6;
    heroCoreGroup.add(ring2);

    animateHeroCore();
  }

  function animateHeroCore() {
    requestAnimationFrame(animateHeroCore);
    if (!isTabActive || !heroRenderer || !heroCoreGroup) return;

    heroCoreGroup.rotation.y += 0.012;
    heroCoreGroup.rotation.x += 0.007;

    // Tilt slightly towards cursor
    heroCoreGroup.rotation.z = mouse.x * 0.4;

    const time = Date.now() * 0.003;
    const pulse = 1 + Math.sin(time) * 0.05;
    heroCoreGroup.scale.set(pulse, pulse, pulse);

    heroRenderer.render(heroScene, heroCamera);
  }

  // --- 3. 3D Particle Celebration Vortex on 100% Mastery ---
  function triggerMasteryExplosion() {
    if (!bgScene) return;

    const pCount = 350;
    const pGeo = new THREE.BufferGeometry();
    const pPositions = new Float32Array(pCount * 3);
    const pVelocities = [];
    const pColors = new Float32Array(pCount * 3);

    const goldPalette = [
      new THREE.Color(0xfbbf24), // Gold
      new THREE.Color(0x34d399), // Emerald
      new THREE.Color(0x38bdf8), // Cyan
      new THREE.Color(0xf43f5e)  // Rose
    ];

    for (let i = 0; i < pCount; i++) {
      pPositions[i * 3] = (Math.random() - 0.5) * 50;
      pPositions[i * 3 + 1] = (Math.random() - 0.5) * 50;
      pPositions[i * 3 + 2] = 200 + (Math.random() - 0.5) * 50;

      // Spherical explosion velocity
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const speed = 4 + Math.random() * 7;

      pVelocities.push({
        vx: speed * Math.sin(phi) * Math.cos(theta),
        vy: speed * Math.sin(phi) * Math.sin(theta) + 2, // Slight upward lift
        vz: speed * Math.cos(phi)
      });

      const col = goldPalette[Math.floor(Math.random() * goldPalette.length)];
      pColors[i * 3] = col.r;
      pColors[i * 3 + 1] = col.g;
      pColors[i * 3 + 2] = col.b;
    }

    pGeo.setAttribute("position", new THREE.BufferAttribute(pPositions, 3));
    pGeo.setAttribute("color", new THREE.BufferAttribute(pColors, 3));

    const pMat = new THREE.PointsMaterial({
      size: 7,
      vertexColors: true,
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending
    });

    const explosionPoints = new THREE.Points(pGeo, pMat);
    bgScene.add(explosionPoints);

    celebrationParticles = {
      points: explosionPoints,
      velocities: pVelocities,
      positions: pPositions,
      life: 1.0,
      decay: 0.009
    };
  }

  function updateCelebrationParticles() {
    if (!celebrationParticles) return;

    const p = celebrationParticles;
    p.life -= p.decay;

    if (p.life <= 0) {
      bgScene.remove(p.points);
      p.points.geometry.dispose();
      p.points.material.dispose();
      celebrationParticles = null;
      return;
    }

    const pos = p.positions;
    for (let i = 0; i < p.velocities.length; i++) {
      const v = p.velocities[i];
      pos[i * 3] += v.vx;
      pos[i * 3 + 1] += v.vy;
      pos[i * 3 + 2] += v.vz;

      // Gravity and air drag
      v.vy -= 0.06;
      v.vx *= 0.985;
      v.vy *= 0.985;
      v.vz *= 0.985;
    }

    p.points.geometry.attributes.position.needsUpdate = true;
    p.points.material.opacity = p.life;
  }

  function triggerRemediationPulse() {
    if (!bgLines) return;
    const origOpacity = bgLines.material.opacity;
    bgLines.material.opacity = 0.65;
    bgLines.material.color.setHex(0xfbbf24); // Amber pulse

    setTimeout(() => {
      if (bgLines) {
        bgLines.material.opacity = origOpacity;
        bgLines.material.color.setHex(0x38bdf8);
      }
    }, 600);
  }

  // --- 4. Interactive 3D Card Hover Tilt with Dynamic Specular Glare ---
  function setupCardTilt() {
    const tiltTargets = document.querySelectorAll(
      ".ui-card, .question-card, .option-label, .dropzone, .stat-card, .sample-chip"
    );

    tiltTargets.forEach(card => {
      if (card.dataset.tiltBound === "true") return;
      card.dataset.tiltBound = "true";

      // Add specular glare overlay element if not present
      let glare = card.querySelector(".card-glare");
      if (!glare) {
        glare = document.createElement("div");
        glare.className = "card-glare";
        card.appendChild(glare);
      }

      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -7; // Max -7 to 7 deg
        const rotateY = ((x - centerX) / centerX) * 7;

        card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px) scale3d(1.01, 1.01, 1.01)`;

        if (glare) {
          glare.style.opacity = "1";
          glare.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255, 255, 255, 0.12) 0%, transparent 70%)`;
        }
      });

      card.addEventListener("mouseleave", () => {
        card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)";
        if (glare) {
          glare.style.opacity = "0";
        }
      });
    });
  }

  function setupMouseTracking() {
    window.addEventListener("mousemove", (e) => {
      mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    });
  }

  function onWindowResize() {
    if (!bgCamera || !bgRenderer) return;
    const w = window.innerWidth;
    const h = window.innerHeight;

    bgCamera.aspect = w / h;
    bgCamera.updateProjectionMatrix();
    bgRenderer.setSize(w, h);

    if (heroCamera && heroRenderer) {
      const container = document.getElementById("hero-3d-container");
      if (container) {
        const hw = container.clientWidth;
        const hh = container.clientHeight;
        heroCamera.aspect = hw / hh;
        heroCamera.updateProjectionMatrix();
        heroRenderer.setSize(hw, hh);
      }
    }
  }

})();

