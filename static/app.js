const pill = document.getElementById("weather-pill");
const drawer = document.getElementById("drawer");
const backdrop = document.getElementById("drawer-backdrop");
const closeBtn = document.getElementById("drawer-close");

const wxTemp = document.getElementById("wx-temp");
const wxPop  = document.getElementById("wx-pop");
const wxIcon = document.getElementById("wx-icon");

const drawerCurrent = document.getElementById("drawer-current");
const drawerForecast = document.getElementById("drawer-forecast");

function openDrawer() {
  drawer.classList.add("open");
  backdrop.classList.add("open");
}
function closeDrawer() {
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
}

if (pill) pill.addEventListener("click", async () => {
  openDrawer();
  await refreshDrawer();
});

if (backdrop) backdrop.addEventListener("click", closeDrawer);
if (closeBtn) closeBtn.addEventListener("click", closeDrawer);

function iconFromMain(main) {
  const m = (main || "").toLowerCase();
  if (m.includes("rain")) return "🌧️";
  if (m.includes("cloud")) return "☁️";
  if (m.includes("clear")) return "☀️";
  if (m.includes("snow")) return "❄️";
  if (m.includes("storm") || m.includes("thunder")) return "⛈️";
  return "🌤️";
}

async function refreshTopPill() {
  try {
    const r1 = await fetch("/api/weather/current");
    const current = await r1.json();

    if (current && current.main && typeof current.main.temp !== "undefined") {
      wxTemp.textContent = `${Math.round(current.main.temp)}°C`;
      wxIcon.textContent = iconFromMain(current.weather?.[0]?.main);
    }

    const r2 = await fetch("/api/weather/forecast");
    const fc = await r2.json();
    const today = (fc.days || [])[0];
    if (today && typeof today.pop_max !== "undefined") {
      wxPop.textContent = `${Math.round(today.pop_max * 100)}% rain`;
    }
  } catch (e) {
    wxTemp.textContent = "--°C";
    wxPop.textContent = "--% rain";
  }
}

function renderForecast(days) {
  drawerForecast.innerHTML = "";
  if (!days || days.length === 0) {
    drawerForecast.textContent = "No forecast available.";
    return;
  }

  for (const d of days) {
    const div = document.createElement("div");
    div.className = "forecast-item";
    div.innerHTML = `
      <div class="left">
        <div class="date">${d.date}</div>
        <div class="desc">POP max: ${d.pop_max != null ? Math.round(d.pop_max*100) + "%" : "n/a"}</div>
      </div>
      <div style="text-align:right;">
        <div><strong>${d.temp_max ?? "n/a"}°</strong></div>
        <div class="small">${d.temp_min ?? "n/a"}°</div>
      </div>
    `;
    drawerForecast.appendChild(div);
  }
}

async function refreshDrawer() {
  try {
    drawerCurrent.textContent = "Loading...";
    drawerForecast.textContent = "Loading...";

    const r1 = await fetch("/api/weather/current");
    const current = await r1.json();
    drawerCurrent.textContent = JSON.stringify(current, null, 2);

    const r2 = await fetch("/api/weather/forecast");
    const fc = await r2.json();
    renderForecast(fc.days || []);
  } catch (e) {
    drawerCurrent.textContent = "Failed to load weather.";
    drawerForecast.textContent = "Failed to load forecast.";
  }
}


refreshTopPill();

async function loadStationCard(stationNumber = 42) {

  // 读取实时 bikes 数据
  const r = await fetch("/api/bikes/current");
  const stations = await r.json();

  const s = stations.find(x => x.number === stationNumber);
  if (!s) return;

  document.getElementById("bikesAvailable").textContent =
      s.available_bikes ?? "-";

  document.getElementById("docksAvailable").textContent =
      s.available_bike_stands ?? "-";
}

window.addEventListener("load", () => {
  loadStationCard(42);
});