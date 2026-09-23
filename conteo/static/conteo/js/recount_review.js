(() => {
  const dialog = document.querySelector("[data-review-modal]");
  const body = dialog?.querySelector("[data-review-body]");
  const form = dialog?.querySelector("[data-review-form]");
  if (!dialog || !body || !form) return;

  const selectAll = dialog.querySelector("[data-review-select-all]");
  const allValue = dialog.querySelector("[data-review-all-value]");
  const search = dialog.querySelector("[data-review-search]");
  const sort = dialog.querySelector("[data-review-sort]");
  const minTotal = dialog.querySelector("[data-review-min-total]");
  const maxTotal = dialog.querySelector("[data-review-max-total]");
  const clearFilters = dialog.querySelector("[data-review-clear-filters]");
  const counter = dialog.querySelector("[data-review-counter]");
  const saveButton = dialog.querySelector("[data-review-save]");
  const finalizeButton = dialog.querySelector("[data-finalize-line]");
  const loading = dialog.querySelector("[data-review-loading]");
  const shortageTotal = dialog.querySelector("[data-review-shortage]");
  const overageTotal = dialog.querySelector("[data-review-overage]");
  const netTotal = dialog.querySelector("[data-review-net]");

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);

  const formatUsd = (value) => {
    const amount = String(value);
    return amount.startsWith("-") ? `-$${amount.slice(1)}` : `$${amount}`;
  };

  const updateCounter = () => {
    const inputs = [...body.querySelectorAll("input[name='codes']")];
    const visibleInputs = inputs.filter((input) => !input.closest("[data-review-row]").hidden);
    const checked = inputs.filter((input) => input.checked).length;
    const visibleChecked = visibleInputs.filter((input) => input.checked).length;
    counter.textContent = `${checked} seleccionado${checked === 1 ? "" : "s"} · ${visibleInputs.length} visibles`;
    saveButton.disabled = checked === 0;
    selectAll.checked = visibleInputs.length > 0 && visibleChecked === visibleInputs.length;
    selectAll.indeterminate = visibleChecked > 0 && visibleChecked < visibleInputs.length;
    allValue.value = inputs.length > 0 && checked === inputs.length ? "1" : "0";
  };

  const numericFilter = (input) => {
    const value = input.value.trim();
    return value === "" ? null : Number(value);
  };

  const applyView = () => {
    const term = search.value.trim().toLowerCase();
    const minimum = numericFilter(minTotal);
    const maximum = numericFilter(maxTotal);
    const rows = [...body.querySelectorAll("[data-review-row]")];

    rows.forEach((row) => {
      const total = row.dataset.total === "" ? null : Number(row.dataset.total);
      const matchesSearch = row.dataset.search.includes(term);
      const matchesMinimum = minimum === null || (total !== null && total >= minimum);
      const matchesMaximum = maximum === null || (total !== null && total <= maximum);
      row.hidden = !(matchesSearch && matchesMinimum && matchesMaximum);
    });

    rows.sort((left, right) => {
      if (sort.value === "default") return Number(left.dataset.order) - Number(right.dataset.order);
      const leftTotal = left.dataset.total === "" ? null : Number(left.dataset.total);
      const rightTotal = right.dataset.total === "" ? null : Number(right.dataset.total);
      if (leftTotal === null) return rightTotal === null ? Number(left.dataset.order) - Number(right.dataset.order) : 1;
      if (rightTotal === null) return -1;
      const comparison = leftTotal - rightTotal;
      return sort.value === "asc" ? comparison : -comparison;
    });
    rows.forEach((row) => body.appendChild(row));
    updateCounter();
  };

  const renderCodes = (codes) => {
    body.innerHTML = codes.map((item, index) => {
      const locations = [item.ubicacion_1, item.ubicacion_2, item.ubicacion_3, item.ubicacion_4].filter(Boolean).join(", ") || "—";
      const searchValue = `${item.codigo} ${item.sublinea} ${locations}`.toLowerCase();
      const differenceClass = Number(item.diferencia) < 0 ? "is-negative" : "is-positive";
      const totalClass = item.costo_total === null ? "" : (Number(item.costo_total) < 0 ? "is-negative" : "is-positive");
      return `<tr data-review-row data-search="${escapeHtml(searchValue)}" data-total="${escapeHtml(item.costo_total ?? "")}" data-order="${index}">
        <td><input type="checkbox" name="codes" value="${escapeHtml(item.id)}" /></td>
        <td>${escapeHtml(item.sublinea)}</td>
        <td><strong>${escapeHtml(item.codigo)}</strong></td>
        <td>${escapeHtml(item.ultimo_conteo)}</td>
        <td>${escapeHtml(item.existencia)}</td>
        <td><span class="difference-value ${differenceClass}">${escapeHtml(item.diferencia)}</span></td>
        <td>${item.costo === null ? "—" : escapeHtml(formatUsd(item.costo))}</td>
        <td>${item.costo_total === null ? "—" : `<span class="difference-value ${totalClass}">${escapeHtml(formatUsd(item.costo_total))}</span>`}</td>
        <td title="${escapeHtml(locations)}">${escapeHtml(locations)}</td>
      </tr>`;
    }).join("");
    if (!codes.length) body.innerHTML = '<tr><td colspan="9" class="review-empty">No hay códigos con diferencia.</td></tr>';
    body.querySelectorAll("input[name='codes']").forEach((checkbox) => checkbox.addEventListener("change", updateCounter));
    selectAll.checked = false;
    selectAll.indeterminate = false;
    allValue.value = "0";
    applyView();
  };

  const openReview = async (button) => {
    loading.hidden = false;
    body.innerHTML = "";
    search.value = "";
    sort.value = "default";
    minTotal.value = "";
    maxTotal.value = "";
    shortageTotal.textContent = "—";
    overageTotal.textContent = "—";
    netTotal.textContent = "—";
    netTotal.classList.remove("is-negative", "is-positive");
    saveButton.disabled = true;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    try {
      const response = await fetch(button.dataset.codesUrl, {headers: {"X-Requested-With": "XMLHttpRequest"}});
      if (!response.ok) throw new Error("No se pudieron cargar los códigos.");
      const data = await response.json();
      dialog.querySelector("[data-review-line]").textContent = data.linea;
      dialog.querySelector("[data-review-recount]").textContent = `Carga #${data.reconteo}`;
      dialog.querySelector("[data-review-file]").textContent = data.archivo;
      shortageTotal.textContent = formatUsd(data.totales.faltante);
      overageTotal.textContent = formatUsd(data.totales.sobrante);
      netTotal.textContent = formatUsd(data.totales.diferencia_neta);
      netTotal.classList.add(Number(data.totales.diferencia_neta) < 0 ? "is-negative" : "is-positive");
      form.action = button.dataset.saveUrl;
      finalizeButton.formAction = button.dataset.finalizeUrl;
      renderCodes(data.codes);
    } catch (error) {
      body.innerHTML = `<tr><td colspan="9" class="review-empty">${escapeHtml(error.message)}</td></tr>`;
    } finally {
      loading.hidden = true;
    }
  };

  document.querySelectorAll("[data-review-load]").forEach((button) => {
    button.addEventListener("click", () => openReview(button));
  });
  dialog.querySelectorAll("[data-review-close]").forEach((button) => {
    button.addEventListener("click", () => dialog.close());
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  selectAll.addEventListener("change", () => {
    body.querySelectorAll("[data-review-row]:not([hidden]) input[name='codes']").forEach((checkbox) => { checkbox.checked = selectAll.checked; });
    updateCounter();
  });
  search.addEventListener("input", applyView);
  sort.addEventListener("change", applyView);
  minTotal.addEventListener("input", applyView);
  maxTotal.addEventListener("input", applyView);
  clearFilters.addEventListener("click", () => {
    search.value = "";
    sort.value = "default";
    minTotal.value = "";
    maxTotal.value = "";
    applyView();
  });
})();
