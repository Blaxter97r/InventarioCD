(() => {
  const form = document.querySelector("[data-inventory-upload-form]");
  const submit = form?.querySelector("[data-inventory-upload-submit]");
  if (!form || !submit) return;

  let processing = false;
  form.addEventListener("submit", (event) => {
    if (processing) {
      event.preventDefault();
      return;
    }
    processing = true;
    submit.disabled = true;
    submit.textContent = "Procesando archivo…";
  });
})();
