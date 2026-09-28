(() => {
  const modal = document.querySelector("[data-difference-report-modal]");
  const openButton = document.querySelector("[data-difference-report-open]");
  const payload = document.querySelector("#difference-report-filter-data");
  if (!modal || !openButton || !payload) return;

  let warehouses;
  try {
    warehouses = JSON.parse(payload.textContent);
  } catch {
    warehouses = [];
  }
  if (!warehouses.length) {
    openButton.disabled = true;
    return;
  }

  const form = modal.querySelector("[data-difference-report-form]");
  const warehouseSelect = modal.querySelector("[data-report-warehouse]");
  const typeSelect = modal.querySelector("[data-report-type]");
  const scopeSelect = modal.querySelector("[data-report-scope]");
  const scopeLabel = modal.querySelector("[data-report-scope-label]");
  const aisleContainer = modal.querySelector("[data-report-aisles]");
  const selectAll = modal.querySelector("[data-report-select-all]");
  const submitButton = modal.querySelector("[data-report-submit]");
  const reportInputs = [...modal.querySelectorAll("input[name='reporte']")];
  const previewTitle = modal.querySelector("[data-report-preview-title]");
  const previewDetail = modal.querySelector("[data-report-preview-detail]");
  const primaryFormat = modal.querySelector("[data-report-format-primary]");
  const secondaryFormat = modal.querySelector("[data-report-format-secondary]");
  const duplicatesFormat = modal.querySelector("[data-report-format-duplicates]");
  const initial = {
    warehouse: openButton.dataset.selectedWarehouse,
    type: openButton.dataset.selectedType,
    scope: openButton.dataset.selectedScope,
  };

  const selectedWarehouse = () => warehouses.find((item) => item.value === warehouseSelect.value);
  const selectedType = () => selectedWarehouse()?.types.find((item) => item.value === typeSelect.value);
  const selectedScope = () => selectedType()?.scopes.find((item) => item.value === scopeSelect.value);
  const aisleInputs = () => [...aisleContainer.querySelectorAll("input[name='pasillo']")];

  const fillSelect = (select, options, selectedValue) => {
    select.replaceChildren();
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label || item.value;
      option.selected = item.value === selectedValue;
      select.append(option);
    });
    if (![...select.options].some((option) => option.selected)) select.selectedIndex = 0;
  };

  const updatePreview = () => {
    const warehouse = selectedWarehouse();
    const type = selectedType();
    const scope = selectedScope();
    const checked = aisleInputs().filter((input) => input.checked);
    const inputs = aisleInputs();
    const locationCount = checked.reduce((total, input) => total + Number(input.dataset.locationCount || 0), 0);
    const report = reportInputs.find((input) => input.checked)?.value || "diferencias";
    const isDuplicates = report === "duplicados";

    selectAll.checked = Boolean(inputs.length) && checked.length === inputs.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < inputs.length;
    submitButton.disabled = !checked.length;
    primaryFormat.hidden = isDuplicates || type?.value !== "PRIMARIO";
    secondaryFormat.hidden = isDuplicates || type?.value !== "SECUNDARIO";
    duplicatesFormat.hidden = !isDuplicates;

    if (!warehouse || !type || !scope || !checked.length) {
      previewTitle.textContent = "Completa los filtros";
      previewDetail.textContent = "Selecciona al menos un pasillo para habilitar la descarga.";
      return;
    }
    const reportLabel = isDuplicates ? "Posibles duplicados" : "Diferencias";
    previewTitle.textContent = `${reportLabel} · ${warehouse.label} · ${type.label} · ${type.scope_label} ${scope.value}`;
    previewDetail.textContent = `${checked.length} pasillo${checked.length === 1 ? "" : "s"} · ${locationCount} ubicaciones incluidas`;
  };

  const renderAisles = () => {
    aisleContainer.replaceChildren();
    const scope = selectedScope();
    (scope?.aisles || []).forEach((aisle) => {
      const label = document.createElement("label");
      label.className = "difference-report-aisle";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "pasillo";
      input.value = aisle.value;
      input.dataset.locationCount = aisle.location_count;
      const mark = document.createElement("span");
      mark.setAttribute("aria-hidden", "true");
      const copy = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = `Pasillo ${aisle.value}`;
      const count = document.createElement("small");
      count.textContent = `${aisle.location_count} ubicaciones`;
      copy.append(name, count);
      label.append(input, mark, copy);
      input.addEventListener("change", updatePreview);
      aisleContainer.append(label);
    });
    selectAll.checked = false;
    selectAll.indeterminate = false;
    updatePreview();
  };

  const renderScopes = (preferred = "") => {
    const type = selectedType();
    scopeLabel.textContent = type?.scope_label || "Piso o zona";
    fillSelect(
      scopeSelect,
      (type?.scopes || []).map((item) => ({
        ...item,
        label: `${type.scope_label} ${item.value}`,
      })),
      preferred,
    );
    renderAisles();
  };

  const renderTypes = (preferredType = "", preferredScope = "") => {
    const warehouse = selectedWarehouse();
    fillSelect(typeSelect, warehouse?.types || [], preferredType);
    renderScopes(preferredScope);
  };

  fillSelect(warehouseSelect, warehouses, initial.warehouse);
  renderTypes(initial.type, initial.scope);

  warehouseSelect.addEventListener("change", () => renderTypes());
  typeSelect.addEventListener("change", () => renderScopes());
  scopeSelect.addEventListener("change", renderAisles);
  reportInputs.forEach((input) => input.addEventListener("change", updatePreview));
  selectAll.addEventListener("change", () => {
    aisleInputs().forEach((input) => { input.checked = selectAll.checked; });
    updatePreview();
  });

  openButton.addEventListener("click", () => modal.showModal());
  modal.querySelectorAll("[data-difference-report-close]").forEach((button) => {
    button.addEventListener("click", () => modal.close());
  });
  modal.addEventListener("click", (event) => {
    const bounds = modal.getBoundingClientRect();
    const inside = event.clientX >= bounds.left && event.clientX <= bounds.right
      && event.clientY >= bounds.top && event.clientY <= bounds.bottom;
    if (!inside) modal.close();
  });
  form.addEventListener("submit", () => {
    window.setTimeout(() => modal.close(), 100);
  });
})();
