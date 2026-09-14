(() => {
  const body = document.body;
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const closeButton = document.querySelector("[data-sidebar-close]");
  const navigation = document.querySelector(".sidebar-nav");
  const desktopQuery = window.matchMedia("(min-width: 901px)");
  const storageKey = "inventario-sidebar-collapsed";
  const scrollStorageKey = "inventario-sidebar-scroll";

  if (!toggle) return;

  const updateAccessibility = () => {
    const isOpen = desktopQuery.matches
      ? !body.classList.contains("sidebar-collapsed")
      : body.classList.contains("sidebar-mobile-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "Ocultar menú lateral" : "Mostrar menú lateral");
  };

  const restoreDesktopState = () => {
    if (desktopQuery.matches) {
      body.classList.toggle("sidebar-collapsed", localStorage.getItem(storageKey) === "true");
      body.classList.remove("sidebar-mobile-open");
    } else {
      body.classList.remove("sidebar-collapsed");
    }
    updateAccessibility();
  };

  const saveScrollPosition = () => {
    if (navigation) sessionStorage.setItem(scrollStorageKey, String(navigation.scrollTop));
  };

  const restoreScrollPosition = () => {
    if (!navigation) return;
    const savedPosition = Number(sessionStorage.getItem(scrollStorageKey));
    if (Number.isFinite(savedPosition) && savedPosition >= 0) {
      navigation.scrollTop = savedPosition;
      requestAnimationFrame(() => { navigation.scrollTop = savedPosition; });
    }
  };

  toggle.addEventListener("click", () => {
    if (desktopQuery.matches) {
      const collapsed = body.classList.toggle("sidebar-collapsed");
      localStorage.setItem(storageKey, String(collapsed));
    } else {
      body.classList.toggle("sidebar-mobile-open");
    }
    updateAccessibility();
  });

  closeButton?.addEventListener("click", () => {
    body.classList.remove("sidebar-mobile-open");
    updateAccessibility();
  });

  navigation?.addEventListener("scroll", saveScrollPosition, { passive: true });
  navigation?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", saveScrollPosition);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      body.classList.remove("sidebar-mobile-open");
      updateAccessibility();
    }
  });

  desktopQuery.addEventListener("change", restoreDesktopState);
  restoreDesktopState();
  restoreScrollPosition();
})();
