/**
 * AutoQuiz Minimalist 3D Technical Graphics Engine
 * Lightweight, hardware-accelerated 3D geometric visualizations.
 * Includes:
 *  1. Header / Welcome Isometric Knowledge Polyhedron
 *  2. Interactive 3D Mastery Trophy Gem
 */

(function () {
  'use strict';

  window.ThreeElements = {
    init: initEngine,
    renderMasteryTrophy: renderMasteryTrophy
  };

  let heroRenderer, heroScene, heroCamera, heroMesh, heroWire;
  let mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  let isTabVisible = true;

  document.addEventListener("DOMContentLoaded", () => {
    initEngine();
  });

  document.addEventListener("visibilitychange", () => {
    isTabVisible = !document.hidden;
  });

  function initEngine() {
    if (typeof THREE === "undefined") return;
    initHeroPrism();
    setupMouseTracking();
    window.addEventListener("resize", onWindowResize);
  }

  // --- 1. Minimalist 3D Wireframe Knowledge Prism ---
  function initHeroPrism() {
    const container = document.getElementById("hero-3d-prism-canvas");
    if (!container) return;

    const w = container.clientWidth || 140;
    const h = container.clientHeight || 140;

    heroScene = new THREE.Scene();
    heroCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    heroCamera.position.z = 4.2;

    heroRenderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance"
    });
    heroRenderer.setSize(w, h);
    heroRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = "";
    container.appendChild(heroRenderer.domElement);

    // Faceted technical polyhedron (Dodecahedron)
    const geometry = new THREE.DodecahedronGeometry(1.35, 0);

    // Solid inner facet
    const material = new THREE.MeshBasicMaterial({
      color: 0x1f242d,
      wireframe: false,
      transparent: true,
      opacity: 0.85
    });
    heroMesh = new THREE.Mesh(geometry, material);
    heroScene.add(heroMesh);

    // Clean outer technical wireframe
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x0969da,
      wireframe: true,
      transparent: true,
      opacity: 0.95
    });
    heroWire = new THREE.Mesh(geometry, wireMat);
    heroScene.add(heroWire);

    // Inner glowing core point
    const coreGeo = new THREE.OctahedronGeometry(0.5, 0);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      wireframe: true,
      transparent: true,
      opacity: 0.7
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    heroMesh.add(coreMesh);

    animateHeroPrism();
  }

  function animateHeroPrism() {
    requestAnimationFrame(animateHeroPrism);
    if (!isTabVisible || !heroRenderer || !heroMesh) return;

    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    heroMesh.rotation.y += 0.008;
    heroMesh.rotation.x += 0.005;

    // Interactive mouse parallax tilt
    heroMesh.rotation.z = mouse.x * 0.35;
    heroMesh.rotation.x += mouse.y * 0.01;

    heroWire.rotation.copy(heroMesh.rotation);
    heroRenderer.render(heroScene, heroCamera);
  }

  // --- 2. Interactive 3D Mastery Trophy Gem ---
  function renderMasteryTrophy(containerId) {
    if (typeof THREE === "undefined") return;
    const container = document.getElementById(containerId);
    if (!container) return;

    const w = 110;
    const h = 110;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 50);
    camera.position.z = 3.6;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // Gold & Azure 3D Icosahedron Trophy
    const geo = new THREE.IcosahedronGeometry(1.1, 0);
    const mat = new THREE.MeshBasicMaterial({
      color: 0x2ea043,
      wireframe: false,
      transparent: true,
      opacity: 0.3
    });
    const mesh = new THREE.Mesh(geo, mat);
    scene.add(mesh);

    const wireMat = new THREE.MeshBasicMaterial({
      color: 0xd29922,
      wireframe: true
    });
    const wire = new THREE.Mesh(geo, wireMat);
    scene.add(wire);

    function animate() {
      if (!document.getElementById(containerId)) {
        renderer.dispose();
        geo.dispose();
        mat.dispose();
        wireMat.dispose();
        return;
      }
      requestAnimationFrame(animate);
      mesh.rotation.y += 0.016;
      mesh.rotation.x += 0.009;
      wire.rotation.copy(mesh.rotation);
      renderer.render(scene, camera);
    }
    animate();
  }

  function setupMouseTracking() {
    window.addEventListener("mousemove", (e) => {
      mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    });
  }

  function onWindowResize() {
    if (!heroCamera || !heroRenderer) return;
    const container = document.getElementById("hero-3d-prism-canvas");
    if (!container) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    heroCamera.aspect = w / h;
    heroCamera.updateProjectionMatrix();
    heroRenderer.setSize(w, h);
  }

})();
