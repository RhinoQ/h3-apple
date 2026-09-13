// Copy the visible reproduction command; no uploads or stored state.
document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const code = document.getElementById(button.dataset.copy);
  try {
    await navigator.clipboard.writeText(code.textContent);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Select and copy the text below";
  }
});
