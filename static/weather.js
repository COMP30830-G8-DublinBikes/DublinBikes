const errorEl = document.getElementById("weatherError");

const summaryTemp = document.getElementById("summaryTemp");
const summaryDesc = document.getElementById("summaryDesc");
const summaryFeels = document.getElementById("summaryFeels");
const summaryHumidity = document.getElementById("summaryHumidity");
const summaryWind = document.getElementById("summaryWind");
const summaryMain = document.getElementById("summaryMain");
const summaryMainSub = document.getElementById("summaryMainSub");
const rideNote = document.getElementById("rideNote");

const verdictTitle = document.getElementById("verdictTitle");
const verdictSub = document.getElementById("verdictSub");

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
    renderRideSuitability(current);
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
  const conditionText = formatConditionText(weather.weather_main, weather.weather_description);
  const conditionLabel = formatConditionLabel(weather.weather_main, weather.weather_description);

  summaryTemp.textContent = formatRoundedTemp(weather.temp);
  summaryDesc.textContent = conditionText || "Current weather conditions";

  summaryFeels.textContent = formatRoundedTemp(weather.feels_like);
  summaryHumidity.textContent = formatPercent(weather.humidity);
  summaryWind.textContent = formatWind(weather.wind_speed);

  summaryMain.textContent = conditionLabel;
  if (summaryMainSub) {
    summaryMainSub.textContent = conditionText || "Current sky conditions";
  }
}

function renderRideSuitability(weather) {
  const main = String(weather.weather_main || "").toLowerCase();
  const temp = toNumberOrNull(weather.temp);
  const wind = toNumberOrNull(weather.wind_speed);
  const rain = toNumberOrNull(weather.rain_1h) ?? 0;

  let verdict = "Conditions updating";
  let cls = "good";
  let detail = "Live weather is being checked for your journey.";

  if (main.includes("thunder") || rain > 5 || (wind !== null && wind > 12)) {
    verdict = "Not recommended today";
    cls = "bad";
    detail = "Strong wind or heavy rain is expected, so postponing your ride would be safer.";
  } else if (main.includes("rain") || main.includes("drizzle") || (temp !== null && temp < 5) || (wind !== null && wind > 8)) {
    verdict = "Possible with precautions";
    cls = "ok";

    if (main.includes("rain") || main.includes("drizzle")) {
      detail = "Bring waterproofs and allow extra time for a wetter ride.";
    } else if (temp !== null && temp < 5) {
      detail = "Dress warmly and consider gloves before setting off.";
    } else {
      detail = "Conditions are manageable, but wind may make the ride feel less comfortable.";
    }
  } else {
    verdict = "Good conditions for cycling";
    cls = "good";

    if (temp !== null && temp >= 15) {
      detail = "Mild conditions should make for a comfortable city ride.";
    } else {
      detail = "Conditions look stable for riding across the city.";
    }
  }

  if (verdictTitle) {
    verdictTitle.textContent = verdict;
    verdictTitle.className = `verdict-title ${cls}`;
  }

  if (verdictSub) {
    verdictSub.textContent = detail;
  }
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
          tension: 0.35,
          fill: false,
          spanGaps: true
        },
        {
          label: "Max temperature (°C)",
          data: maxTemps,
          borderWidth: 2,
          tension: 0.35,
          fill: false,
          spanGaps: true
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
            label: (context) => {
              const value = toNumberOrNull(context.raw);
              if (value == null) return `${context.dataset.label}: --`;
              return `${context.dataset.label}: ${Math.round(value)}°C`;
            }
          }
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Temperature (°C)"
          },
          ticks: {
            callback: (value) => `${Math.round(value)}°`
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
          },
          ticks: {
            callback: (value) => `${Math.round(value)}%`
          }
        }
      }
    }
  });
}

function renderRideNote(current, days) {
  const main = String(current.weather_main || "").toLowerCase();
  const desc = formatConditionText(current.weather_main, current.weather_description) || "current conditions";
  const temp = toNumberOrNull(current.temp);

  let highestPop = 0;
  let wettestDayLabel = null;

  for (const day of days) {
    const popValue = toNumberOrNull(day.pop_max);
    if (popValue != null && popValue > highestPop) {
      highestPop = popValue;
      wettestDayLabel = formatDateLabel(day.date);
    }
  }

  const popPercent = Math.round(highestPop * 100);
  let message = `Current weather is ${desc.toLowerCase()}. `;

  if (main.includes("rain") || main.includes("drizzle")) {
    message += "Cycling is still possible, but waterproof clothing is recommended. ";
  } else if (temp != null && temp <= 5) {
    message += "It is quite cold, so gloves and an extra layer would be sensible. ";
  } else if (temp != null && temp >= 18) {
    message += "Conditions are relatively mild for a city ride. ";
  } else {
    message += "Conditions look generally manageable for cycling. ";
  }

  if (wettestDayLabel && popPercent > 0) {
    message += `The highest forecast precipitation probability is ${popPercent}% on ${wettestDayLabel}.`;
  } else {
    message += "Rain risk remains low across the available forecast.";
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

  if (summaryMainSub) {
    summaryMainSub.textContent = "Current sky conditions unavailable";
  }

  if (verdictTitle) {
    verdictTitle.textContent = "Weather data unavailable";
    verdictTitle.className = "verdict-title";
  }

  if (verdictSub) {
    verdictSub.textContent = "The riding recommendation could not be generated because the weather API did not respond.";
  }

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

function formatRoundedTemp(value) {
  const num = toNumberOrNull(value);
  return num == null ? "--°C" : `${Math.round(num)}°C`;
}

function formatPercent(value) {
  const num = toNumberOrNull(value);
  return num == null ? "--%" : `${Math.round(num)}%`;
}

function formatWind(value) {
  const num = toNumberOrNull(value);
  return num == null ? "-- m/s" : `${num.toFixed(1)} m/s`;
}

function formatConditionLabel(main, desc) {
  const key = String(main || "").toLowerCase().trim();

  const map = {
    clear: "Clear",
    clouds: "Cloudy",
    rain: "Rainy",
    drizzle: "Drizzly",
    thunderstorm: "Stormy",
    snow: "Snowy",
    mist: "Misty",
    haze: "Hazy",
    fog: "Foggy",
    smoke: "Smoky"
  };

  if (map[key]) return map[key];

  const fallback = desc || main;
  return fallback ? capitalizeWords(String(fallback)) : "N/A";
}

function formatConditionText(main, desc) {
  const fallback = String(desc || main || "").replace(/_/g, " ").trim();
  return fallback ? capitalizeWords(fallback) : "";
}

function capitalizeWords(text) {
  return String(text)
    .toLowerCase()
    .replace(/\b[a-z]/g, (char) => char.toUpperCase());
}

function toNumberOrNull(value) {
  if (value == null || value === "") return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
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