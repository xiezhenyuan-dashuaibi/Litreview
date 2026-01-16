import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

// 辅助函数：生成占位噪点纹理
const createPlaceholderTexture = () => {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 724;
  const ctx = canvas.getContext('2d')!;
  
  ctx.fillStyle = '#fdfbf7';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#e0e0e0';
  ctx.fillRect(40, 40, 300, 20);
  for(let i = 100; i < 700; i += 15) {
    const w = Math.random() * 300 + 100;
    ctx.fillRect(40, i, w, 6);
  }

  // 叠加四边淡淡的内阴影
  const vignWidth = 24;
  const topGrad = ctx.createLinearGradient(0, 0, 0, vignWidth);
  topGrad.addColorStop(0, 'rgba(0,0,0,0.12)');
  topGrad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = topGrad;
  ctx.fillRect(0, 0, canvas.width, vignWidth);

  const botGrad = ctx.createLinearGradient(0, canvas.height - vignWidth, 0, canvas.height);
  botGrad.addColorStop(0, 'rgba(0,0,0,0)');
  botGrad.addColorStop(1, 'rgba(0,0,0,0.12)');
  ctx.fillStyle = botGrad;
  ctx.fillRect(0, canvas.height - vignWidth, canvas.width, vignWidth);

  const leftGrad = ctx.createLinearGradient(0, 0, vignWidth, 0);
  leftGrad.addColorStop(0, 'rgba(0,0,0,0.10)');
  leftGrad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = leftGrad;
  ctx.fillRect(0, 0, vignWidth, canvas.height);

  const rightGrad = ctx.createLinearGradient(canvas.width - vignWidth, 0, canvas.width, 0);
  rightGrad.addColorStop(0, 'rgba(0,0,0,0)');
  rightGrad.addColorStop(1, 'rgba(0,0,0,0.10)');
  ctx.fillStyle = rightGrad;
  ctx.fillRect(canvas.width - vignWidth, 0, vignWidth, canvas.height);

  const texture = new THREE.CanvasTexture(canvas);
  texture.anisotropy = 16;
  return texture;
};

// 将图片绘制到 Canvas 并叠加边缘阴影，返回 CanvasTexture（同步占位，异步更新）
const loadVignetteTexture = (url: string) => {
  const canvas = document.createElement('canvas');
  const width = 1024;
  const height = Math.floor(width * 1.414);
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;

  // 初始底色
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  const tex = new THREE.CanvasTexture(canvas);
  tex.anisotropy = 16;

  const img = new Image();
  img.crossOrigin = '';
  img.onload = () => {
    // cover 等比填充
    const iw = img.width, ih = img.height;
    const scale = Math.max(width / iw, height / ih);
    const dw = iw * scale, dh = ih * scale;
    const dx = (width - dw) / 2, dy = (height - dh) / 2;
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(img, 0, 0, iw, ih, dx, dy, dw, dh);

    // 叠加四边淡阴影
    const vw = 32;
    const top = ctx.createLinearGradient(0, 0, 0, vw);
    top.addColorStop(0, 'rgba(0,0,0,0.12)');
    top.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = top; ctx.fillRect(0, 0, width, vw);

    const bottom = ctx.createLinearGradient(0, height - vw, 0, height);
    bottom.addColorStop(0, 'rgba(0,0,0,0)');
    bottom.addColorStop(1, 'rgba(0,0,0,0.12)');
    ctx.fillStyle = bottom; ctx.fillRect(0, height - vw, width, vw);

    const left = ctx.createLinearGradient(0, 0, vw, 0);
    left.addColorStop(0, 'rgba(0,0,0,0.10)');
    left.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = left; ctx.fillRect(0, 0, vw, height);

    const right = ctx.createLinearGradient(width - vw, 0, width, 0);
    right.addColorStop(0, 'rgba(0,0,0,0)');
    right.addColorStop(1, 'rgba(0,0,0,0.10)');
    ctx.fillStyle = right; ctx.fillRect(width - vw, 0, vw, height);

    tex.needsUpdate = true;
  };
  img.onerror = () => {
    // 如果加载失败，保持白底 + 阴影
    tex.needsUpdate = true;
  };
  img.src = url;
  return tex;
};

