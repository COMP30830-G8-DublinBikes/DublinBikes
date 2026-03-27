const USE_MOCK_DATA = false;
const AUTO_REFRESH_MS = 60000;

let map = null;
let markers = [];
let historyChart = null;
let allStations = [];
let displayedStations = [];
let selectedStationId = null;
let selectedSeries = "occupancy";
let refreshTimer = null;

const DEFAULT_CENTER = [53.3498, -6.2603];
const DEFAULT_ZOOM = 13;

window.addEventListener("DOMContentLoaded", async () => {
  bindSearch();
  bindTrendToggles();
  bindAssistantRefresh();
  initMap();
  await Promise.all([
    loadSessionState(),
    loadWeather(),
    loadStations(true)
  ]);
  startAutoRefresh();
});

function initMap() {
  const mapElement = document.getElementById("map");
  if (!mapElement) return;

  map = L.map("map", { zoomControl: true }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  setTimeout(() => map.invalidateSize(), 120);
}

function bindSearch() {
  const searchInput = document.getElementById("stationSearchInput");
  if (!searchInput) return;

  searchInput.addEventListener("input", async (event) => {
    const keyword = event.target.value.trim().toLowerCase();
    displayedStations = allStations.filter((station) => {
      const name = String(station.name || "").toLowerCase();
      const address = String(station.address || "").toLowerCase();
      return !keyword || name.includes(keyword) || address.includes(keyword);
    });

    renderMarkers(displayedStations);
    updateMapSummary(displayedStations);

    if (!displayedStations.length) {
      renderStationEmpty("No stations match your search.");
      renderHistoryEmpty("No trend data available for the current search result.");
      renderAssistantEmpty("No station is currently selected for assistant advice.");
      return;
    }

    const stillVisible = displayedStations.some(
      (station) => Number(station.station_id) === Number(selectedStationId)
    );

    if (!stillVisible) {
      await selectStation(displayedStations[0].station_id);
    }
  });
}

function bindTrendToggles() {
  document.querySelectorAll("[data-series]").forEach((button) => {
    button.addEventListener("click", async () => {
      selectedSeries = button.dataset.series || "occupancy";
      document.querySelectorAll("[data-series]").forEach((btn) => btn.classList.remove("active"));
      button.classList.add("active");

      if (selectedStationId != null) {
        await loadHistory(selectedStationId);
      }
    });
  });
}

function bindAssistantRefresh() {
  const refreshBtn = document.getElementById("refreshAdviceBtn");
  if (!refreshBtn) return;

  refreshBtn.addEventListener("click", async () => {
    if (selectedStationId == null) {
      renderAssistantEmpty("Select a station before requesting assistant advice.");
      return;
    }
    await loadAssistantAdvice(selectedStationId);
  });
}

function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  refreshTimer = setInterval(async () => {
    await Promise.all([
      loadWeather(),
      loadStations(false)
    ]);
  }, AUTO_REFRESH_MS);
}

async function loadSessionState() {
  const sessionPill = document.getElementById("sessionPill");
  if (!sessionPill) return;

  try {
    const response = await fetch("/api/auth/me");
    const result = await response.json();

    if (result.authenticated && result.user) {
      sessionPill.textContent = `Signed in: ${result.user.username}`;
      sessionPill.classList.add("signed-in");
    } else {
      sessionPill.textContent = "Guest session";
      sessionPill.classList.remove("signed-in");
    }
  } catch (error) {
    console.error("Failed to load session state:", error);
    sessionPill.textContent = "Session unknown";
    sessionPill.classList.remove("signed-in");
  }
}

async function loadWeather() {
  try {
    const response = await fetch("/api/weather/current");
    const result = await response.json();
    const weather = result.data;

    if (!result.ok || !weather) {
      renderWeatherUnavailable();
      return;
    }

    renderWeatherCard(weather);
    renderWeatherPill(weather);
  } catch (error) {
    console.error("Weather load failed:", error);
    renderWeatherUnavailable();
  }
}

