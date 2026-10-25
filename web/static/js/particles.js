/**
 * Shomei Fluid Cursor-Reactive Particle Field
 * Stratified Grid Distribution for perfectly uniform, balanced coverage across
 * the entire screen (left, center, right, top, and bottom).
 * Physics-based spring and damping model with shiny, luminous emerald hover effects.
 * Respects prefers-reduced-motion.
 */

(function () {
  const canvas = document.getElementById('canvas-particles');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return;

  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  const mouse = {
    x: -9999,
    y: -9999,
    radius: 230, // Interactive hover influence radius
    isActive: false,
  };

  const handlePointer = (clientX, clientY) => {
    mouse.x = clientX;
    mouse.y = clientY;
    mouse.isActive = true;
  };

  window.addEventListener('mousemove', (e) => handlePointer(e.clientX, e.clientY));
  window.addEventListener('touchmove', (e) => {
    if (e.touches && e.touches.length > 0) {
      handlePointer(e.touches[0].clientX, e.touches[0].clientY);
    }
  }, { passive: true });

  const resetPointer = () => {
    mouse.isActive = false;
    mouse.x = -9999;
    mouse.y = -9999;
  };

  window.addEventListener('mouseleave', resetPointer);
  window.addEventListener('touchend', resetPointer);
  window.addEventListener('touchcancel', resetPointer);

  const particles = [];

  class SpringParticle {
    constructor(startX, startY) {
      this.originX = startX;
      this.originY = startY;
      this.x = startX;
      this.y = startY;
      this.vx = 0;
      this.vy = 0;
      this.driftX = (Math.random() - 0.5) * 0.22;
      this.driftY = (Math.random() - 0.5) * 0.22;

      // Refined resting size & opacity (little bit smaller, crisp & elegant)
      this.baseRadius = Math.random() * 0.8 + 1.1; // 1.1px - 1.9px
      this.baseAlpha = Math.random() * 0.20 + 0.32;  // 0.32 - 0.52
      this.springK = 0.024;
      this.damping = 0.88;

      // Interactive hover shine & scale
      this.hoverFactor = 0;
      this.sparklePhase = Math.random() * Math.PI * 2;
      this.sparkleSpeed = Math.random() * 0.005 + 0.003;
    }

    update(time) {
      if (prefersReducedMotion) return;

      // Ambient drift within local bounding cell
      this.originX += this.driftX;
      this.originY += this.driftY;
      if (this.originX < 10 || this.originX > width - 10) this.driftX *= -1;
      if (this.originY < 10 || this.originY > height - 10) this.driftY *= -1;

      // Cursor proximity calculation
      let targetHover = 0;
      if (mouse.isActive) {
        const dx = this.x - mouse.x;
        const dy = this.y - mouse.y;
        const dist = Math.hypot(dx, dy);

        if (dist < mouse.radius) {
          const proximity = 1 - dist / mouse.radius;
          targetHover = Math.pow(proximity, 1.1);

          // Gentle organic repulsion so particles orbit naturally
          if (dist > 0.1) {
            const force = proximity * 1.7;
            const angle = Math.atan2(dy, dx);
            this.vx += Math.cos(angle) * force;
            this.vy += Math.sin(angle) * force;
          }
        }
      }

      // Fast, smooth interpolation for hover scaling and shine
      this.hoverFactor += (targetHover - this.hoverFactor) * 0.18;

      // Spring force returning particle to origin anchor
      const springX = (this.originX - this.x) * this.springK;
      const springY = (this.originY - this.y) * this.springK;

      this.vx = (this.vx + springX) * this.damping;
      this.vy = (this.vy + springY) * this.damping;

      this.x += this.vx;
      this.y += this.vy;
    }

    draw(time) {
      ctx.save();

      if (this.hoverFactor > 0.02) {
        // --- HOVER STATE: Refined, radiant & shiny without being overly bulky ---
        const pulse = 0.92 + 0.08 * Math.sin(time * this.sparkleSpeed + this.sparklePhase);
        const currentRadius = (this.baseRadius + this.hoverFactor * 3.8) * pulse;

        // 1. Radiant luminous outer aura
        const outerAuraRadius = currentRadius * 3.4;
        const auraGrad = ctx.createRadialGradient(
          this.x, this.y, 0,
          this.x, this.y, outerAuraRadius
        );
        auraGrad.addColorStop(0, `rgba(255, 255, 255, ${0.98 * this.hoverFactor})`);
        auraGrad.addColorStop(0.2, `rgba(134, 239, 172, ${0.88 * this.hoverFactor})`); // mint glow
        auraGrad.addColorStop(0.5, `rgba(34, 197, 94, ${0.70 * this.hoverFactor})`);   // vivid emerald
        auraGrad.addColorStop(0.8, `rgba(21, 128, 61, ${0.26 * this.hoverFactor})`);   // deep forest
        auraGrad.addColorStop(1, 'rgba(21, 128, 61, 0)');

        ctx.beginPath();
        ctx.arc(this.x, this.y, outerAuraRadius, 0, Math.PI * 2);
        ctx.fillStyle = auraGrad;
        ctx.fill();

        // 2. Shiny emerald glow shadow
        ctx.shadowColor = `rgba(34, 197, 94, ${0.92 * this.hoverFactor})`;
        ctx.shadowBlur = 12 * this.hoverFactor;

        // Outer ring of the particle
        ctx.beginPath();
        ctx.arc(this.x, this.y, currentRadius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(22, 163, 74, ${0.95 * this.hoverFactor})`;
        ctx.fill();

        // 3. Glowing bright white specular core
        ctx.beginPath();
        ctx.arc(this.x, this.y, currentRadius * 0.68, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${0.98 * this.hoverFactor + 0.02})`;
        ctx.fill();

        // 4. Specular highlight glints
        if (this.hoverFactor > 0.25) {
          ctx.shadowBlur = 0;
          ctx.beginPath();
          ctx.arc(
            this.x - currentRadius * 0.32,
            this.y - currentRadius * 0.32,
            currentRadius * 0.24,
            0,
            Math.PI * 2
          );
          ctx.fillStyle = `rgba(255, 255, 255, ${1.0 * this.hoverFactor})`;
          ctx.fill();
        }
      } else {
        // --- REST STATE: Refined particles adapting to light/dark ---
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.baseRadius, 0, Math.PI * 2);
        ctx.fillStyle = isDark
          ? `rgba(235, 235, 230, ${this.baseAlpha * 0.45})`
          : `rgba(24, 24, 22, ${this.baseAlpha})`;
        ctx.fill();
      }

      ctx.restore();
    }
  }

  /**
   * Initializes particles using Stratified Grid Sampling across the full screen
   * This guarantees 100% equal distribution across all columns (left, center, right)
   * and all rows (top, middle, bottom) with no clumping or empty voids.
   */
  function initStratifiedParticles() {
    particles.length = 0;

    // Determine grid dimensions based on viewport aspect ratio
    const totalTarget = Math.max(80, Math.min(150, Math.floor((width * height) / 11500)));
    const cols = Math.max(10, Math.round(Math.sqrt(totalTarget * (width / height))));
    const rows = Math.max(7, Math.ceil(totalTarget / cols));

    const cellW = width / cols;
    const cellH = height / rows;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        // Place particle inside cell with controlled organic jitter
        const jitterX = (Math.random() - 0.5) * (cellW * 0.68);
        const jitterY = (Math.random() - 0.5) * (cellH * 0.68);
        const x = Math.max(12, Math.min(width - 12, (c + 0.5) * cellW + jitterX));
        const y = Math.max(12, Math.min(height - 12, (r + 0.5) * cellH + jitterY));

        particles.push(new SpringParticle(x, y));
      }
    }
  }

  initStratifiedParticles();

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    initStratifiedParticles();
  });

  function render(time) {
    ctx.clearRect(0, 0, width, height);

    // Uniform connection web across the entire screen
    const maxLinkDist = Math.max(110, Math.min(140, width / 12));

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.hypot(dx, dy);

        if (dist < maxLinkDist) {
          const maxHover = Math.max(particles[i].hoverFactor, particles[j].hoverFactor);
          const baseAlpha = (1 - dist / maxLinkDist) * 0.16;
          const lineAlpha = baseAlpha + maxHover * 0.45;

          ctx.save();
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);

          if (maxHover > 0.12) {
            ctx.strokeStyle = `rgba(34, 197, 94, ${lineAlpha})`;
            ctx.lineWidth = 1.0 + maxHover * 1.4;
            ctx.shadowColor = 'rgba(74, 222, 128, 0.85)';
            ctx.shadowBlur = 10 * maxHover;
          } else {
            ctx.strokeStyle = `rgba(22, 163, 74, ${baseAlpha})`;
            ctx.lineWidth = 0.85;
          }

          ctx.stroke();
          ctx.restore();
        }
      }
    }

    particles.forEach((p) => {
      p.update(time);
      p.draw(time);
    });

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
})();
