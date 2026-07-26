/* Light/dark theme toggle. Persists choice in localStorage. */
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("careerlens-theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const preferred = saved || (prefersDark ? "dark" : "light");

  root.setAttribute("data-theme", preferred);

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;

    updateLabel(preferred);

    btn.addEventListener("click", () => {
      const current = root.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("careerlens-theme", next);
      updateLabel(next);
    });
  });

  function updateLabel(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
  }
})();
