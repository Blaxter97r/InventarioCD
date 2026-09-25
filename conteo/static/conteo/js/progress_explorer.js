(() => {
  const explorer = document.querySelector("[data-progress-explorer]");
  const payload = document.querySelector("#progress-explorer-data");
  if (!explorer || !payload) return;

  let group1Items;
  try { group1Items = JSON.parse(payload.textContent); } catch { return; }

  const labels = {
    scope: explorer.dataset.scopeLabel,
    group1: explorer.dataset.group1Label,
    group2: explorer.dataset.group2Label,
    group3: explorer.dataset.group3Label,
    leaf: explorer.dataset.leafLabel,
  };
  const browser = explorer.querySelector("[data-progress-browser]");
  const lists = {
    group1: explorer.querySelector("[data-group1-list]"),
    group2: explorer.querySelector("[data-group2-list]"),
    group3: explorer.querySelector("[data-group3-list]"),
    locations: explorer.querySelector("[data-location-list]"),
  };
  const search = explorer.querySelector("[data-group1-search]");
  const group1Count = explorer.querySelector("[data-group1-count]");
  const locationCount = explorer.querySelector("[data-location-count]");
  const trail = {
    group1: explorer.querySelector("[data-progress-trail='group1']"),
    group2: explorer.querySelector("[data-progress-trail='group2']"),
    group3: explorer.querySelector("[data-progress-trail='group3']"),
  };
  const state = { group1: null, group2: null, group3: null };
  const dialog = explorer.querySelector("[data-reconciliation-dialog]");
  const validationForm = explorer.querySelector("[data-validation-form]");
  const validationCheckbox = explorer.querySelector("[data-validation-checkbox]");
  const validationHelp = explorer.querySelector("[data-validation-help]");
  const validationFeedback = explorer.querySelector("[data-validation-feedback]");
  const rgeModificationControl = explorer.querySelector("[data-rge-modification-control]");
  const rgeModificationCheckbox = explorer.querySelector("[data-rge-modification-checkbox]");
  const validationUrl = explorer.dataset.validationUrl;
  const locationType = explorer.dataset.locationType;
  const restoredStateKey = `inventario:avance:explorador:${window.location.search}`;
  let currentLocation = null;
  const dialogFields = {
    title: explorer.querySelector("[data-reconciliation-title]"),
    path: explorer.querySelector("[data-reconciliation-path]"),
    alert: explorer.querySelector("[data-reconciliation-alert]"),
    status: explorer.querySelector("[data-reconciliation-status]"),
    message: explorer.querySelector("[data-reconciliation-message]"),
    expected: explorer.querySelector("[data-reconciliation-expected]"),
    found: explorer.querySelector("[data-reconciliation-found]"),
    missing: explorer.querySelector("[data-reconciliation-missing]"),
    products: explorer.querySelector("[data-reconciliation-products]"),
    empty: explorer.querySelector("[data-reconciliation-empty]"),
  };

  const pluralize = (amount, singular, plural) => `${amount} ${amount === 1 ? singular : plural}`;
  const labelValue = (label, value) => `${label} ${value}`;

  const setEmpty = (container, message, detail = "") => {
    container.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "progress-browser__empty";
    const icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "→";
    const text = document.createElement("p");
    text.textContent = message;
    empty.append(icon, text);
    if (detail) {
      const small = document.createElement("small");
      small.textContent = detail;
      empty.append(small);
    }
    container.append(empty);
  };

  const makeOption = (item, label, selected, onSelect) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "progress-browser__option";
    button.classList.toggle("is-selected", selected);
    button.classList.toggle("is-complete", item.pending === 0);
    button.setAttribute("aria-pressed", String(selected));
    const heading = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = label;
    const pending = document.createElement("small");
    pending.textContent = item.pending ? pluralize(item.pending, "pendiente", "pendientes") : "Completo";
    heading.append(name, pending);
    const progress = document.createElement("span");
    progress.className = "progress-browser__option-progress";
    const bar = document.createElement("i");
    const fill = document.createElement("b");
    fill.style.width = `${item.percentage}%`;
    bar.append(fill);
    const percentage = document.createElement("em");
    percentage.textContent = `${item.percentage}%`;
    progress.append(bar, percentage);
    button.append(heading, progress);
    button.addEventListener("click", onSelect);
    return button;
  };

  const moveTo = (columnName) => {
    if (!window.matchMedia("(max-width: 900px)").matches) return;
    const column = explorer.querySelector(`[data-browser-column='${columnName}']`);
    if (column) browser.scrollTo({ left: column.offsetLeft, behavior: "smooth" });
  };

  const updateTrail = () => {
    Object.keys(trail).forEach((key) => {
      trail[key].textContent = state[key] ? labelValue(labels[key], state[key].name) : `${labels[key]} —`;
      trail[key].disabled = !state[key];
    });
  };

  const messages = {
    counted: "La ubicación ya tiene registros en el conteo actual.",
    validated: "La ubicación fue revisada y validada por el personal asignado.",
    possible_location_error: "Todos los productos esperados aparecen registrados en otras ubicaciones. Podría tratarse de un escaneo incorrecto.",
    needs_review: "Algunos productos aparecen en otras ubicaciones y otros todavía no se localizaron.",
    not_located: "Los productos esperados no aparecen en ninguna ubicación del conteo actual.",
    no_rge: "Carga el RGE para comparar los productos teóricos contra el conteo.",
    no_reference: "El RGE vigente no asocia productos con esta ubicación.",
  };

  const appendCell = (row, content) => {
    const cell = document.createElement("td");
    if (content instanceof Node) cell.append(content); else cell.textContent = content;
    row.append(cell);
  };

  const openReconciliation = (location) => {
    currentLocation = location;
    dialogFields.title.textContent = location.code;
    dialogFields.path.textContent = location.path.map((item) => labelValue(item.label, item.value)).join(" · ");
    dialogFields.alert.className = `progress-reconciliation__alert is-${location.status}`;
    dialogFields.status.textContent = location.status_label;
    dialogFields.message.textContent = messages[location.status] || "Revisa esta ubicación.";
    dialogFields.expected.textContent = location.expected_products;
    dialogFields.found.textContent = location.found_elsewhere;
    dialogFields.missing.textContent = location.expected_products - location.found_elsewhere;
    dialogFields.products.replaceChildren();
    const table = dialogFields.products.closest("table");
    table.hidden = !location.products.length;
    dialogFields.empty.hidden = Boolean(location.products.length);
    validationForm.hidden = location.counted;
    validationCheckbox.checked = location.validated;
    validationCheckbox.disabled = false;
    const canModifyRge = locationType === "SECUNDARIO" && !location.counted;
    rgeModificationControl.hidden = !canModifyRge;
    rgeModificationCheckbox.checked = location.modify_rge;
    rgeModificationCheckbox.disabled = false;
    validationHelp.textContent = location.validated
      ? "Esta ubicación ya suma al avance. Desmarca el check si necesitas devolverla a pendientes."
      : "Marca este check cuando la ubicación ya fue revisada y se tomó una decisión. Se sumará al avance.";
    validationFeedback.textContent = "";
    location.products.forEach((product) => {
      const row = document.createElement("tr");
      const code = document.createElement("strong");
      code.textContent = product.code;
      appendCell(row, code);
      appendCell(row, product.expected_location);
      const status = document.createElement("span");
      status.className = product.counted_here || product.counted_elsewhere ? "reconciliation-status is-found" : "reconciliation-status is-missing";
      status.textContent = product.counted_here ? "Contado aquí" : (product.counted_elsewhere ? "Contado en otro lugar" : "No localizado");
      appendCell(row, status);
      const locations = document.createElement("div");
      locations.className = "progress-reconciliation__locations";
      if (product.counted_locations.length) {
        product.counted_locations.forEach((value) => {
          const tag = document.createElement("span");
          tag.textContent = value;
          locations.append(tag);
        });
      } else {
        const missing = document.createElement("small");
        missing.textContent = "No localizado";
        locations.append(missing);
      }
      appendCell(row, locations);
      dialogFields.products.append(row);
    });
    if (typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open", "");
  };

  const renderLocations = () => {
    lists.locations.replaceChildren();
    if (!state.group3) {
      locationCount.textContent = "Pendientes y contadas";
      setEmpty(lists.locations, `Selecciona ${labels.group3.toLowerCase()}`, "Aquí aparecerán las ubicaciones del recorrido.");
      return;
    }
    const locations = state.group3.locations || state.group3.pending_locations;
    locationCount.textContent = `${locations.length} ubicaciones · ${state.group3.pending} pendientes`;
    locations.forEach((location) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = `progress-location is-${location.status}`;
      const marker = document.createElement("span");
      marker.textContent = location.counted || location.validated ? "✓" : (["no_reference", "no_rge"].includes(location.status) ? "?" : "!");
      const data = document.createElement("div");
      const code = document.createElement("strong");
      code.textContent = location.code;
      const detail = document.createElement("small");
      const leaf = location.leaf_value ? `${labelValue(labels.leaf, location.leaf_value)} · ` : "";
      detail.textContent = location.counted
        ? `${leaf}ubicación contada`
        : (location.validated ? `${leaf}ubicación validada` : `${leaf}${location.expected_products} productos esperados`);
      data.append(code, detail);
      const status = document.createElement("b");
      status.textContent = location.status_label;
      row.append(marker, data, status);
      row.addEventListener("click", () => openReconciliation(location));
      lists.locations.append(row);
    });
  };

  const renderGroup3 = () => {
    lists.group3.replaceChildren();
    if (!state.group2) { setEmpty(lists.group3, `Selecciona ${labels.group2.toLowerCase()}`); return; }
    state.group2.bodies.forEach((item) => lists.group3.append(makeOption(item, labelValue(labels.group3, item.name), state.group3?.name === item.name, () => {
      state.group3 = item; updateTrail(); renderGroup3(); renderLocations(); moveTo("locations");
    })));
  };

  const renderGroup2 = () => {
    lists.group2.replaceChildren();
    if (!state.group1) { setEmpty(lists.group2, `Selecciona ${labels.group1.toLowerCase()}`); return; }
    state.group1.sides.forEach((item) => lists.group2.append(makeOption(item, labelValue(labels.group2, item.name), state.group2?.name === item.name, () => {
      state.group2 = item; state.group3 = null; updateTrail(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group3");
    })));
  };

  const renderGroup1 = () => {
    const query = search.value.trim().toLowerCase();
    const filtered = group1Items.filter((item) => item.name.toLowerCase().includes(query));
    lists.group1.replaceChildren();
    group1Count.textContent = `${filtered.length} opciones`;
    if (!filtered.length) { setEmpty(lists.group1, "Sin resultados", "Prueba con otro valor."); return; }
    filtered.forEach((item) => lists.group1.append(makeOption(item, labelValue(labels.group1, item.name), state.group1?.name === item.name, () => {
      state.group1 = item; state.group2 = null; state.group3 = null; updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group2");
    })));
  };

  explorer.querySelector("[data-progress-back='scope']")?.addEventListener("click", () => {
    state.group1 = state.group2 = state.group3 = null;
    updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations();
    browser.scrollTo({ left: 0, behavior: "smooth" });
  });
  trail.group1.addEventListener("click", () => { state.group2 = state.group3 = null; updateTrail(); renderGroup2(); renderGroup3(); renderLocations(); moveTo("group2"); });
  trail.group2.addEventListener("click", () => { state.group3 = null; updateTrail(); renderGroup3(); renderLocations(); moveTo("group3"); });
  trail.group3.addEventListener("click", () => moveTo("locations"));
  search.addEventListener("input", renderGroup1);
  explorer.querySelector("[data-reconciliation-close]")?.addEventListener("click", () => dialog.close());
  dialog?.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  const saveLocationFlag = async (field, checkbox) => {
    if (!currentLocation || !validationUrl) return;
    const requestedValue = checkbox.checked;
    checkbox.disabled = true;
    validationFeedback.textContent = "Guardando…";
    const formData = new FormData();
    formData.append("ubicacion", currentLocation.code);
    formData.append("campo", field);
    formData.append(field, String(requestedValue));
    formData.append("csrfmiddlewaretoken", validationForm.querySelector("[name='csrfmiddlewaretoken']").value);
    try {
      const response = await fetch(validationUrl, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "No fue posible guardar la validación.");
      window.sessionStorage.setItem(restoredStateKey, JSON.stringify({
        group1: state.group1?.name,
        group2: state.group2?.name,
        group3: state.group3?.name,
      }));
      window.location.reload();
    } catch (error) {
      checkbox.checked = !requestedValue;
      checkbox.disabled = false;
      validationFeedback.textContent = error.message;
    }
  };
  validationCheckbox?.addEventListener("change", () => saveLocationFlag("validada", validationCheckbox));
  rgeModificationCheckbox?.addEventListener("change", () => saveLocationFlag("modificar_rge", rgeModificationCheckbox));

  renderGroup1(); renderGroup2(); renderGroup3(); renderLocations();
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(restoredStateKey));
    window.sessionStorage.removeItem(restoredStateKey);
    state.group1 = group1Items.find((item) => item.name === saved.group1) || null;
    state.group2 = state.group1?.sides.find((item) => item.name === saved.group2) || null;
    state.group3 = state.group2?.bodies.find((item) => item.name === saved.group3) || null;
    updateTrail(); renderGroup1(); renderGroup2(); renderGroup3(); renderLocations();
  } catch { window.sessionStorage.removeItem(restoredStateKey); }
})();
