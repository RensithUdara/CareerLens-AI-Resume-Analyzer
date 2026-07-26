/* Drives the /analysis/{resume_id} page:
   1. Kicks off the AI analysis as soon as the page loads.
   2. Renders ATS score, skills, strengths/weaknesses, suggestions.
   3. Lets the user paste a job description and see the match score.
   4. Lets the user download the PDF report.
*/
document.addEventListener("DOMContentLoaded", async () => {
  const root = document.getElementById("analysis-root");
  if (!root) return;
  const resumeId = root.dataset.resumeId;

  showLoading(true);
  try {
    const analysis = await apiRequest(`/api/analysis/${resumeId}`, { method: "POST" });
    renderAnalysis(analysis);
    window.currentAnalysisId = analysis.id;
  } catch (err) {
    document.getElementById("analysis-error").textContent = err.message;
  } finally {
    showLoading(false);
  }

  const jobForm = document.getElementById("job-match-form");
  jobForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("job-match-btn");
    const jd = document.getElementById("job-description").value.trim();
    if (jd.length < 20) {
      document.getElementById("job-match-error").textContent = "Paste a more complete job description (20+ characters).";
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Matching...';
    document.getElementById("job-match-error").textContent = "";

    try {
      const result = await apiRequest(`/api/analysis/${resumeId}/job-match`, {
        method: "POST",
        body: JSON.stringify({ resume_id: Number(resumeId), job_description: jd }),
      });
      renderJobMatch(result);
    } catch (err) {
      document.getElementById("job-match-error").textContent = err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "Compare against this job";
    }
  });

  document.getElementById("download-report-btn").addEventListener("click", () => {
    if (!window.currentAnalysisId) return;
    window.location.href = `/api/analysis/${window.currentAnalysisId}/report`;
  });
});

function showLoading(isLoading) {
  document.getElementById("analysis-loading").style.display = isLoading ? "flex" : "none";
  document.getElementById("analysis-content").style.display = isLoading ? "none" : "block";
}

function renderAnalysis(a) {
  renderScoreRing("ats-score-ring", a.ats_score);
  document.getElementById("ats-score-label").textContent = `${Math.round(a.ats_score)}%`;

  fillChipList("technical-skills", a.technical_skills, "primary");
  fillChipList("soft-skills", a.soft_skills, "primary");
  fillList("education-list", a.education);
  fillList("experience-list", a.experience);
  fillList("projects-list", a.projects);
  fillList("certifications-list", a.certifications);

  fillBadgeList("ats-strengths", a.ats_strengths, "good", "✔");
  fillBadgeList("ats-weaknesses", a.ats_weaknesses, "warn", "✖");

  fillList("suggestions-list", a.suggestions, true);

  document.getElementById("download-report-btn").disabled = false;
}

function renderJobMatch(a) {
  const section = document.getElementById("job-match-results");
  section.style.display = "block";
  renderScoreRing("job-match-ring", a.job_match_score);
  document.getElementById("job-match-label").textContent = `${Math.round(a.job_match_score)}%`;

  fillChipList("matching-skills", a.matching_skills, "matching");
  fillChipList("missing-skills", a.missing_skills, "missing");
  fillChipList("recommended-skills", a.recommended_skills, "primary");
}

function renderScoreRing(elementId, percent) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, percent)) / 100) * circumference;

  let svg = el.querySelector("svg");
  if (!svg) {
    el.insertAdjacentHTML("afterbegin", `
      <svg viewBox="0 0 130 130">
        <circle class="track" cx="65" cy="65" r="${radius}"></circle>
        <circle class="fill" cx="65" cy="65" r="${radius}"
          stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}"></circle>
      </svg>`);
  } else {
    svg.querySelector(".fill").setAttribute("stroke-dasharray", circumference);
  }

  requestAnimationFrame(() => {
    el.querySelector(".fill").style.strokeDashoffset = offset;
  });
}

function fillChipList(elementId, items, variant) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (!items || items.length === 0) {
    el.innerHTML = `<span class="skill-chip">None detected</span>`;
    return;
  }
  el.innerHTML = items.map((s) => `<span class="skill-chip ${variant}">${escapeHtml(s)}</span>`).join("");
}

function fillList(elementId, items, numbered = false) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (!items || items.length === 0) {
    el.innerHTML = `<li>Nothing detected</li>`;
    return;
  }
  const itemClass = numbered ? "suggestion-item" : "detail-item";
  el.innerHTML = items.map((s) => `<li class="${itemClass}">${escapeHtml(s)}</li>`).join("");
}

function fillBadgeList(elementId, items, variant, icon) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (!items || items.length === 0) {
    el.innerHTML = `<li>Nothing detected</li>`;
    return;
  }
  el.innerHTML = items.map((s) => `<li><span class="badge badge-${variant}">${icon} ${escapeHtml(s)}</span></li>`).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
