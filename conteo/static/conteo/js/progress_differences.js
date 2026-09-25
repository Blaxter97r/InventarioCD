(() => {
  const payload = document.querySelector("#code-differences-data");
  if (!payload) return;
  let scopes;
  try { scopes = JSON.parse(payload.textContent); } catch { return; }

  const makeEmpty = (container, message) => {
    container.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "progress-browser__empty";
    const icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "→";
    const text = document.createElement("p");
    text.textContent = message;
    empty.append(icon, text);
    container.append(empty);
  };

  document.querySelectorAll("[data-code-difference-explorer]").forEach((explorer) => {
    const scope = scopes.find((item) => item.name === explorer.dataset.scopeName);
    if (!scope) return;
    const labels = {
      group1: explorer.dataset.group1Label,
      group2: explorer.dataset.group2Label,
      group3: explorer.dataset.group3Label,
      leaf: explorer.dataset.leafLabel,
    };
    const state = { group1: null, group2: null, group3: null };
    const browser = explorer.querySelector("[data-difference-browser]");
    const search = explorer.querySelector("[data-difference-search]");
    const group1Count = explorer.querySelector("[data-difference-group1-count]");
    const locationCount = explorer.querySelector("[data-difference-location-count]");
    const secondaryPdfDownload = explorer.querySelector("[data-secondary-pdf-download]");
    const lists = Object.fromEntries(["group1", "group2", "group3", "locations"].map((key) => [key, explorer.querySelector(`[data-difference-list='${key}']`)]));
    const trail = Object.fromEntries(["group1", "group2", "group3"].map((key) => [key, explorer.querySelector(`[data-difference-trail='${key}']`)]));
    const labelValue = (label, value) => `${label} ${value}`;
    const normalizedLabel = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
    const stages = ["group1", "group2", "group3"];
    const shelfStage = stages.findIndex((key) => normalizedLabel(labels[key]) === "ESTANTE");
    const metricText = (item, stage) => {
      const stageIndex = stages.indexOf(stage);
      return shelfStage >= 0 && stageIndex >= shelfStage
        ? `${item.counted_codes}/${item.total_codes} contados`
        : `${item.missing_codes} códigos sin contar`;
    };
    const moveTo = (columnName) => {
      if (!window.matchMedia("(max-width: 900px)").matches) return;
      const column = explorer.querySelector(`[data-difference-column='${columnName}']`);
      if (column) browser.scrollTo({ left: column.offsetLeft, behavior: "smooth" });
    };
    const makeOption = (item, label, stage, selected, onSelect) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "progress-browser__option difference-browser__option";
      button.classList.toggle("is-selected", selected);
      button.classList.toggle("is-complete", item.missing_codes === 0);
      button.setAttribute("aria-pressed", String(selected));
      const heading = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = label;
      const alert = document.createElement("small");
      alert.textContent = metricText(item, stage);
      heading.append(name, alert);
      const meter = document.createElement("span");
      meter.className = "difference-browser__meter";
      const track = document.createElement("i");
      const fill = document.createElement("b");
      fill.style.width = `${item.total_codes ? Math.round(item.missing_codes / item.total_codes * 100) : 0}%`;
      track.append(fill);
      meter.append(track);
      button.append(heading, meter);
      button.addEventListener("click", onSelect);
      return button;
    };
    const updateTrail = () => {
      Object.keys(trail).forEach((key) => {
        trail[key].textContent = state[key] ? labelValue(labels[key], state[key].name) : `${labels[key]} —`;
        trail[key].disabled = !state[key];
      });
      if (secondaryPdfDownload) {
        secondaryPdfDownload.hidden = !state.group1;
        if (state.group1) {
          const params = new URLSearchParams({
            bodega: explorer.dataset.warehouse,
            piso: scope.name,
            pasillo: state.group1.name,
          });
          secondaryPdfDownload.href = `${explorer.dataset.secondaryPdfUrl}?${params}`;
          secondaryPdfDownload.textContent = `PDF diferencias · ${labels.group1} ${state.group1.name}`;
        }
      }
    };
    const renderLocations = () => {
      lists.locations.replaceChildren();
      if (!state.group3) {
        locationCount.textContent = "Elige una opción";
        makeEmpty(lists.locations, `Selecciona ${labels.group3.toLowerCase()}`);
        return;
      }
      locationCount.textContent = `${state.group3.locations.length} ubicaciones · ${metricText(state.group3, "group3")}`;
      state.group3.locations.forEach((location) => {
        const card = document.createElement(location.missing_codes ? "details" : "div");
        card.className = "difference-location-card";
        card.classList.toggle("is-clear", location.missing_codes === 0);
        const heading = document.createElement(location.missing_codes ? "summary" : "div");
        const data = document.createElement("span");
        const code = document.createElement("strong");
        code.textContent = location.code;
        const detail = document.createElement("small");
        detail.textContent = location.leaf_value ? `${labels.leaf} ${location.leaf_value} · Ubicación` : "Ubicación";
        data.append(code, detail);
        const alert = document.createElement("span");
        alert.className = `code-alert-count${location.missing_codes ? "" : " is-clear"}`;
        const alertStrong = document.createElement("strong");
        alertStrong.textContent = `${location.counted_codes}/${location.total_codes}`;
        alert.append(alertStrong, " contados");
        heading.append(data, alert);
        card.append(heading);
        if (location.missing_codes) {
          const codes = document.createElement("div");
          codes.className = "difference-location-card__codes";
          location.missing_code_list.forEach((value) => {
            const chip = document.createElement("span");
            chip.textContent = value;
            codes.append(chip);
          });
          card.append(codes);
        }
        lists.locations.append(card);
      });
    };
    const renderGroup3 = () => {
      lists.group3.replaceChildren();
      if (!state.group2) { makeEmpty(lists.group3, `Selecciona ${labels.group2.toLowerCase()}`); return; }
      state.group2.children.forEach((item) => lists.group3.append(makeOption(item, labelValue(labels.group3, item.name), "group3", state.group3?.name === item.name, () => {
        state.group3 = item; updateTrail(); renderGroup3(); renderLocations(); moveTo("locations");
      })));
    };
    const renderGroup2 = () => {
      lists.group2.replaceChildren();
      if (!state.group1) { makeEmpty(lists.group2, `Selecciona ${labels.group1.toLowerCase()}`); return; }
      state.group1.children.forEach((item) => lists.group2.append(makeOption(item, labelValue(labels.group2, item.name), "group2", state.group2?.name === item.name, () => {
        state.group2 = item; state.group3 = null; updateTrail(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group3");
      })));
    };
    const renderGroup1 = () => {
      const query = search.value.trim().toLowerCase();
      const filtered = scope.groups.filter((item) => item.name.toLowerCase().includes(query));
      lists.group1.replaceChildren();
      group1Count.textContent = `${filtered.length} opciones`;
      if (!filtered.length) { makeEmpty(lists.group1, "Sin resultados"); return; }
      filtered.forEach((item) => lists.group1.append(makeOption(item, labelValue(labels.group1, item.name), "group1", state.group1?.name === item.name, () => {
        state.group1 = item; state.group2 = null; state.group3 = null; updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group2");
      })));
    };
    explorer.querySelector("[data-difference-back]").addEventListener("click", () => {
      state.group1 = state.group2 = state.group3 = null;
      updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations();
      browser.scrollTo({ left: 0, behavior: "smooth" });
    });
    trail.group1.addEventListener("click", () => { state.group2 = state.group3 = null; updateTrail(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group2"); });
    trail.group2.addEventListener("click", () => { state.group3 = null; updateTrail(); renderGroup3(); renderLocations(); moveTo("group3"); });
    trail.group3.addEventListener("click", () => moveTo("locations"));
    search.addEventListener("input", renderGroup1);
    updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations();
  });
})();