function renderWeatherCard(weather) {
  const weatherCard = document.getElementById("weather-card");
  if (!weatherCard) return;

  weatherCard.innerHTML = `
    <h2>Current Weather</h2>
    <p><strong>Description:</strong> ${safeValue(weather.weather_description)}</p>
    <div class="weather-grid">
      <div class="weather-mini">
        <div class="label">Temperature</div>
        <div class="value">${safeValue(weather.temp)}°C</div>
      </div>
      <div class="weather-mini">
        <div class="label">Feels like</div>
        <div class="value">${safeValue(weather.feels_like)}°C</div>
      </div>
      <div class="weather-mini">
        <div class="label">Humidity</div>
        <div class="value">${safeValue(weather.humidity)}%</div>
      </div>
      <div class="weather-mini">
        <div class="label">Wind speed</div>
        <div class="value">${safeValue(weather.wind_speed)} m/s</div>
      </div>
    </div>
    <p><strong>Condition:</strong> ${safeValue(weather.weather_main)}</p>
    <p><strong>Rain (1h):</strong> ${weather.rain_1h == null ? "N/A" : `${weather.rain_1h} mm`}</p>
  `;
}

function renderWeatherPill(weather) {
  const iconEl = document.getElementById("wx-icon");
  const tempEl = document.getElementById("wx-temp");
  const popEl = document.getElementById("wx-pop");

  if (iconEl) iconEl.textContent = getWeatherEmoji(weather.weather_main, weather.weather_description);
  if (tempEl) tempEl.textContent = `${safeValue(weather.temp)}°C`;

  if (popEl) {
    if (weather.rain_1h != null) {
      popEl.textContent = `${weather.rain_1h} mm rain`;
    } else {
      popEl.textContent = safeValue(weather.weather_description);
    }
  }
}

function renderWeatherUnavailable() {
  const weatherCard = document.getElementById("weather-card");
  if (weatherCard) {
    weatherCard.innerHTML = `
      <h2>Current Weather</h2>
      <p>Weather data unavailable.</p>
    `;
  }

  const tempEl = document.getElementById("wx-temp");
  const popEl = document.getElementById("wx-pop");
  if (tempEl) tempEl.textContent = "--°C";
  if (popEl) popEl.textContent = "Weather unavailable";
}

async function loadStations(initialLoad = false) {
  try {
    let rows = [];

    if (USE_MOCK_DATA) {
      rows = [];
    } else {
      const response = await fetch("/api/bike/all");
      const result = await response.json();
      rows = result.rows || [];
    }

    allStations = rows.filter((row) => row.latitude != null && row.longitude != null);

    const keyword = String(document.getElementById("stationSearchInput")?.value || "").trim().toLowerCase();
    displayedStations = allStations.filter((station) => {
      const name = String(station.name || "").toLowerCase();
      const address = String(station.address || "").toLowerCase();
      return !keyword || name.includes(keyword) || address.includes(keyword);
    });

    renderMarkers(displayedStations);
    updateMapSummary(displayedStations);
    updateRefreshStamp();

    if (!displayedStations.length) {
      renderStationEmpty("No station data available yet.");
      renderHistoryEmpty("No historical data available.");
      renderAssistantEmpty("No station selected for assistant advice.");
      return;
    }

    const selectedStillExists = displayedStations.some(
      (station) => Number(station.station_id) === Number(selectedStationId)
    );

    if (initialLoad || !selectedStillExists) {
      await selectStation(displayedStations[0].station_id);
      return;
    }

    const currentStation = displayedStations.find(
      (station) => Number(station.station_id) === Number(selectedStationId)
    );

    if (currentStation) {
      renderStationCard(currentStation);
    }
  } catch (error) {
    console.error("Station load failed:", error);
    clearMarkers();
    resetMapView();
    renderStationEmpty("Failed to load station data.");
    renderHistoryEmpty("Failed to load historical data.");
    renderAssistantEmpty("Assistant advice is unavailable because station data failed to load.");
  }
}

function updateMapSummary(rows) {
  const stationCountChip = document.getElementById("stationCountChip");
  const availableBikeChip = document.getElementById("availableBikeChip");

  if (stationCountChip) {
    stationCountChip.textContent = `Stations: ${rows.length}`;
  }

  if (availableBikeChip) {
    const totalBikes = rows.reduce((sum, row) => sum + Number(row.available_bikes || 0), 0);
    availableBikeChip.textContent = `Available bikes: ${totalBikes}`;
  }
}

