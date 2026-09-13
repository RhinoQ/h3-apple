// Prompt files stay on the reader's device. Nothing is uploaded or persisted.
document.addEventListener("change", async (event) => {
  const input = event.target;
  if (!(input instanceof HTMLInputElement) || !input.matches("[data-prompt-file]")) return;
  const panel = input.closest(".prompt-panel");
  const status = panel.querySelector("[role=status]");
  const content = panel.querySelector("pre");
  const file = input.files[0];
  content.hidden = true;
  if (!file) return;
  try {
    if (file.size > 100000) throw new Error("Choose the case's prompt.txt file.");
    const bytes = await file.arrayBuffer();
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
      .map((n) => n.toString(16).padStart(2, "0")).join("");
    if (hash !== input.dataset.sha256) throw new Error("This text does not match the prompt used for this case.");
    content.textContent = new TextDecoder().decode(bytes);
    content.hidden = false;
    status.textContent = "Exact prompt verified. Displayed locally; no upload.";
  } catch (error) {
    status.textContent = error.message;
  }
});

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
