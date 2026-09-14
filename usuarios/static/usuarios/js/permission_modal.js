(() => {
  const dialog = document.querySelector("[data-admin-permission-modal]");
  const openButtons = document.querySelectorAll("[data-admin-permission-open]");

  if (!dialog || !openButtons.length) return;

  const openDialog = () => {
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  const closeDialog = () => {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  openButtons.forEach((button) => button.addEventListener("click", openDialog));
  dialog.querySelectorAll("[data-admin-permission-close]").forEach((button) => {
    button.addEventListener("click", closeDialog);
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog();
  });
})();