function updateRefreshStamp() {
  const chip = document.getElementById("lastRefreshChip");
  if (!chip) return;

  const now = new Date();
  chip.textContent = `Last refresh: ${now.toLocaleTimeString("en-IE", { hour: "2-digit", minute: "2-digit" })}`;
}

function renderMarkers(rows) {
  if (!map) return;

  clearMarkers();
  const bounds = [];

  rows.forEach((row) => {
    const lat = Number(row.latitude);
    const lng = Number(row.longitude);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    const color = getMarkerColor(row.available_bikes, row.capacity);

    const marker = L.circleMarker([lat, lng], {
      radius: Number(row.station_id) === Number(selectedStationId) ? 12 : 10,
      color: "#ffffff",
      weight: 2,
      fillColor: color,
      fillOpacity: 1
    }).addTo(map);

    marker.bindPopup(`
      <div style="min-width: 180px; line-height: 1.6;">
        <strong>${safeValue(row.name)}</strong><br>
        ${safeValue(row.address)}<br><br>
        Bikes: ${safeValue(row.available_bikes)}<br>
        Docks: ${safeValue(row.available_bike_stands)}<br>
        Status: ${safeValue(row.status)}
      </div>
    `);

    marker.on("click", async () => {
      await selectStation(row.station_id);
    });

    markers.push(marker);
    bounds.push([lat, lng]);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 15
    });
  } else {
    resetMapView();
  }
}

async function selectStation(stationId) {
  selectedStationId = Number(stationId);

  const station = allStations.find((row) => Number(row.station_id) === Number(selectedStationId));
  if (!station) return;

  renderMarkers(displayedStations.length ? displayedStations : allStations);
  renderStationCard(station);
  await Promise.all([
    loadHistory(selectedStationId),
    loadAssistantAdvice(selectedStationId)
  ]);
}

function clearMarkers() {
  markers.forEach((marker) => marker.remove());
  markers = [];
}

function resetMapView() {
  if (!map) return;
  map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
}

