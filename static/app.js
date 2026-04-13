const pill = document.getElementById("weather-pill");
const drawer = document.getElementById("drawer");
const backdrop = document.getElementById("drawer-backdrop");
const closeBtn = document.getElementById("drawer-close");

const wxTemp = document.getElementById("wx-temp");
const wxPop = document.getElementById("wx-pop");
const wxIcon = document.getElementById("wx-icon");

const drawerCurrent = document.getElementById("drawer-current");
const drawerForecast = document.getElementById("drawer-forecast");

function openDrawer() {
  if (!drawer || !backdrop) return;
  drawer.classList.add("open");
  backdrop.classList.add("open");
}

function closeDrawer() {
  if (!drawer || !backdrop) return;
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
}

if (pill && drawer) {
  pill.addEventListener("click", async () => {
    openDrawer();
    await refreshDrawer();
  });
}

if (backdrop) backdrop.addEventListener("click", closeDrawer);
if (closeBtn) closeBtn.addEventListener("click", closeDrawer);

function iconFromWeather(main, description) {
  const text = `${main || ""} ${description || ""}`.toLowerCase();
  if (text.includes("rain")) return "🌧️";
  if (text.includes("drizzle")) return "🌦️";
  if (text.includes("cloud")) return "☁️";
  if (text.includes("clear")) return "☀️";
  if (text.includes("snow")) return "❄️";
  if (text.includes("storm") || text.includes("thunder")) return "⛈️";
  if (text.includes("mist") || text.includes("fog")) return "🌫️";
  return "🌤️";
}

async function fetchCurrentWeather() {
  const response = await fetch("/api/weather/current");
  const result = await response.json();
  if (!result.ok || !result.data) {
    throw new Error(result.error || "Current weather unavailable.");
  }
  return result.data;
}

async function fetchForecastWeather() {
  const response = await fetch("/api/weather/forecast");
  const result = await response.json();
  if (!result.ok || !result.data) {
    throw new Error(result.error || "Forecast weather unavailable.");
  }
  return result.data;
}

async function refreshTopPill() {
  try {
    const current = await fetchCurrentWeather();

    if (wxTemp) {
      wxTemp.textContent = current.temp == null ? "--°C" : `${current.temp}°C`;
    }

    if (wxIcon) {
      wxIcon.textContent = iconFromWeather(current.weather_main, current.weather_description);
    }

    if (wxPop) {
      if (current.rain_1h != null) {
        wxPop.textContent = `${current.rain_1h} mm rain`;
      } else {
        wxPop.textContent = current.weather_description || current.weather_main || "Live weather";
      }
    }
  } catch (error) {
    console.error("Top weather pill load failed:", error);
    if (wxTemp) wxTemp.textContent = "--°C";
    if (wxPop) wxPop.textContent = "Weather unavailable";
  }
}

function renderForecast(days) {
  if (!drawerForecast) return;

  drawerForecast.innerHTML = "";

  if (!days || days.length === 0) {
    drawerForecast.textContent = "No forecast available.";
    return;
  }

  for (const day of days) {
    const div = document.createElement("div");
    div.className = "forecast-item";
    div.innerHTML = `
      <div class="left">
        <div class="date">${day.date || "N/A"}</div>
        <div class="desc">POP max: ${day.pop_max != null ? Math.round(day.pop_max * 100) + "%" : "N/A"}</div>
      </div>
      <div style="text-align:right;">
        <div><strong>${day.temp_max ?? "N/A"}°</strong></div>
        <div class="small">${day.temp_min ?? "N/A"}°</div>
      </div>
    `;
    drawerForecast.appendChild(div);
  }
}

async function refreshDrawer() {
  if (!drawerCurrent || !drawerForecast) return;

  try {
    drawerCurrent.innerHTML = "Loading...";
    drawerForecast.innerHTML = "Loading...";

    const [current, forecast] = await Promise.all([
      fetchCurrentWeather(),
      fetchForecastWeather()
    ]);

    drawerCurrent.innerHTML = `
      <strong>Current weather</strong><br><br>
      Temperature: ${current.temp ?? "N/A"}°C<br>
      Feels like: ${current.feels_like ?? "N/A"}°C<br>
      Condition: ${current.weather_main ?? "N/A"} (${current.weather_description ?? "N/A"})<br>
      Humidity: ${current.humidity ?? "N/A"}%<br>
      Wind speed: ${current.wind_speed ?? "N/A"} m/s<br>
      Rain (1h): ${current.rain_1h == null ? "N/A" : `${current.rain_1h} mm`}
    `;

    renderForecast(forecast.days || []);
  } catch (error) {
    console.error("Drawer weather load failed:", error);
    drawerCurrent.textContent = "Failed to load current weather.";
    drawerForecast.textContent = "Failed to load forecast.";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  refreshTopPill();
});