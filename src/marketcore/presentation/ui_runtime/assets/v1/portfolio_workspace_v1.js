"use strict";

(function () {
    const sections = Array.from(document.querySelectorAll('[data-section="PORTFOLIO"]'));
    const positions = sections[0];
    if (!positions) return;

    const grid = positions.querySelector(".mc-v2-grid");
    if (!grid) return;

    const rows = Array.from(grid.querySelectorAll(":scope > .mc-v2-card"));
    if (!rows.length) return;

    const toolbar = document.createElement("div");
    toolbar.className = "mc-portfolio-toolbar";
    toolbar.innerHTML = `
      <label>Поиск <input type="search" data-control="search" placeholder="Тикер или название"></label>
      <label>Результат
        <select data-control="result">
          <option value="all">Все позиции</option>
          <option value="loss">Убыточные</option>
          <option value="profit">Прибыльные</option>
        </select>
      </label>
      <label>Сортировка
        <select data-control="sort">
          <option value="default">По умолчанию</option>
          <option value="value_desc">Стоимость ↓</option>
          <option value="pnl_asc">P&L: худшие</option>
          <option value="pnl_pct_asc">P&L %: худшие</option>
          <option value="name_asc">Название А–Я</option>
        </select>
      </label>
      <label>Плотность
        <select data-control="density">
          <option value="comfortable">Обычная</option>
          <option value="compact">Компактная</option>
        </select>
      </label>
      <button type="button" class="mc-settings-button" data-control="settings">Настройки</button>
      <output data-control="count"></output>`;
    positions.insertBefore(toolbar, grid);

    const search = toolbar.querySelector('[data-control="search"]');
    const result = toolbar.querySelector('[data-control="result"]');
    const sort = toolbar.querySelector('[data-control="sort"]');
    const density = toolbar.querySelector('[data-control="density"]');
    const count = toolbar.querySelector('[data-control="count"]');
    const settingsButton = toolbar.querySelector('[data-control="settings"]');

    const drawer = document.createElement("aside");
    drawer.className = "mc-settings-drawer";
    drawer.hidden = true;
    drawer.innerHTML = `
      <div class="mc-settings-head"><strong>Настройки оператора</strong><button type="button" data-settings="close">×</button></div>
      <label>Часовой пояс<select data-settings="timezone"><option>Europe/Moscow</option><option>UTC</option><option>Europe/Helsinki</option></select></label>
      <label>Валюта<select data-settings="currency"><option>RUB</option><option>USD</option><option>EUR</option></select></label>
      <label>Брокер<select data-settings="broker"><option>Finam</option><option>T-Bank</option><option>QUIK</option><option>Interactive Brokers</option></select></label>
      <p>Суммы портфеля остаются в валюте источника RUB до подключения FX.</p>
      <button type="button" class="mc-settings-apply" data-settings="apply">Применить</button>`;
    document.body.appendChild(drawer);

    const setting = name => drawer.querySelector(`[data-settings="${name}"]`);
    setting("timezone").value = document.body.dataset.timezone || "Europe/Moscow";
    setting("currency").value = document.body.dataset.currency || "RUB";
    setting("broker").value = document.body.dataset.broker || "Finam";
    settingsButton.addEventListener("click", () => { drawer.hidden = false; });
    setting("close").addEventListener("click", () => { drawer.hidden = true; });
    setting("apply").addEventListener("click", () => {
        const params = new URLSearchParams(location.search);
        ["timezone", "currency", "broker"].forEach(name => {
            const value = setting(name).value;
            params.set(name, value);
            localStorage.setItem(`marketcore.operator.${name}`, value);
        });
        location.search = params.toString();
    });

    const fields = row => {
        const map = {};
        row.querySelectorAll(".mc-v2-value-row").forEach(item => {
            const key = item.querySelector("dt")?.textContent.trim() || "";
            const value = item.querySelector("dd")?.textContent.trim() || "";
            map[key] = value;
        });
        return map;
    };
    const number = value => {
        const normalized = String(value || "").replace(/[^0-9,.-]/g, "").replace(",", ".");
        const parsed = Number.parseFloat(normalized);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const savedDensity = localStorage.getItem("marketcore.portfolio.density") || "comfortable";
    density.value = savedDensity;

    function update() {
        const query = search.value.trim().toLocaleLowerCase("ru");
        let visible = rows.filter(row => {
            const text = row.textContent.toLocaleLowerCase("ru");
            const negative = Boolean(row.querySelector(".is-negative"));
            const positive = Boolean(row.querySelector(".is-positive"));
            const resultMatch = result.value === "all" || (result.value === "loss" && negative) || (result.value === "profit" && positive);
            return text.includes(query) && resultMatch;
        });

        const key = sort.value;
        visible.sort((a, b) => {
            const av = fields(a); const bv = fields(b);
            if (key === "value_desc") return number(bv["Оценка"]) - number(av["Оценка"]);
            if (key === "pnl_asc") return number(av["P&L общий"]) - number(bv["P&L общий"]);
            if (key === "pnl_pct_asc") return number(av["P&L %"]) - number(bv["P&L %"]);
            if (key === "name_asc") return String(av["Название"]).localeCompare(String(bv["Название"]), "ru");
            return rows.indexOf(a) - rows.indexOf(b);
        });

        rows.forEach(row => { row.hidden = true; });
        visible.forEach(row => { row.hidden = false; grid.appendChild(row); });
        grid.dataset.density = density.value;
        localStorage.setItem("marketcore.portfolio.density", density.value);
        count.textContent = `Показано: ${visible.length} из ${rows.length}`;
    }

    [search, result, sort, density].forEach(control => control.addEventListener("input", update));
    update();
})();
