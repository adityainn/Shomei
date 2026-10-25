/**
 * Shomei Landing Page Interactions
 * Hotkey keyboard shortcuts, scroll-led step observer, and smooth anchors.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const targetEl = document.querySelector(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }
    });
  });

  // Sticky header blur transition on scroll
  const header = document.querySelector('.site-header');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 30) {
      header.style.boxShadow = '0 4px 20px rgba(24, 24, 22, 0.05)';
      header.style.background = 'rgba(250, 248, 245, 0.95)';
    } else {
      header.style.boxShadow = 'none';
      header.style.background = 'rgba(250, 248, 245, 0.85)';
    }
  });

  // Keyboard Hotkeys Navigation (Insomnia Reference Style)
  window.addEventListener('keydown', (e) => {
    // Ignore if typing in an input or textarea
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    const key = e.key.toLowerCase();
    const keyMap = {
      h: '#hero',
      s: '#systems',
      p: '#problem',
      d: '#discovery',
      i: '#investigation',
      r: '#remediation',
      v: '#verification',
    };

    if (key in keyMap) {
      e.preventDefault();
      const target = document.querySelector(keyMap[key]);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } else if (key === 'c') {
      e.preventDefault();
      window.location.href = '/dashboard';
    }
  });

  // Scroll-Spy for Step Indicators (01 to 05)
  const sections = [
    { id: 'problem', stepIndex: 0 },
    { id: 'discovery', stepIndex: 1 },
    { id: 'investigation', stepIndex: 2 },
    { id: 'remediation', stepIndex: 3 },
    { id: 'verification', stepIndex: 4 },
  ];

  const stepItems = document.querySelectorAll('.story-step-item');

  if (stepItems.length > 0 && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const sec = sections.find((s) => s.id === entry.target.id);
            if (sec !== undefined) {
              stepItems.forEach((item, idx) => {
                if (idx === sec.stepIndex) {
                  item.classList.add('active');
                } else {
                  item.classList.remove('active');
                }
              });
            }
          }
        });
      },
      { rootMargin: '-20% 0px -50% 0px' }
    );

    sections.forEach((sec) => {
      const el = document.getElementById(sec.id);
      if (el) observer.observe(el);
    });
  }
});
