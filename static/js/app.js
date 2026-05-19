document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyzeForm');
    const loader = document.getElementById('loader');
    const results = document.getElementById('results');
    const error = document.getElementById('error');
    const summaryDiv = document.getElementById('summary');
    const forecastDiv = document.getElementById('forecast');
    const competitorsDiv = document.getElementById('competitors');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        results.classList.add('hidden');
        error.classList.add('hidden');
        loader.classList.remove('hidden');

        const formData = new FormData(form);
        const params = new URLSearchParams();
        params.append('query', formData.get('query'));
        params.append('top_n', formData.get('top_n'));
        params.append('max_feedbacks', formData.get('max_feedbacks'));
        params.append('search_pages', formData.get('search_pages'));
        params.append('save', formData.get('save') === 'on' ? 'true' : 'false');

        try {
            const resp = await fetch(`/analyze?${params.toString()}`);
            const data = await resp.json();

            if (!resp.ok || data.error) {
                throw new Error(data.error || data.detail || 'Ошибка сервера');
            }

            renderResults(data);
            results.classList.remove('hidden');
        } catch (err) {
            error.textContent = '❌ ' + err.message;
            error.classList.remove('hidden');
        } finally {
            loader.classList.add('hidden');
        }
    });

    function renderResults(data) {
        const ms = data.market_summary || {};
        const nf = ms.new_product_forecast || {};

        // Summary
        summaryDiv.innerHTML = `
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="label">Конкурентов</div>
                    <div class="value">${ms.competitors_analyzed || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">Средняя цена</div>
                    <div class="value accent">${ms.avg_price ? ms.avg_price.toFixed(0) + ' ₽' : '—'}</div>
                </div>
                <div class="summary-card">
                    <div class="label">Ценовой диапазон</div>
                    <div class="value">${ms.min_price ? ms.min_price.toFixed(0) : '—'} – ${ms.max_price ? ms.max_price.toFixed(0) : '—'} ₽</div>
                </div>
                <div class="summary-card">
                    <div class="label">Рынок/мес (оценка)</div>
                    <div class="value success">${ms.total_market_revenue_30d_low ? (ms.total_market_revenue_30d_low/1000).toFixed(0) + '–' + (ms.total_market_revenue_30d_high/1000).toFixed(0) + 'K ₽' : '—'}</div>
                </div>
            </div>
        `;

        // Forecast
        if (nf) {
            forecastDiv.innerHTML = `
                <div class="forecast-box">
                    <h4>🎯 Прогноз для нового товара (вход в нишу)</h4>
                    <div class="forecast-row">
                        <div class="forecast-item pess">
                            <div class="f-label">Пессимистичный (1%)</div>
                            <div class="f-value">${nf.pessimistic_1pct_orders_30d || 0} заказов/мес</div>
                            <div class="f-value" style="font-size:0.9rem;color:var(--text-muted)">${nf.pessimistic_revenue_30d ? nf.pessimistic_revenue_30d.toLocaleString('ru-RU') : 0} ₽</div>
                        </div>
                        <div class="forecast-item real">
                            <div class="f-label">Реалистичный (3%)</div>
                            <div class="f-value">${nf.realistic_3pct_orders_30d || 0} заказов/мес</div>
                            <div class="f-value" style="font-size:0.9rem;color:var(--text-muted)">${nf.realistic_revenue_30d ? nf.realistic_revenue_30d.toLocaleString('ru-RU') : 0} ₽</div>
                        </div>
                        <div class="forecast-item opt">
                            <div class="f-label">Оптимистичный (10%)</div>
                            <div class="f-value">${nf.optimistic_10pct_orders_30d || 0} заказов/мес</div>
                            <div class="f-value" style="font-size:0.9rem;color:var(--text-muted)">${nf.optimistic_revenue_30d ? nf.optimistic_revenue_30d.toLocaleString('ru-RU') : 0} ₽</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Competitors table
        const comps = data.competitors || [];
        let tableHTML = `
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Артикул</th>
                            <th>Название</th>
                            <th>Бренд</th>
                            <th>Цена</th>
                            <th>Рейтинг</th>
                            <th>Отзывов WB</th>
                            <th>Заказов/мес (оценка)</th>
                            <th>Выручка/мес (оценка)</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        comps.forEach(c => {
            const se = c.sales_estimate || {};
            tableHTML += `
                <tr>
                    <td><a href="https://www.wildberries.ru/catalog/${c.article_id}/detail.aspx" target="_blank" style="color:var(--accent);text-decoration:none">${c.article_id}</a></td>
                    <td>${c.name ? c.name.substring(0, 50) + (c.name.length > 50 ? '...' : '') : '—'}</td>
                    <td>${c.brand || '—'}</td>
                    <td class="price">${c.price ? c.price.toFixed(0) + ' ₽' : '—'}</td>
                    <td class="rating">${c.rating ? '★ ' + c.rating : '—'}</td>
                    <td>${c.total_feedbacks_wb || 0}</td>
                    <td class="orders">${se.estimated_orders_30d_low ? se.estimated_orders_30d_low + '–' + se.estimated_orders_30d_high : '—'}</td>
                    <td class="price">${se.estimated_revenue_30d_low ? (se.estimated_revenue_30d_low/1000).toFixed(1) + '–' + (se.estimated_revenue_30d_high/1000).toFixed(1) + 'K ₽' : '—'}</td>
                </tr>
            `;
        });
        tableHTML += '</tbody></table></div>';
        competitorsDiv.innerHTML = '<h3>🏆 Топ конкуренты</h3>' + tableHTML;
    }
});
