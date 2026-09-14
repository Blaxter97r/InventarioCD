(() => {
  const storageKey = `inventario:avance:scroll:${window.location.pathname}`;
  const floorLinks = document.querySelectorAll("[data-progress-floor-link]");

  const rememberScrollPosition = () => {
    try {
      window.sessionStorage.setItem(storageKey, String(window.scrollY));
    } catch {
      // La navegacion debe continuar aunque el almacenamiento este deshabilitado.
    }
  };

  const restoreScrollPosition = () => {
    let savedPosition = null;

    try {
      savedPosition = window.sessionStorage.getItem(storageKey);
      window.sessionStorage.removeItem(storageKey);
    } catch {
      return;
    }

    if (savedPosition === null) return;

    const scrollPosition = Number.parseInt(savedPosition, 10);
    if (!Number.isFinite(scrollPosition)) return;

    window.requestAnimationFrame(() => {
      window.scrollTo({ top: scrollPosition, left: 0, behavior: "auto" });
    });
  };

  floorLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const opensInCurrentTab =
        event.button === 0 &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.shiftKey &&
        !event.altKey;

      if (opensInCurrentTab) rememberScrollPosition();
    });
  });

  restoreScrollPosition();
})();
