function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T12:00:00Z");
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

const chartColors = {
  grid: "#e2e8f0",
  tick: "#475569",
  legend: "#334155",
  line30: "#db2777",
  fill30: "rgba(219, 39, 119, 0.14)",
  line15: "#2563eb",
  fill15: "rgba(37, 99, 235, 0.14)",
};

async function loadToday() {
  const res = await fetch("/api/rates/today");
  if (!res.ok) {
    document.getElementById("r30").textContent = "—";
    document.getElementById("r15").textContent = "—";
    document.getElementById("m30").textContent = "Unavailable";
    document.getElementById("m15").textContent = "";
    return;
  }
  const d = await res.json();
  document.getElementById("r30").textContent = Number(d.rate_30y).toFixed(2);
  document.getElementById("r15").textContent = Number(d.rate_15y).toFixed(2);
  document.getElementById("m30").textContent =
    "FRED observation " + fmtDate(d.fred_observation_date_30y);
  document.getElementById("m15").textContent =
    "FRED observation " + fmtDate(d.fred_observation_date_15y);
}

let chart;

function setChartLoading(on) {
  const overlay = document.getElementById("chartLoading");
  const wrap = document.getElementById("chartWrap");
  const sel = document.getElementById("range");
  if (on) {
    overlay.hidden = false;
    wrap.setAttribute("aria-busy", "true");
    sel.disabled = true;
  } else {
    overlay.hidden = true;
    wrap.setAttribute("aria-busy", "false");
    sel.disabled = false;
  }
}

function showChartError(msg) {
  const el = document.getElementById("chartErr");
  el.textContent = msg;
  el.hidden = !msg;
}

function buildChart(payload) {
  const s30 = payload.series_30y || [];
  const s15 = payload.series_15y || [];
  const labels = [...new Set([...s30.map((x) => x.date), ...s15.map((x) => x.date)])].sort();

  const map30 = Object.fromEntries(s30.map((x) => [x.date, x.value]));
  const map15 = Object.fromEntries(s15.map((x) => [x.date, x.value]));

  const data30 = labels.map((d) => (map30[d] != null ? map30[d] : null));
  const data15 = labels.map((d) => (map15[d] != null ? map15[d] : null));

  const ctx = document.getElementById("rateChart");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "30-year",
          data: data30,
          borderColor: chartColors.line30,
          backgroundColor: chartColors.fill30,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 5,
          spanGaps: true,
          tension: 0.25,
        },
        {
          label: "15-year",
          data: data15,
          borderColor: chartColors.line15,
          backgroundColor: chartColors.fill15,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 5,
          spanGaps: true,
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        y: {
          title: {
            display: true,
            text: "Rate (%)",
            color: chartColors.tick,
            font: { size: 12, weight: "600" },
          },
          ticks: {
            color: chartColors.tick,
            callback: (v) => v + "%",
          },
          grid: { color: chartColors.grid },
        },
        x: {
          ticks: { color: chartColors.tick, maxRotation: 45, minRotation: 0 },
          grid: { color: chartColors.grid },
        },
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: chartColors.legend,
            usePointStyle: true,
            padding: 16,
            font: { size: 13, weight: "600" },
          },
        },
      },
    },
  });
}

async function loadChart(range) {
  setChartLoading(true);
  showChartError("");
  try {
    const res = await fetch("/api/rates/chart?range=" + encodeURIComponent(range));
    if (!res.ok) {
      if (chart) chart.destroy();
      showChartError("Chart data unavailable. Check FRED API key and network.");
      return;
    }
    const payload = await res.json();
    buildChart(payload);
  } finally {
    setChartLoading(false);
  }
}

document.getElementById("range").addEventListener("change", (e) => {
  loadChart(e.target.value);
});

loadToday();
loadChart("30d");
