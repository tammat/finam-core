"use strict";
(function () {
  const storageKey = "marketcore.controlCenter.activeAction";
  const statusBar = document.querySelector("[data-action-status]");
  const statusText = document.querySelector("[data-action-status-text]");
  const statusPct = document.querySelector("[data-action-progress-pct]");
  const statusFill = document.querySelector("[data-action-progress-fill]");

  function showStatus(label, pct, running) {
    if (!statusBar) return;
    const safePct = Math.max(0, Math.min(100, Number(pct) || 0));
    statusBar.hidden = false;
    statusBar.dataset.state = running ? "RUNNING" : "COMPLETE";
    statusText.textContent = `${running ? "Выполняется" : "Завершено"} «${label}»`;
    statusPct.textContent = `${safePct}%`;
    statusFill.style.width = `${safePct}%`;
  }

  async function pollAction(action) {
    try {
      const response = await fetch(`/api/v1/control-center/action-status?action=${encodeURIComponent(action.code)}`, {cache: "no-store"});
      const status = await response.json();
      const label = status.known ? status.label : action.label;
      showStatus(label, status.progress_pct, status.running);
      if (status.running) {
        window.setTimeout(() => pollAction(action), 1500);
      } else {
        localStorage.removeItem(storageKey);
        window.setTimeout(() => { if (statusBar) statusBar.hidden = true; }, 5000);
      }
    } catch (_) {
      showStatus(action.label, 10, true);
      window.setTimeout(() => pollAction(action), 3000);
    }
  }

  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (saved && saved.code && saved.label) {
      showStatus(saved.label, 10, true);
      pollAction(saved);
    }
  } catch (_) {
    localStorage.removeItem(storageKey);
  }

  const actionForms = Array.from(document.querySelectorAll('form[action^="/workspace-v2/control-center/edge-oos/"]'));
  actionForms.forEach(form => form.addEventListener("submit", event => {
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    if (button.disabled) {
      event.preventDefault();
      return;
    }
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    const label = button.textContent.trim();
    const code = form.action.split("/").filter(Boolean).pop();
    const action = {code, label};
    localStorage.setItem(storageKey, JSON.stringify(action));
    showStatus(label, 5, true);
    button.textContent = document.body.dataset.actionRunningLabel || "Запускаю…";
    document.body.dataset.actionState = "RUNNING";
  }));

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

  function bindMultiFilter(filterSelector, rowSelector, countSelector) {
    const filters = Array.from(document.querySelectorAll(filterSelector));
    const filteredRows = Array.from(document.querySelectorAll(rowSelector));
    const output = document.querySelector(countSelector);
    function updateMultiFilter() {
      let visible = 0;
      filteredRows.forEach(row => {
        const show = filters.every(select => {
          const key = select.dataset.sessionFilter || select.dataset.executionFilter || select.dataset.factoryFilter;
          return select.value === "ALL" || row.dataset[key] === select.value;
        });
        row.hidden = !show;
        visible += Number(show);
      });
      if (output) output.textContent = `Показано: ${visible} из ${filteredRows.length}`;
    }
    filters.forEach(select => select.addEventListener("input", updateMultiFilter));
    updateMultiFilter();
  }
  bindMultiFilter("[data-session-filter]", "[data-session-row]", "[data-session-count]");
  bindMultiFilter("[data-execution-filter]", "[data-execution-row]", "[data-execution-count]");
  bindMultiFilter("[data-factory-filter]", "[data-factory-row]", "[data-factory-count]");
})();
