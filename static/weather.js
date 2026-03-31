const errorEl = document.getElementById("weatherError");

const summaryTemp = document.getElementById("summaryTemp");
const summaryDesc = document.getElementById("summaryDesc");
const summaryFeels = document.getElementById("summaryFeels");
const summaryHumidity = document.getElementById("summaryHumidity");
const summaryWind = document.getElementById("summaryWind");
const summaryMain = document.getElementById("summaryMain");
const rideNote = document.getElementById("rideNote");

let tempChart = null;
let popChart = null;

document.addEventListener("DOMContentLoaded", async () => {
  await loadWeatherDashboard();
});

async function loadWeatherDashboard() {
  try {
    const [currentResult, forecastResult] = await Promise.all([
      fetch("/api/weather/current").then((res) => res.json()),
      fetch("/api/weather/forecast").then((res) => res.json())
    ]);

    if (!currentResult.ok || !currentResult.data) {
      throw new Error(currentResult.error || "Current weather data unavailable.");
    }

    if (!forecastResult.ok || !forecastResult.data) {
      throw new Error(forecastResult.error || "Forecast weather data unavailable.");
    }

    const current = currentResult.data;
    const days = forecastResult.data.days || [];

    renderSummary(current);
    renderTempChart(days);
    renderPopChart(days);
    renderRideNote(current, days);
    hideError();
  } catch (error) {
    console.error("Weather dashboard load failed:", error);
    showError(error.message || "Failed to load weather dashboard.");
    renderFallbackState();
  }
}

function renderSummary(weather) {
  summaryTemp.textContent = formatTemp(weather.temp);
  summaryDesc.textContent = weather.weather_description || weather.weather_main || "No description";

  summaryFeels.textContent = formatTemp(weather.feels_like);
  summaryHumidity.textContent = `${safeNumber(weather.humidity, "--")}%`;
  summaryWind.textContent = `${safeNumber(weather.wind_speed, "--")} m/s`;
  summaryMain.textContent = weather.weather_main || "N/A";
}

function renderTempChart(days) {
  const ctx = document.getElementById("tempChart");
  if (!ctx) return;

  const labels = days.map((day) => formatDateLabel(day.date));
  const minTemps = days.map((day) => toNumberOrNull(day.temp_min));
  const maxTemps = days.map((day) => toNumberOrNull(day.temp_max));

  if (tempChart) {
    tempChart.destroy();
  }

  tempChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Min temperature (°C)",
          data: minTemps,
          borderWidth: 2,
          tension: 0.3,
          fill: false
        },
        {
          label: "Max temperature (°C)",
          data: maxTemps,
          borderWidth: 2,
          tension: 0.3,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.raw}°C`
          }
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Temperature (°C)"
          }
        }
      }
    }
  });
}

function renderPopChart(days) {
  const ctx = document.getElementById("popChart");
  if (!ctx) return;

  const labels = days.map((day) => formatDateLabel(day.date));
  const pops = days.map((day) => {
    const value = toNumberOrNull(day.pop_max);
    if (value == null) return null;
    return Math.round(value * 100);
  });

  if (popChart) {
    popChart.destroy();
  }

  popChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Precipitation probability (%)",
          data: pops,
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.raw}%`
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          title: {
            display: true,
            text: "Probability (%)"
          }
        }
      }
    }
  });
}

function renderRideNote(current, days) {
  const main = (current.weather_main || "").toLowerCase();
  const desc = current.weather_description || "current conditions";
  const temp = toNumberOrNull(current.temp);

  let highestPop = 0;
  let wettestDay = null;

  for (const day of days) {
    const popValue = toNumberOrNull(day.pop_max);
    if (popValue != null && popValue > highestPop) {
      highestPop = popValue;
      wettestDay = day.date;
    }
  }

  const popPercent = Math.round(highestPop * 100);

  let message = `Current weather is ${desc}. `;

  if (main.includes("rain") || main.includes("drizzle")) {
    message += "Cycling is still possible, but waterproof clothing is recommended. ";
  } else if (temp != null && temp <= 5) {
    message += "It is quite cold, so gloves and extra layers would be sensible. ";
  } else if (temp != null && temp >= 18) {
    message += "Conditions are relatively mild for a city ride. ";
  } else {
    message += "Conditions look generally manageable for cycling. ";
  }

  if (wettestDay) {
    message += `The highest forecast precipitation probability is ${popPercent}% on ${wettestDay}.`;
  } else {
    message += "No strong precipitation signal appears in the available forecast.";
  }

  rideNote.textContent = message;
}

function renderFallbackState() {
  summaryTemp.textContent = "--°C";
  summaryDesc.textContent = "Weather data unavailable";
  summaryFeels.textContent = "--°C";
  summaryHumidity.textContent = "--%";
  summaryWind.textContent = "-- m/s";
  summaryMain.textContent = "--";
  rideNote.textContent = "Weather interpretation is unavailable because the API response could not be loaded.";

  if (tempChart) {
    tempChart.destroy();
    tempChart = null;
  }

  if (popChart) {
    popChart.destroy();
    popChart = null;
  }
}

function showError(message) {
  if (!errorEl) return;
  errorEl.style.display = "block";
  errorEl.textContent = message;
}

function hideError() {
  if (!errorEl) return;
  errorEl.style.display = "none";
  errorEl.textContent = "";
}

function formatTemp(value) {
  const num = toNumberOrNull(value);
  return num == null ? "--°C" : `${num}°C`;
}

function safeNumber(value, fallback = "N/A") {
  const num = toNumberOrNull(value);
  return num == null ? fallback : num;
}

function toNumberOrNull(value) {
  if (value == null || value === "") return null;
  const num = Number(value);
  return Number.isNaN(num) ? null : Number(num.toFixed(2));
}

function formatDateLabel(dateString) {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  return date.toLocaleDateString("en-IE", {
    weekday: "short",
    month: "short",
    day: "numeric"
  });
}