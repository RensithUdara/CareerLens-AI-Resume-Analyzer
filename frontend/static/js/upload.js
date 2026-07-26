/* Handles the drag-and-drop resume upload on /upload */
document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const errorEl = document.getElementById("upload-error");
  const uploadBtn = document.getElementById("upload-btn");
  if (!dropzone) return;

  let selectedFile = null;

  dropzone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
  );
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) setFile(fileInput.files[0]);
  });

  function setFile(file) {
    const allowed = [".pdf", ".docx"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
      errorEl.textContent = "Please choose a PDF or DOCX file.";
      selectedFile = null;
      uploadBtn.disabled = true;
      return;
    }
    selectedFile = file;
    errorEl.textContent = "";
    uploadBtn.disabled = false;
    document.getElementById("dropzone-text").textContent = `Selected: ${file.name}`;
  }

  uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner"></span> Uploading...';
    errorEl.textContent = "";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/resumes/upload", { method: "POST", body: formData, credentials: "same-origin" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed.");
      window.location.href = `/analysis/${data.id}`;
    } catch (err) {
      errorEl.textContent = err.message;
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Analyze my resume";
    }
  });
});
