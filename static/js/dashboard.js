let currentCharts = {};

document.addEventListener('DOMContentLoaded', () => {
    loadNiches();
});

async function loadNiches() {
    try {
        const resp = await fetch('/api/niches?limit=50');
        const data = await resp.json();
        const tbody = document.querySelector('#nichesTable tbody');
        tbody.innerHTML = '';

        data.items.forEach(n => {
            const f = n.forecast || {};
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${n.id}</td>
                <td><strong>${n.query}</strong></td>
                <td>${n.analyzed_at ? new Date(n.analyzed_at).toLocaleDateString('ru-RU') : '—'}</td>
                <td>${n.competitors_analyzed || 0}</td>
                <td>${n.avg_price ? n.avg_price.toFixed(0) + ' ₽' : '—'}</td>
                <td>${n.median_orders_30d_low ? n.median_orders_30d_low + '–' + n.median_orders_30d_high : '—'}</td>
                <td class="success">${f.realistic_revenue_30d ? f.realistic_revenue_30d.toLocaleString('ru-RU') + ' ₽' : '—'}</td>
                <td><button class="btn btn-small btn-primary" onclick="showDetail(${n.id})">Открыть</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Failed to load niches', e);
    }
}

async function showDetail(nicheId) {
    try {
        const resp = await fetch(`/api/niche/${nicheId}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Error');

        document.getElementById('detail-title').textContent = `Ниша: ${data.query}`;
        const ms = data.market_summary || {};
        const nf = ms.new_product_forecast || {};

        document.getElementById('d-avg-price').textContent = ms.avg_price ? ms.avg_price.toFixed(0) + ' ₽' : '—';
        document.getElementById('d-price-range').textContent = (ms.min_price && ms.max_price) ? `${ms.min_price.toFixed(0)} – ${ms.max_price.toFixed(0)} ₽` : '—';
        document.getElementById('d-median-orders').textContent = ms.median_orders_30d_low ? `${ms.median_orders_30d_low} – ${ms.median_orders_30d_high} шт/мес` : '—';
        document.getElementById('d-forecast').textContent = nf.realistic_revenue_30d ? nf.realistic_revenue_30d.toLocaleString('ru-RU') + ' ₽/мес' : '—';

        renderCharts(data);

        const cbody = document.querySelector('#competitorsTable tbody');
        cbody.innerHTML = '';
        (data.competitors || []).forEach(c => {
            const se = c.sales_estimate || {};
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><a href="https://www.wildberries.ru/catalog/${c.article_id}/detail.aspx" target="_blank" style="color:var(--accent);text-decoration:none">${c.article_id}</a></td>
                <td>${c.name ? c.name.substring(0, 55) + (c.name.length > 55 ? '...' : '') : '—'}</td>
                <td>${c.brand || '—'}</td>
                <td class="price">${c.price ? c.price.toFixed(0) + ' ₽' : '—'}</td>
                <td class="rating">${c.rating ? '★ ' + c.rating : '—'}</td>
                <td>${se.reviews_last_30d || 0}</td>
                <td class="orders">${se.estimated_orders_30d_low ? se.estimated_orders_30d_low + '–' + se.estimated_orders_30d_high : '—'}</td>
                <td class="price">${se.estimated_revenue_30d_low ? (se.estimated_revenue_30d_low/1000).toFixed(1) + '–' + (se.estimated_revenue_30d_high/1000).toFixed(1) + 'K ₽' : '—'}</td>
            `;
            cbody.appendChild(tr);
        });

        document.getElementById('detail-view').classList.remove('hidden');
        document.getElementById('niches-list').classList.add('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
        alert('Ошибка загрузки: ' + e.message);
    }
}

function closeDetail() {
    document.getElementById('detail-view').classList.add('hidden');
    document.getElementById('niches-list').classList.remove('hidden');
    Object.values(currentCharts).forEach(c => c.destroy());
    currentCharts = {};
}

function renderCharts(data) {
    const comps = data.competitors || [];
    const labels = comps.map((c, i) => (c.brand || 'Бренд') + ' #' + (i+1));
    const prices = comps.map(c => c.price || 0);
    const revLow = comps.map(c => (c.sales_estimate && c.sales_estimate.estimated_revenue_30d_low) || 0);
    const revHigh = comps.map(c => (c.sales_estimate && c.sales_estimate.estimated_revenue_30d_high) || 0);
    const orders = comps.map(c => (c.sales_estimate && c.sales_estimate.estimated_orders_30d_low) || 0);

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#f1f5f9' } }
        },
        scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
        }
    };

    const ctx1 = document.getElementById('priceChart').getContext('2d');
    currentCharts.price = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Цена, ₽',
                data: prices,
                backgroundColor: 'rgba(99,102,241,0.7)',
                borderColor: '#6366f1',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: commonOptions
    });

    const ctx2 = document.getElementById('revenueChart').getContext('2d');
    currentCharts.revenue = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Выручка/мес min, ₽',
                    data: revLow,
                    backgroundColor: 'rgba(52,211,153,0.6)',
                    borderColor: '#34d399',
                    borderWidth: 1,
                    borderRadius: 6
                },
                {
                    label: 'Выручка/мес max, ₽',
                    data: revHigh,
                    backgroundColor: 'rgba(34,211,238,0.6)',
                    borderColor: '#22d3ee',
                    borderWidth: 1,
                    borderRadius: 6
                }
            ]
        },
        options: commonOptions
    });

    const ctx3 = document.getElementById('scatterChart').getContext('2d');
    currentCharts.scatter = new Chart(ctx3, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Конкуренты',
                data: comps.map(c => ({
                    x: c.price || 0,
                    y: (c.sales_estimate && c.sales_estimate.estimated_orders_30d_low) || 0,
                    label: (c.brand || 'Бренд') + ' ' + (c.article_id || '')
                })),
                backgroundColor: 'rgba(251,191,36,0.7)',
                borderColor: '#fbbf24',
                borderWidth: 1,
                pointRadius: 6,
                pointHoverRadius: 10
            }]
        },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const pt = ctx.raw;
                            return `${pt.label}: Цена ${pt.x}₽, Заказов ${pt.y}/мес`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ...commonOptions.scales.x,
                    title: { display: true, text: 'Цена, ₽', color: '#94a3b8' }
                },
                y: {
                    ...commonOptions.scales.y,
                    title: { display: true, text: 'Заказов/мес (оценка)', color: '#94a3b8' }
                }
            }
        }
    });
}
