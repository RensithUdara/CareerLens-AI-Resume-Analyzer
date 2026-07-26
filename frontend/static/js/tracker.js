/* Renders the improvement tracker on /tracker: ATS score over every
   analysis the user has ever run, oldest to newest. */
document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("tracker-list");
  const empty = document.getElementById("tracker-empty");
  if (!list) return;

  try {
    const data = await apiRequest("/api/analysis/tracker/all");
    if (!data || data.length === 0) {
      empty.style.display = "block";
      return;
    }

    list.innerHTML = data.map((item, index) => {
      const prev = index > 0 ? data[index - 1].ats_score : null;
      const delta = prev !== null ? Math.round(item.ats_score - prev) : null;
      const deltaHtml = delta === null
        ? `<span class="badge badge-primary">First analysis</span>`
        : `<span class="tracker-delta ${delta >= 0 ? "positive" : "negative"}">${delta >= 0 ? "+" : ""}${delta}%</span>`;
      const canCompare = index > 0 && data[index - 1].resume_id !== item.resume_id;
      const compareHtml = canCompare
        ? `<a class="btn btn-outline" href="/compare?before=${data[index - 1].resume_id}&after=${item.resume_id}">Compare</a>`
        : "";

      const date = new Date(item.created_at).toLocaleString();
      return `
        <div class="tracker-item">
          <div style="flex:1">
            <strong>${Math.round(item.ats_score)}% ATS score</strong>
            <div style="color:var(--text-muted); font-size:0.85rem;">${date}</div>
          </div>
          <div class="item-actions">
            ${deltaHtml}
            ${compareHtml}
          </div>
        </div>`;
    }).join("");
  } catch (err) {
    empty.style.display = "block";
    empty.querySelector("p").textContent = err.message;
  }
});
