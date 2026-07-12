"use strict";
(function () {
  const filter = document.querySelector("[data-oos-filter]");
  const rows = Array.from(document.querySelectorAll("[data-oos-results] tr"));
  const count = document.querySelector("[data-oos-count]");
  if (!filter) return;
  function update() {
    let visible = 0;
    rows.forEach(row => {
      const show = filter.value === "ALL" || row.dataset.verdict === filter.value;
      row.hidden = !show; visible += Number(show);
    });
    count.textContent = `Показано: ${visible} из ${rows.length}`;
  }
  filter.addEventListener("input", update); update();
  const hypothesisFilter = document.querySelector("[data-hypothesis-filter]");
  const hypothesisRows = Array.from(document.querySelectorAll("[data-hypothesis-row]"));
  if (hypothesisFilter) hypothesisFilter.addEventListener("input", () => hypothesisRows.forEach(row => {
    row.hidden = hypothesisFilter.value !== "ALL" && row.dataset.family !== hypothesisFilter.value;
  }));
  const leadLagFilter = document.querySelector("[data-lead-lag-filter]");
  const leadLagRows = Array.from(document.querySelectorAll("[data-lead-lag-row]"));
  const leadLagCount = document.querySelector("[data-lead-lag-count]");
  function updateLeadLag() {
    if (!leadLagFilter) return;
    let visible = 0;
    leadLagRows.forEach(row => {
      const show = leadLagFilter.value === "ALL" || row.dataset.verdict === leadLagFilter.value;
      row.hidden = !show;
      visible += Number(show);
    });
    if (leadLagCount) leadLagCount.textContent = `Показано: ${visible} из ${leadLagRows.length}`;
  }
  if (leadLagFilter) leadLagFilter.addEventListener("input", updateLeadLag);
  updateLeadLag();
})();
