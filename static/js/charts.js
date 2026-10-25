// Shared Chart.js setup: one palette and one set of defaults for every chart in the app.

const GYM_COLORS = {
    accent: '#ff6b00',  // electric orange (brand accent, series 1)
    blue: '#1f6feb',    // series 2
    teal: '#12a594',    // series 3
    amber: '#e0a400',   // series 4
    grey: '#9aa0a6',    // "none" / remainder
    text: '#52525b',
    grid: 'rgba(0, 0, 0, 0.06)',
};
const GYM_SERIES = [GYM_COLORS.accent, GYM_COLORS.blue, GYM_COLORS.teal, GYM_COLORS.amber];

const rupees = value => '₹' + Number(value).toLocaleString('en-IN');

(function applyChartDefaults() {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.color = GYM_COLORS.text;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.borderColor = GYM_COLORS.grid;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
    Chart.defaults.plugins.tooltip.backgroundColor = '#1c1c1e';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    if (reduceMotion) Chart.defaults.animation = false;
})();

// "Gym Progress - Last 12 Months": cumulative members (left axis) and monthly revenue (right axis)
function renderProgressChart(canvas, data) {
    const membersFill = context => {
        const { ctx, chartArea } = context.chart;
        if (!chartArea) return 'rgba(255, 107, 0, 0.15)';
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, 'rgba(255, 107, 0, 0.28)');
        gradient.addColorStop(1, 'rgba(255, 107, 0, 0)');
        return gradient;
    };
    const line = color => ({
        borderColor: color, backgroundColor: color, borderWidth: 2, tension: 0.35,
        pointRadius: 4, pointHoverRadius: 6, pointBackgroundColor: '#fff', pointBorderColor: color, pointBorderWidth: 2,
    });

    return new Chart(canvas, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                { ...line(GYM_COLORS.accent), label: 'Total members', data: data.members, yAxisID: 'members',
                  fill: 'origin', backgroundColor: membersFill },
                { ...line(GYM_COLORS.blue), label: 'Monthly revenue (₹)', data: data.revenue, yAxisID: 'revenue' },
            ],
        },
        options: {
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { display: false } },
                members: { position: 'left', beginAtZero: true, ticks: { precision: 0 },
                           title: { display: true, text: 'Members' } },
                revenue: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false },
                           ticks: { callback: rupees }, title: { display: true, text: 'Revenue' } },
            },
            plugins: {
                legend: { position: 'top', align: 'end' },
                tooltip: { callbacks: {
                    label: ctx => ctx.dataset.yAxisID === 'revenue'
                        ? ` Revenue: ${rupees(ctx.parsed.y)}`
                        : ` Members: ${ctx.parsed.y.toLocaleString('en-IN')}`,
                } },
            },
        },
    });
}