function renderStationCard(row) {
  const stationCard = document.getElementById("station-card");
  if (!stationCard) return;

  const capacity = Number(row.capacity || 0);
  const bikes = Number(row.available_bikes || 0);
  const occupancy = capacity > 0 ? Math.round((bikes / capacity) * 100) : 0;
  const statusText = getAvailabilityText(row.available_bikes, row.capacity);

  const directionsUrl =
    row.latitude != null && row.longitude != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${row.latitude},${row.longitude}&travelmode=bicycling`
      : "#";

  stationCard.innerHTML = `
    <h2>${safeValue(row.name)}</h2>
    <p>${safeValue(row.address)}</p>

    <div class="station-status">${statusText}</div>

    <div class="station-meta">
      <div class="metric-box">
        <div class="label">Bikes Available</div>
        <div class="value">${safeValue(row.available_bikes)}</div>
      </div>
      <div class="metric-box">
        <div class="label">Docks Available</div>
        <div class="value">${safeValue(row.available_bike_stands)}</div>
      </div>
    </div>

    <p><strong>Total Capacity:</strong> ${safeValue(row.capacity)}</p>
    <p><strong>Occupancy:</strong> ${occupancy}%</p>
    <p><strong>Status:</strong> ${safeValue(row.status)}</p>
    <p><strong>Last Update:</strong> ${safeValue(row.last_update)}</p>
    <p><strong>Mechanical Bikes:</strong> ${safeValue(row.mechanical_bikes)}</p>
    <p><strong>Electrical Bikes:</strong> ${safeValue(row.electrical_bikes)}</p>

    <div class="station-actions">
      <a class="btn" href="${directionsUrl}" target="_blank" rel="noopener noreferrer">Navigate with Google Maps</a>
      <button class="ghost-btn" type="button" id="openJourneyPlannerBtn">Open journey planner</button>
    </div>
  `;

  const plannerBtn = document.getElementById("openJourneyPlannerBtn");
  if (plannerBtn) {
    plannerBtn.addEventListener("click", () => {
      window.location.href = "/journey-planner";
    });
  }
}

function renderStationEmpty(message) {
  const stationCard = document.getElementById("station-card");
  if (!stationCard) return;
  stationCard.innerHTML = `
    <h2>Station Details</h2>
    <p>${message}</p>
  `;
}

async function loadHistory(stationId) {
  try {
    const response = await fetch(`/api/db/bikes/hourly_avg/${stationId}?hours=48`);
    const result = await response.json();
    const rows = result.rows || [];
    renderHistoryChart(rows);
  } catch (error) {
    console.error("History load failed:", error);
    renderHistoryEmpty("Failed to load historical data.");
  }
}

function renderHistoryChart(rows) {
  if (!rows.length) {
    renderHistoryEmpty("No historical data available for this station yet.");
    return;
  }

  ensureChartCanvas();
  const canvas = document.getElementById("historyChart");
  if (!canvas) return;

  const labels = rows.map((row) => formatHour(row.hour_bucket));
  const bikesSeries = rows.map((row) => roundTo2(row.avg_bikes));
  const standsSeries = rows.map((row) => roundTo2(row.avg_stands));
  const occupancySeries = rows.map((row) => {
    const bikes = Number(row.avg_bikes || 0);
    const capacity = Number(row.avg_capacity || 0);
    return capacity > 0 ? roundTo2((bikes / capacity) * 100) : 0;
  });

  const seriesConfig = getSeriesConfig(selectedSeries, bikesSeries, standsSeries, occupancySeries);

  if (historyChart) {
    historyChart.destroy();
  }

  historyChart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: seriesConfig.label,
          data: seriesConfig.data,
          borderWidth: 2,
          tension: 0.3,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true }
      },
      scales: {
        y: {
          min: seriesConfig.min,
          max: seriesConfig.max,
          title: {
            display: true,
            text: seriesConfig.axisTitle
          }
        }
      }
    }
  });

  updateChartSummary(rows, seriesConfig, occupancySeries, bikesSeries, standsSeries);
}

function getSeriesConfig(seriesKey, bikesSeries, standsSeries, occupancySeries) {
  if (seriesKey === "bikes") {
    const max = Math.max(...bikesSeries, 1);
    return {
      key: "bikes",
      label: "Average bikes available",
      data: bikesSeries,
      axisTitle: "Bikes",
      min: 0,
      max: Math.ceil(max + 2)
    };
  }

  if (seriesKey === "stands") {
    const max = Math.max(...standsSeries, 1);
    return {
      key: "stands",
      label: "Average docks available",
      data: standsSeries,
      axisTitle: "Docks",
      min: 0,
      max: Math.ceil(max + 2)
    };
  }

  return {
    key: "occupancy",
    label: "Bike occupancy rate (%)",
    data: occupancySeries,
    axisTitle: "Percent",
    min: 0,
    max: 100
  };
}

function updateChartSummary(rows, seriesConfig, occupancySeries, bikesSeries, standsSeries) {
  const summary = document.getElementById("chartSummary");
  if (!summary) return;

  const station = allStations.find((row) => Number(row.station_id) === Number(selectedStationId));
  const peakOccupancy = Math.max(...occupancySeries);
  const avgBikes = roundTo2(bikesSeries.reduce((sum, value) => sum + value, 0) / bikesSeries.length);
  const avgStands = roundTo2(standsSeries.reduce((sum, value) => sum + value, 0) / standsSeries.length);
  const lastBucket = rows[rows.length - 1]?.hour_bucket || "recent hours";

  summary.textContent = `${station?.name || "Selected station"}: showing ${seriesConfig.label.toLowerCase()} over the last 48 hours. Average bikes: ${avgBikes}. Average docks: ${avgStands}. Peak occupancy: ${peakOccupancy}%. Latest bucket: ${lastBucket}.`;
}

function renderHistoryEmpty(message = "No historical data available.") {
  if (historyChart) {
    historyChart.destroy();
    historyChart = null;
  }

  const chartCard = document.getElementById("trend-card");
  if (!chartCard) return;

  chartCard.innerHTML = `
    <h2>48-Hour Bike Trend</h2>
    <div class="chart-toolbar">
      <button class="small-btn active" data-series="occupancy" type="button">Occupancy %</button>
      <button class="small-btn" data-series="bikes" type="button">Avg bikes</button>
      <button class="small-btn" data-series="stands" type="button">Avg docks</button>
    </div>
    <p>${message}</p>
  `;

  bindTrendToggles();
}

function ensureChartCanvas() {
  const chartCard = document.getElementById("trend-card");
  if (!chartCard) return;

  if (!document.getElementById("historyChart")) {
    chartCard.innerHTML = `
      <h2>48-Hour Bike Trend</h2>
      <div class="chart-toolbar">
        <button class="small-btn ${selectedSeries === "occupancy" ? "active" : ""}" data-series="occupancy" type="button">Occupancy %</button>
        <button class="small-btn ${selectedSeries === "bikes" ? "active" : ""}" data-series="bikes" type="button">Avg bikes</button>
        <button class="small-btn ${selectedSeries === "stands" ? "active" : ""}" data-series="stands" type="button">Avg docks</button>
      </div>
      <canvas id="historyChart"></canvas>
      <div class="chart-summary" id="chartSummary">Loading chart insight...</div>
    `;
    bindTrendToggles();
  }
}

async function loadAssistantAdvice(stationId) {
  const adviceBox = document.getElementById("assistantAdvice");
  const metaBox = document.getElementById("assistantMeta");
  if (!adviceBox || !metaBox) return;

  adviceBox.textContent = "Loading assistant advice...";
  metaBox.textContent = "Combining current station status with live weather conditions.";

  try {
    const response = await fetch("/api/assistant/recommend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ station_id: stationId })
    });

    const result = await response.json();

    if (!result.ok) {
      renderAssistantEmpty(result.error || "Assistant advice is unavailable.");
      return;
    }

    const station = result.station || {};
    const weather = result.weather || {};

    adviceBox.textContent = result.advice || "No assistant advice returned.";
    metaBox.textContent = `${safeValue(station.name)} • ${safeValue(weather.weather_description)} • ${safeValue(weather.temp)}°C`;
  } catch (error) {
    console.error("Assistant advice load failed:", error);
    renderAssistantEmpty("Failed to load assistant advice.");
  }
}

function renderAssistantEmpty(message) {
  const adviceBox = document.getElementById("assistantAdvice");
  const metaBox = document.getElementById("assistantMeta");
  if (adviceBox) adviceBox.textContent = message;
  if (metaBox) metaBox.textContent = "The assistant becomes active after a station is selected.";
}

function getMarkerColor(availableBikes, capacity) {
  if (availableBikes == null || capacity == null || Number(capacity) === 0) {
    return "#6c757d";
  }

  if (Number(availableBikes) === 0) {
    return "#dc3545";
  }

  const ratio = Number(availableBikes) / Number(capacity);
  if (ratio < 0.3) {
    return "#fd7e14";
  }

  return "#28a745";
}

function getAvailabilityText(availableBikes, capacity) {
  if (availableBikes == null || capacity == null || Number(capacity) === 0) return "No data";
  if (Number(availableBikes) === 0) return "Empty station";
  const ratio = Number(availableBikes) / Number(capacity);
  if (ratio < 0.3) return "Limited availability";
  return "Good availability";
}

function getWeatherEmoji(main, description) {
  const text = `${main || ""} ${description || ""}`.toLowerCase();
  if (text.includes("rain")) return "🌧️";
  if (text.includes("drizzle")) return "🌦️";
  if (text.includes("cloud")) return "☁️";
  if (text.includes("clear")) return "☀️";
  if (text.includes("thunder")) return "⛈️";
  if (text.includes("snow")) return "❄️";
  if (text.includes("mist") || text.includes("fog")) return "🌫️";
  return "🌤️";
}

function formatHour(value) {
  if (!value) return "N/A";
  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IE", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function roundTo2(value) {
  const num = Number(value || 0);
  return Number(num.toFixed(2));
}

function safeValue(value) {
  return value == null || value === "" ? "N/A" : value;
}