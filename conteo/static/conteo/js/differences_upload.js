(() => {
  const form = document.querySelector("#differences-upload-form");
  const dialog = document.querySelector("[data-differences-confirm-modal]");
  const openButton = document.querySelector("[data-differences-confirm-open]");
  const submitButton = document.querySelector("[data-differences-submit]");

  if (!form || !dialog || !openButton || !submitButton) return;

  const lineSelect = form.querySelector("select[name='linea']");
  const fileInput = form.querySelector("input[name='archivo']");
  const as400Input = form.querySelector("input[name='archivo_as400']");
  let confirmed = false;

  const closeDialog = () => {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  const openDialog = () => {
    if (!form.reportValidity()) return;
    const fileName = fileInput.files[0]?.name || "—";
    const lineName = lineSelect.options[lineSelect.selectedIndex]?.text || "—";
    dialog.querySelector("[data-confirm-file]").textContent = fileName;
    dialog.querySelector("[data-confirm-as400]").textContent = as400Input.files[0]?.name || "Sin adjuntar";
    dialog.querySelector("[data-confirm-line]").textContent = lineName;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  openButton.addEventListener("click", openDialog);
  form.addEventListener("submit", (event) => {
    if (!confirmed) {
      event.preventDefault();
      openDialog();
    }
  });
  dialog.querySelectorAll("[data-differences-confirm-close]").forEach((button) => {
    button.addEventListener("click", closeDialog);
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog();
  });
  submitButton.addEventListener("click", () => {
    confirmed = true;
    closeDialog();
    form.requestSubmit();
  });
})();
