/* Side-by-side resume version comparison for /compare. */
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("compare-form");
  if (!form) return;

  const beforeSelect = document.getElementById("before-resume");
  const afterSelect = document.getElementById("after-resume");
  const empty = document.getElementById("compare-empty");
  const error = document.getElementById("compare-error");
  const results = document.getElementById("compare-results");

  try {
    const resumes = await apiRequest("/api/resumes/history");
    if (!resumes || resumes.length < 2) {
      form.closest(".card").style.display = "none";
      empty.style.display = "block";
      return;
    }

    fillResumeSelect(beforeSelect, resumes);
    fillResumeSelect(afterSelect, resumes);

    const params = new URLSearchParams(window.location.search);
    const beforeId = params.get("before");
    const afterId = params.get("after");
    if (beforeId && resumes.some((resume) => String(resume.id) === beforeId)) {
      beforeSelect.value = beforeId;
    }
    if (afterId && resumes.some((resume) => String(resume.id) === afterId)) {
      afterSelect.value = afterId;
      if (!beforeId) {
        const afterIndex = resumes.findIndex((resume) => String(resume.id) === afterId);
        beforeSelect.value = String(resumes[Math.min(afterIndex + 1, resumes.length - 1)].id);
      }
    } else if (!beforeId) {
      beforeSelect.value = String(resumes[1].id);
      afterSelect.value = String(resumes[0].id);
    }

    await runCompare();
  } catch (err) {
    error.textContent = err.message;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runCompare();
  });

  async function runCompare() {
    error.textContent = "";
    if (beforeSelect.value === afterSelect.value) {
      error.textContent = "Choose two different resume versions.";
      return;
    }

    try {
      const data = await apiRequest(`/api/resumes/compare?before_id=${beforeSelect.value}&after_id=${afterSelect.value}`);
      renderComparison(data);
      results.style.display = "grid";
    } catch (err) {
      error.textContent = err.message;
    }
  }
});

function fillResumeSelect(select, resumes) {
  select.innerHTML = resumes.map((resume) => {
    const date = new Date(resume.uploaded_at).toLocaleString();
    return `<option value="${resume.id}">${escapeHtml(resume.original_filename)} - ${date}</option>`;
  }).join("");
}

function renderComparison(data) {
  const before = data.before_resume;
  const after = data.after_resume;

  document.getElementById("before-title").textContent = before.original_filename;
  document.getElementById("before-meta").textContent = summaryText(before);
  document.getElementById("after-title").textContent = after.original_filename;
  document.getElementById("after-meta").textContent = summaryText(after);

  const deltaEl = document.getElementById("score-delta");
  if (data.score_delta === null || data.score_delta === undefined) {
    deltaEl.textContent = "No paired scores";
    deltaEl.className = "";
  } else {
    const delta = Math.round(data.score_delta);
    deltaEl.textContent = `${delta >= 0 ? "+" : ""}${delta}%`;
    deltaEl.className = delta >= 0 ? "positive" : "negative";
  }

  const grid = document.getElementById("diff-grid");
  const changedLines = data.diff.filter((line) => line.status !== "same").length;
  const rows = data.diff.length ? data.diff : [{ line_number: 1, before: "", after: "", status: "same" }];

  grid.innerHTML = `
    <div class="diff-col-head">Before</div>
    <div class="diff-col-head">After</div>
    ${rows.map((line) => `
      <pre class="diff-line ${line.status}">${escapeHtml(line.before || " ")}</pre>
      <pre class="diff-line ${line.status}">${escapeHtml(line.after || " ")}</pre>
    `).join("")}
  `;

  if (changedLines === 0) {
    grid.insertAdjacentHTML("beforeend", `<div class="diff-note">No text differences detected between these uploads.</div>`);
  }
}

function summaryText(resume) {
  const uploaded = new Date(resume.uploaded_at).toLocaleString();
  const score = resume.ats_score === null || resume.ats_score === undefined
    ? "No analysis yet"
    : `${Math.round(resume.ats_score)}% ATS`;
  return `${uploaded} | ${score}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
