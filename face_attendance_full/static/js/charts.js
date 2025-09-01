function renderLineChart(ctxId, labels, data) {
  const ctx = document.getElementById(ctxId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Attendance %',
        data: data,
        fill: false,
        tension: 0.25
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: { y: { beginAtZero: true, max: 100 } }
    }
  });
}
