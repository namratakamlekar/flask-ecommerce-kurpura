// Scroll animation: cards/tiles slide up when they appear on screen.
const revealItems = document.querySelectorAll(".trust, .card, .cat, .fest a, .hl-art, .why div, .rev");
if ("IntersectionObserver" in window && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      el.classList.add("in");
      observer.unobserve(el);
      setTimeout(() => { el.classList.remove("reveal", "in"); el.style.transitionDelay = ""; }, 1000);
    });
  }, { threshold: 0.15 });
  revealItems.forEach((el, i) => {
    el.classList.add("reveal");
    el.style.transitionDelay = (i % 4) * 90 + "ms";
    observer.observe(el);
  });
}