const ThreeScene: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 1. 初始化场景
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#F2F0E9');
    scene.fog = new THREE.FogExp2('#F2F0E9', 0.02);

    const camera = new THREE.PerspectiveCamera(35, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(-3.5, 7.5, 3);
    camera.lookAt(0, 0, -2.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = false;
    renderer.sortObjects = true;
    
    const currentMount = mountRef.current;
    if (currentMount) {
      currentMount.appendChild(renderer.domElement);
    }

    // 2. 灯光
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(8, 15, 8);
    dirLight.castShadow = false;
    scene.add(dirLight);
    
    const fillLight = new THREE.PointLight(0xffd1a3, 0.6);
    fillLight.position.set(-5, 2, -2);
    scene.add(fillLight);

    // 3. 创建纸张堆叠
    const papers: any[] = [];
    const paperCount = 12;
    const customSources: string[] = (window as any).__paperTextures || [];
    const paperTexture: THREE.CanvasTexture | null = (customSources.length || Object.values(import.meta.glob('../assets/paper-textures/*.{png,jpg,jpeg,webp}', { eager: true, as: 'url' })).length) ? null : createPlaceholderTexture();
    // 随构建打包的本地资源（src/assets/paper-textures/*）
    const textureModules = import.meta.glob('../assets/paper-textures/*.{png,jpg,jpeg,webp}', { eager: true, as: 'url' }) as Record<string, string>;
    const bundledSources: string[] = Object.values(textureModules);

    const paperWidth = 5.5;
    const paperHeight = paperWidth * 1.414;
    const paperGeo = new THREE.PlaneGeometry(paperWidth, paperHeight, 20, 20);
    
    const makeMaterial = (tex: THREE.Texture) => new THREE.MeshStandardMaterial({
      map: tex,
      color: 0xffffff,
      side: THREE.DoubleSide,
      roughness: 0.8,
      metalness: 0.0,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1,
    });

    // 生成纸张边缘淡淡的内阴影（伪影）
    const createEdgeVignetteTexture = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = Math.floor(canvas.width * 1.414);
      const ctx = canvas.getContext('2d')!;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 顶部渐变
      const topGrad = ctx.createLinearGradient(0, 0, 0, 24);
      topGrad.addColorStop(0, 'rgba(0,0,0,0.12)');
      topGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = topGrad;
      ctx.fillRect(0, 0, canvas.width, 24);

      // 底部渐变
      const botGrad = ctx.createLinearGradient(0, canvas.height - 24, 0, canvas.height);
      botGrad.addColorStop(0, 'rgba(0,0,0,0)');
      botGrad.addColorStop(1, 'rgba(0,0,0,0.12)');
      ctx.fillStyle = botGrad;
      ctx.fillRect(0, canvas.height - 24, canvas.width, 24);

      // 左右渐变
      const leftGrad = ctx.createLinearGradient(0, 0, 24, 0);
      leftGrad.addColorStop(0, 'rgba(0,0,0,0.10)');
      leftGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = leftGrad;
      ctx.fillRect(0, 0, 24, canvas.height);

      const rightGrad = ctx.createLinearGradient(canvas.width - 24, 0, canvas.width, 0);
      rightGrad.addColorStop(0, 'rgba(0,0,0,0)');
      rightGrad.addColorStop(1, 'rgba(0,0,0,0.10)');
      ctx.fillStyle = rightGrad;
      ctx.fillRect(canvas.width - 24, 0, 24, canvas.height);

      const tex = new THREE.CanvasTexture(canvas);
      tex.anisotropy = 16;
      return tex;
    };
    const vignetteTex = createEdgeVignetteTexture();

    const stackCenter = new THREE.Vector3(1.2, 0, 0);

    for (let i = 0; i < paperCount; i++) {
      const src = bundledSources.length
        ? bundledSources[i % bundledSources.length]
        : (customSources.length ? customSources[i % customSources.length] : null);
      const tex = src ? loadVignetteTexture(src) : (paperTexture as THREE.Texture);
      const mesh = new THREE.Mesh(paperGeo, makeMaterial(tex));
      
      const stackHeight = i * 0.05;

      const initialPos = new THREE.Vector3(
        stackCenter.x + (Math.random() - 0.3) * 2.2,
        stackCenter.y + stackHeight,
        stackCenter.z + (Math.random() - 0.5) * 1.5 - 2.0
      );
      
      const initialRot = new THREE.Euler(
        -Math.PI / 2,
        0,
        (Math.random() - 0.5) * 0.6
      );

      mesh.position.copy(initialPos);
      mesh.rotation.copy(initialRot);
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      // 控制渲染顺序：保证越靠上的纸张越后绘制，从而遮挡下面的阴影层
      mesh.renderOrder = i * 2;
      
      scene.add(mesh);


      papers.push({
        mesh,
        initialPos: initialPos.clone(),
        initialRot: initialRot.clone(),
        targetPos: initialPos.clone(),
        targetRot: initialRot.clone(),
        randomOffset: Math.random() * 100,
        isRemoved: false,
      });
    }

    // 地面
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(50, 50),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.0 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    ground.receiveShadow = true;
    scene.add(ground);

    // 4. 交互逻辑状态机
    let mouse = new THREE.Vector2(0, 0);
    let hasMouse = false;
    const raycaster = new THREE.Raycaster();
    const planeY = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

    let activeIndex = paperCount - 1;
    let removedCount = 0;
    const maxSwitches = 4;
    let lastTriggerTime = 0;
    const cooldown = 6.0;
    let actionStep = 0; // 0:移动, 1:移动, 2:切换(翻页)

    const onMouseMove = (event: MouseEvent) => {
      hasMouse = true;
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    document.addEventListener('mousemove', onMouseMove);

    // 5. 动画循环
    const clock = new THREE.Clock();
    const windSourceTarget = new THREE.Vector3();

    const animate = () => {
      requestAnimationFrame(animate);
      const time = clock.getElapsedTime();
      
      // 相机在初始时保持静止，仅在用户移动鼠标后微动
      if (hasMouse) {
        camera.position.x += (mouse.x * 0.1 - camera.position.x) * 0.05;
      }
      camera.lookAt(0, 0, -2.5);

      // 计算鼠标投影点
      raycaster.setFromCamera(mouse, camera);
      const hit = raycaster.ray.intersectPlane(planeY, windSourceTarget);
      const mousePos3D = hit ? windSourceTarget : null;

      // 遍历所有纸张进行渲染更新
      papers.forEach((paper, index) => {
        // 逻辑处理
        
        // 只有当前最顶层的纸张才进行交互检测
        if (index === activeIndex && mousePos3D) {
            const dist = mousePos3D.distanceTo(paper.mesh.position);
            const triggerRadius = 3.0;

            // 检查冷却和距离
            if (dist < triggerRadius && (time - lastTriggerTime > cooldown)) {
                
                // 触发交互！
                lastTriggerTime = time;
                
                // 固定序列：移动 → 移动 → 切换，最多切换4次
                const shouldSwitch = (actionStep % 3 === 2) && (removedCount < maxSwitches);
                actionStep = (actionStep + 1) % 3;

                if (shouldSwitch) {
                    // 效果A：吹走翻页
                    removedCount++;
                    activeIndex--;
                    paper.isRemoved = true;

                    // 计算吹走的方向
                    const flyDir = new THREE.Vector3(
                        (Math.random() - 0.5) * 5 + 5,
                        5,
                        (Math.random() - 0.5) * 5
                    );
                    
                    // 设置一个新的遥远的目标位置
                    paper.targetPos.add(flyDir);
                    // 疯狂旋转
                    paper.targetRot.x += Math.random() * 2;
                    paper.targetRot.z += Math.random() * 2;

                } else {
                    // 效果B：水平推动
                    const pushDir = paper.mesh.position.clone().sub(mousePos3D).normalize();
                    pushDir.y = 0;
                    
                    paper.targetPos.add(pushDir.multiplyScalar(0.8));
                    paper.targetRot.z += (Math.random() - 0.5) * 0.2;
                }
            }
        }

        // 物理更新
        
        // 如果是被移除的纸张，让它继续飘远一点
        if (paper.isRemoved) {
             paper.targetPos.y += 0.02;
             paper.targetPos.x += 0.02;
        }

        // 最终位置计算
        let finalX = paper.targetPos.x;
        let finalY = paper.targetPos.y;
        let finalZ = paper.targetPos.z;

        // 叠加呼吸
        if (!paper.isRemoved) {
            finalY += Math.sin(time * 1.5 + paper.randomOffset) * 0.005;
        }

        // 平滑插值更新 Mesh
        const lerpSpeed = 0.08;
        paper.mesh.position.x += (finalX - paper.mesh.position.x) * lerpSpeed;
        paper.mesh.position.y += (finalY - paper.mesh.position.y) * lerpSpeed;
        paper.mesh.position.z += (finalZ - paper.mesh.position.z) * lerpSpeed;
        
        paper.mesh.rotation.x += (paper.targetRot.x - paper.mesh.rotation.x) * lerpSpeed;
        paper.mesh.rotation.y += (paper.targetRot.y - paper.mesh.rotation.y) * lerpSpeed;
        paper.mesh.rotation.z += (paper.targetRot.z - paper.mesh.rotation.z) * lerpSpeed;
      });

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('mousemove', onMouseMove);
      if (currentMount) {
        currentMount.removeChild(renderer.domElement);
      }
      renderer.dispose();
      if (paperTexture) paperTexture.dispose();
    };
  }, []);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} />;
};

export default ThreeScene;
