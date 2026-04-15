const USE_MOCK_DATA = false;
const AUTO_REFRESH_MS = 60000;
const MAX_AI_HISTORY_ITEMS = 8;

let map = null;
let infoWindow = null;
let markers = [];
let historyChart = null;
let allStations = [];
let displayedStations = [];
let selectedStationId = null;
let selectedSeries = "occupancy";
let refreshTimer = null;
let aiChatHistory = [];

let userLocationMarker = null;
let userLocationAccuracyCircle = null;
let currentUserLocation = null;

const DEFAULT_CENTER = { lat: 53.3498, lng: -6.2603 };
const DEFAULT_ZOOM = 13;
const GOOGLE_TEST_MAP_ID = "DEMO_MAP_ID";

let resolveMapReady;
const mapReady = new Promise((resolve) => {
  resolveMapReady = resolve;
});

window.initGoogleMap = function () {
  try {
    const mapElement = document.getElementById("map");
    if (!mapElement) {
      resolveMapReady(false);
      return;
    }

    map = new google.maps.Map(mapElement, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      mapId: GOOGLE_TEST_MAP_ID,
      streetViewControl: false,
      mapTypeControl: false,
      fullscreenControl: true
    });

    infoWindow = new google.maps.InfoWindow();

    addLocateControl();

    resolveMapReady(true);
  } catch (error) {
    console.error("Google Map init failed:", error);
    renderMapError("Google Maps failed to initialize.");
    resolveMapReady(false);
  }
};

function addLocateControl() {
  if (!map || !window.google?.maps) return;

  const controlButton = document.createElement("button");
  controlButton.type = "button";
  controlButton.className = "locate-me-btn";
  controlButton.setAttribute("aria-label", "Locate me");
  controlButton.setAttribute("title", "Locate me");
  controlButton.innerHTML = "📍";

  controlButton.addEventListener("click", () => {
    locateUser();
  });

  const controlWrapper = document.createElement("div");
  controlWrapper.className = "locate-me-control";
  controlWrapper.appendChild(controlButton);

  map.controls[google.maps.ControlPosition.INLINE_END_BLOCK_END].push(controlWrapper);
}

function locateUser() {
  if (!map) return;

  if (!navigator.geolocation) {
    showLocationMessage("Your browser does not support geolocation.");
    return;
  }

  showLocationMessage("Locating you...");

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const userPos = {
        lat: position.coords.latitude,
        lng: position.coords.longitude
      };

      currentUserLocation = userPos;
      renderUserLocation(userPos, position.coords.accuracy);

      const bestStation = findNearestAvailableStation(userPos, allStations);

      if (!bestStation) {
        map.panTo(userPos);
        map.setZoom(15);
        showLocationMessage("Your location was found, but no nearby pickup station is available.");
        return;
      }

      const stillVisible = displayedStations.some(
        (station) => Number(station.station_id) === Number(bestStation.station_id)
      );

      if (!stillVisible) {
        displayedStations = [...allStations];
        const searchInput = document.getElementById("stationSearchInput");
        if (searchInput) searchInput.value = "";
        renderMarkers(displayedStations, { fitToBounds: false });
        updateMapSummary(displayedStations);
      }

      await selectStation(bestStation.station_id, true);
      zoomToUserAndStation(userPos, bestStation);

      showLocationMessage(
        `Recommended pickup station: ${safeValue(bestStation.name)} (${formatDistance(bestStation.distance_m)}, about ${formatWalkMinutes(bestStation.distance_m)} walk).`
      );
    },
    (error) => {
      let message = "Unable to get your location.";

      if (error.code === error.PERMISSION_DENIED) {
        message = "Location permission was denied.";
      } else if (error.code === error.POSITION_UNAVAILABLE) {
        message = "Location information is unavailable.";
      } else if (error.code === error.TIMEOUT) {
        message = "Location request timed out.";
      }

      showLocationMessage(message);
      console.error("Geolocation error:", error);
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0
    }
  );
}

function findNearestAvailableStation(userPos, stations) {
  if (!userPos || !Array.isArray(stations) || !stations.length) {
    return null;
  }

  let bestStation = null;
  let minDistance = Number.POSITIVE_INFINITY;

  stations.forEach((station) => {
    const lat = Number(station.latitude);
    const lng = Number(station.longitude);
    const bikes = Number(station.available_bikes || 0);
    const status = String(station.status || "").toUpperCase();

    if (Number.isNaN(lat) || Number.isNaN(lng)) return;
    if (bikes <= 0) return;
    if (status && status !== "OPEN") return;

    const distance = getDistanceMeters(userPos.lat, userPos.lng, lat, lng);

    if (distance < minDistance) {
      minDistance = distance;
      bestStation = {
        ...station,
        distance_m: distance
      };
    }
  });

  return bestStation;
}

function getDistanceMeters(lat1, lng1, lat2, lng2) {
  const toRad = (value) => (value * Math.PI) / 180;
  const earthRadius = 6371000;

  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return earthRadius * c;
}

function formatDistance(distanceMeters) {
  const meters = Number(distanceMeters || 0);

  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }

  return `${(meters / 1000).toFixed(2)} km`;
}

function formatWalkMinutes(distanceMeters) {
  const meters = Number(distanceMeters || 0);
  const minutes = Math.max(1, Math.round(meters / 1.4 / 60));
  return `${minutes} min`;
}

function zoomToUserAndStation(userPos, station) {
  if (!map || !userPos || !station) return;

  const stationLat = Number(station.latitude);
  const stationLng = Number(station.longitude);

  if (Number.isNaN(stationLat) || Number.isNaN(stationLng)) return;

  const bounds = new google.maps.LatLngBounds();
  bounds.extend(userPos);
  bounds.extend({ lat: stationLat, lng: stationLng });

  map.fitBounds(bounds, 80);
}

function renderUserLocation(userPos, accuracy = 0) {
  if (!map || !window.google?.maps) return;

  if (userLocationMarker) {
    userLocationMarker.setMap(null);
  }

  if (userLocationAccuracyCircle) {
    userLocationAccuracyCircle.setMap(null);
  }

  userLocationMarker = new google.maps.Marker({
    position: userPos,
    map,
    title: "Your current location",
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 9,
      fillColor: "#2563eb",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 3
    }
  });

  userLocationAccuracyCircle = new google.maps.Circle({
    strokeColor: "#2563eb",
    strokeOpacity: 0.35,
    strokeWeight: 1,
    fillColor: "#2563eb",
    fillOpacity: 0.12,
    map,
    center: userPos,
    radius: accuracy
  });
}

function showLocationMessage(message) {
  if (!infoWindow || !map) return;

  infoWindow.setContent(`
    <div style="min-width:180px; line-height:1.6;">
      ${escapeHtml(message)}
    </div>
  `);

  infoWindow.setPosition(map.getCenter());
  infoWindow.open(map);
}

window.gm_authFailure = function () {
  renderMapError("Google Maps authentication failed. Check your API key, referrer restrictions, and billing.");
  resolveMapReady(false);
};

window.addEventListener("DOMContentLoaded", async () => {
  bindSearch();
  bindTrendToggles();
  bindAssistantRefresh();
  bindAiAssistant();

  if (window.GOOGLE_MAPS_KEY_MISSING) {
    renderMapError("Google Maps API key is missing. Add GOOGLE_MAPS_API_KEY to your configuration first.");
    return;
  }

  const ready = await waitForMapReady();
  if (!ready) return;

  await Promise.all([
    loadSessionState(),
    loadWeather(),
    loadStations(true)
  ]);

  startAutoRefresh();
});

function waitForMapReady() {
  return Promise.race([
    mapReady,
    new Promise((resolve) => {
      setTimeout(() => {
        if (!map) {
          renderMapError("Google Maps did not load in time. Check your internet connection and API key settings.");
          resolve(false);
        }
      }, 8000);
    })
  ]);
}

function renderMapError(message) {
  const mapElement = document.getElementById("map");
  if (!mapElement) return;
  mapElement.innerHTML = `<div class="map-error">${escapeHtml(message)}</div>`;
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

    renderMarkers(displayedStations, { fitToBounds: true });
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
      await selectStation(displayedStations[0].station_id, false);
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

function bindAiAssistant() {
  const form = document.getElementById("aiChatForm");
  const input = document.getElementById("aiChatInput");

  if (!form || !input) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = input.value.trim();
    if (!message) return;

    input.value = "";
    await sendAiChatMessage(message);
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
    <p><strong>Description:</strong> ${escapeHtml(safeValue(weather.weather_description))}</p>
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
    <p><strong>Condition:</strong> ${escapeHtml(safeValue(weather.weather_main))}</p>
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

function renderPredictionEmpty(message) {
  const card = document.getElementById("prediction-card");
  if (!card) return;

  card.innerHTML = `
    <h2 class="sidebar-card-title">Bike & Weather Outlook</h2>
    <p class="text-muted text-sm">${escapeHtml(message)}</p>
  `;
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

    const shouldFitMap = initialLoad || selectedStationId == null;
    renderMarkers(displayedStations, { fitToBounds: shouldFitMap });
    updateMapSummary(displayedStations);
    updateRefreshStamp();

    if (!displayedStations.length) {
      renderStationEmpty("No station data available yet.");
      renderHistoryEmpty("No historical data available.");
      renderAssistantEmpty("No station selected for assistant advice.");
      renderPredictionEmpty("No prediction data available.");
      return;
    }

    const selectedStillExists = displayedStations.some(
      (station) => Number(station.station_id) === Number(selectedStationId)
    );

    if (initialLoad || !selectedStillExists) {
      await selectStation(displayedStations[0].station_id, false);
      return;
    }

    const currentStation = displayedStations.find(
      (station) => Number(station.station_id) === Number(selectedStationId)
    );

    if (currentStation) {
      renderStationCard(currentStation);
      await Promise.all([
        loadHistory(selectedStationId),
        loadAssistantAdvice(selectedStationId),
        loadPredictions(selectedStationId)
      ]);
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

function renderMarkers(rows, options = {}) {
  const { fitToBounds = true } = options;

  if (!map || !window.google?.maps?.marker?.AdvancedMarkerElement) return;

  clearMarkers();

  if (!rows.length) {
    resetMapView();
    return;
  }

  const bounds = new google.maps.LatLngBounds();

  rows.forEach((row) => {
    const lat = Number(row.latitude);
    const lng = Number(row.longitude);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    const isSelected = Number(row.station_id) === Number(selectedStationId);
    const color = getMarkerColor(row.available_bikes, row.capacity);
    const content = createMarkerBubble(color, isSelected);

    const marker = new google.maps.marker.AdvancedMarkerElement({
      map,
      position: { lat, lng },
      title: row.name || "",
      content,
      gmpClickable: true
    });

    marker.addListener("gmp-click", async () => {
      await selectStation(row.station_id, true);
    });

    markers.push({
      stationId: Number(row.station_id),
      marker,
      row
    });

    bounds.extend({ lat, lng });
  });

  if (fitToBounds) {
    map.fitBounds(bounds);

    if (rows.length === 1) {
      map.setZoom(15);
    }
  }
}

function createMarkerBubble(color, isSelected) {
  const bubble = document.createElement("div");
  bubble.style.width = isSelected ? "22px" : "18px";
  bubble.style.height = isSelected ? "22px" : "18px";
  bubble.style.borderRadius = "999px";
  bubble.style.background = color;
  bubble.style.border = "2px solid #ffffff";
  bubble.style.boxShadow = isSelected
    ? "0 0 0 2px rgba(37,99,235,0.35), 0 8px 18px rgba(15,23,42,0.22)"
    : "0 6px 16px rgba(15,23,42,0.20)";
  bubble.style.transform = isSelected ? "scale(1.08)" : "scale(1)";
  bubble.style.transition = "all 0.2s ease";
  return bubble;
}

async function selectStation(stationId, openInfoWindowAfterRender = false) {
  selectedStationId = Number(stationId);

  const station = allStations.find((row) => Number(row.station_id) === Number(selectedStationId));
  if (!station) return;

  renderMarkers(displayedStations.length ? displayedStations : allStations, { fitToBounds: false });
  renderStationCard(station);
  
  await Promise.all([
    loadHistory(selectedStationId),
    loadAssistantAdvice(selectedStationId),
    loadPredictions(selectedStationId)
  ]);

  if (openInfoWindowAfterRender) {
    openSelectedInfoWindow();
  }
}

function openSelectedInfoWindow() {
  const selectedEntry = markers.find((entry) => Number(entry.stationId) === Number(selectedStationId));
  if (!selectedEntry || !infoWindow) return;

  const row = selectedEntry.row;

  infoWindow.setContent(`
    <div style="min-width: 180px; line-height: 1.6;">
      <strong>${escapeHtml(safeValue(row.name))}</strong><br>
      ${escapeHtml(safeValue(row.address))}<br><br>
      Bikes: ${safeValue(row.available_bikes)}<br>
      Docks: ${safeValue(row.available_bike_stands)}<br>
      Status: ${escapeHtml(safeValue(row.status))}
    </div>
  `);

  infoWindow.open({
    map,
    anchor: selectedEntry.marker
  });
}

function clearMarkers() {
  markers.forEach((entry) => {
    entry.marker.map = null;
  });
  markers = [];
}

function resetMapView() {
  if (!map) return;
  map.setCenter(DEFAULT_CENTER);
  map.setZoom(DEFAULT_ZOOM);
}

function renderStationCard(row) {
  const stationCard = document.getElementById("station-card");
  if (!stationCard) return;

  const capacity = Number(row.capacity || 0);
  const bikes = Number(row.available_bikes || 0);
  const occupancy = capacity > 0 ? Math.round((bikes / capacity) * 100) : 0;
  const statusText = getAvailabilityText(row.available_bikes, row.capacity);

  const distanceMeters =
  currentUserLocation && row.latitude != null && row.longitude != null
    ? getDistanceMeters(
        currentUserLocation.lat,
        currentUserLocation.lng,
        Number(row.latitude),
        Number(row.longitude)
      )
    : null;

  const distanceHtml =
  distanceMeters != null
    ? `<p><strong>Distance from you:</strong> ${formatDistance(distanceMeters)}</p>`
    : "";

  const walkTimeHtml =
  distanceMeters != null
    ? `<p><strong>Estimated walk time:</strong> ${formatWalkMinutes(distanceMeters)}</p>`
    : "";

  const walkDirectionsUrl =
  currentUserLocation && row.latitude != null && row.longitude != null
    ? `https://www.google.com/maps/dir/?api=1&origin=${currentUserLocation.lat},${currentUserLocation.lng}&destination=${row.latitude},${row.longitude}&travelmode=walking`
    : "#";

  const cycleDirectionsUrl =
  row.latitude != null && row.longitude != null
    ? `https://www.google.com/maps/dir/?api=1&destination=${row.latitude},${row.longitude}&travelmode=bicycling`
    : "#";
    
  stationCard.innerHTML = `
    <h2>${escapeHtml(safeValue(row.name))}</h2>
    <p>${escapeHtml(safeValue(row.address))}</p>

    <div class="station-status">${escapeHtml(statusText)}</div>
    
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

    ${distanceHtml}
    ${walkTimeHtml}

    <p><strong>Total Capacity:</strong> ${safeValue(row.capacity)}</p>
    <p><strong>Occupancy:</strong> ${occupancy}%</p>
    <p><strong>Status:</strong> ${escapeHtml(safeValue(row.status))}</p>
    <p><strong>Last Update:</strong> ${escapeHtml(safeValue(row.last_update))}</p>
    <p><strong>Mechanical Bikes:</strong> ${safeValue(row.mechanical_bikes)}</p>
    <p><strong>Electrical Bikes:</strong> ${safeValue(row.electrical_bikes)}</p>

    <div class="station-actions">
      ${
        distanceMeters != null
          ? `<a class="btn" href="${walkDirectionsUrl}" target="_blank" rel="noopener noreferrer">Walk to this station</a>`
          : ""
      }
      <a class="btn" href="${cycleDirectionsUrl}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>
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
    <p>${escapeHtml(message)}</p>
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

async function loadPredictions(stationId, hours = 24) {
  try {
    // 將網址改為後端存在的路徑
    const url = `/api/db/bikes/hourly_avg/${stationId}?hours=${hours}`;
    const response = await fetch(url);
    
    // 檢查回傳是否成功
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.ok) {
      renderPredictionEmpty(result.error || "Prediction data unavailable.");
      return;
    }

    renderPredictionCard(result);
  } catch (error) {
    console.error("Prediction load failed:", error);
    renderPredictionEmpty("Failed to load prediction data.");
  }
}

function renderPredictionCard(result) {
  const card = document.getElementById("prediction-card");
  if (!card) return;

  const predictions = result.predictions || [];
  if (!predictions.length) {
    renderPredictionEmpty("No prediction data available.");
    return;
  }

  const shortList = predictions.slice(0, 4);
  const longList = predictions.slice(0, 24);

  const shortHtml = shortList.map((item) => {
    const rainText = item.rain_prob != null
      ? `${Math.round(Number(item.rain_prob) * 100)}% rain`
      : "Rain N/A";

    const tag = getPredictionTag(item.predicted_bikes, item.predicted_docks, item.capacity);

    return `
      <div class="prediction-item">
        <div class="prediction-hour">In ${item.hour_offset} hour${item.hour_offset > 1 ? "s" : ""}</div>
        <div class="prediction-main">${escapeHtml(safeValue(item.weather_description))}</div>
        <div class="prediction-sub">
          Temp: ${safeValue(item.temp)}°C<br>
          ${rainText}<br>
          Bikes: ${safeValue(item.predicted_bikes)}<br>
          Docks: ${safeValue(item.predicted_docks)}
        </div>
        <div class="prediction-tag">${escapeHtml(tag)}</div>
      </div>
    `;
  }).join("");

  const longHtml = longList.map((item) => `
    <div class="prediction-24h-row">
      <span>+${item.hour_offset}h</span>
      <span>${escapeHtml(safeValue(item.weather_main))}</span>
      <span>${safeValue(item.temp)}°C</span>
      <span>${safeValue(item.predicted_bikes)} bikes</span>
      <span>${safeValue(item.predicted_docks)} docks</span>
    </div>
  `).join("");

  card.innerHTML = `
    <h2 class="sidebar-card-title">Bike & Weather Outlook</h2>
    <p class="text-muted text-sm">
      Estimated availability for ${escapeHtml(safeValue(result.station_name))} over the next few hours.
    </p>

    <div class="prediction-grid">
      ${shortHtml}
    </div>

    <div class="prediction-actions">
      <button class="btn-sm-outline" type="button" id="toggle24hPredictionsBtn">View 24h outlook</button>
    </div>

    <div class="prediction-24h hidden" id="prediction24hWrap">
      ${longHtml}
    </div>
  `;

  const toggleBtn = document.getElementById("toggle24hPredictionsBtn");
  const wrap = document.getElementById("prediction24hWrap");

  if (toggleBtn && wrap) {
    toggleBtn.addEventListener("click", () => {
      wrap.classList.toggle("hidden");
      toggleBtn.textContent = wrap.classList.contains("hidden")
        ? "View 24h outlook"
        : "Hide 24h outlook";
    });
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
    <p>${escapeHtml(message)}</p>
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

/* =========================
   AI BIKE ASSISTANT
========================= */

async function sendAiChatMessage(message) {
  appendAiChatMessage("user", message);

  aiChatHistory.push({ role: "user", content: message });
  aiChatHistory = aiChatHistory.slice(-MAX_AI_HISTORY_ITEMS);

  setAiControlsDisabled(true);
  setAiStatus("Thinking...");

  try {
    const response = await fetch("/api/ai/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message,
        station_id: selectedStationId,
        history: aiChatHistory
      })
    });

    const result = await response.json();

    if (!response.ok || !result.ok) {
      appendAiChatMessage("bot", result.error || "The AI assistant is unavailable right now.");
      renderAiWeatherContext(null);
      setAiStatus("AI request failed.");
      return;
    }

    const replyText = result.reply || "No reply returned.";

    appendAiChatMessage("bot", replyText);
    aiChatHistory.push({ role: "assistant", content: replyText });
    aiChatHistory = aiChatHistory.slice(-MAX_AI_HISTORY_ITEMS);

    renderAiWeatherContext(result.weather || null);

    let highlightDone = false;
    if (result.selected_station != null) {
      highlightDone = await tryHighlightAiSelectedStation(result.selected_station);
    }

    if (highlightDone) {
      setAiStatus("Suggested station highlighted on the map.");
    } else {
      setAiStatus("AI reply ready.");
    }
  } catch (error) {
    console.error("AI chat failed:", error);
    appendAiChatMessage("bot", "Sorry, the AI assistant is temporarily unavailable.");
    renderAiWeatherContext(null);
    setAiStatus("AI assistant unavailable.");
  } finally {
    setAiControlsDisabled(false);
    const input = document.getElementById("aiChatInput");
    if (input) input.focus();
  }
}

function appendAiChatMessage(role, text) {
  const box = document.getElementById("aiChatMessages");
  if (!box) return;

  const messageEl = document.createElement("div");
  messageEl.className = role === "user"
    ? "ai-message ai-message-user"
    : "ai-message ai-message-bot";

  messageEl.textContent = text || "";
  box.appendChild(messageEl);
  box.scrollTop = box.scrollHeight;
}

function setAiControlsDisabled(isDisabled) {
  const input = document.getElementById("aiChatInput");
  const button = document.getElementById("aiChatSendBtn");

  if (input) input.disabled = isDisabled;
  if (button) button.disabled = isDisabled;
}

function setAiStatus(message) {
  const statusEl = document.getElementById("aiChatStatus");
  if (!statusEl) return;
  statusEl.textContent = message || "";
}

function renderAiWeatherContext(weather) {
  const box = document.getElementById("aiWeatherContext");
  if (!box) return;

  if (!weather) {
    box.hidden = true;
    box.innerHTML = "";
    return;
  }

  box.hidden = false;
  box.innerHTML = `
    <div class="ai-weather-title">Weather context used by AI</div>
    <div class="ai-weather-grid">
      <div class="ai-weather-item">
        <span class="label">Temp</span>
        <span class="value">${escapeHtml(safeValue(weather.temp))}°C</span>
      </div>
      <div class="ai-weather-item">
        <span class="label">Feels like</span>
        <span class="value">${escapeHtml(safeValue(weather.feels_like))}°C</span>
      </div>
      <div class="ai-weather-item">
        <span class="label">Condition</span>
        <span class="value">${escapeHtml(safeValue(weather.weather_main))}</span>
      </div>
      <div class="ai-weather-item">
        <span class="label">Humidity</span>
        <span class="value">${escapeHtml(safeValue(weather.humidity))}%</span>
      </div>
      <div class="ai-weather-item">
        <span class="label">Wind</span>
        <span class="value">${escapeHtml(safeValue(weather.wind_speed))} m/s</span>
      </div>
      <div class="ai-weather-item">
        <span class="label">Description</span>
        <span class="value">${escapeHtml(safeValue(weather.weather_description))}</span>
      </div>
    </div>
  `;
}

async function tryHighlightAiSelectedStation(selectedStation) {
  const station = resolveStationFromAi(selectedStation);
  if (!station) return false;

  const visibleNow = displayedStations.some(
    (row) => Number(row.station_id) === Number(station.station_id)
  );

  if (!visibleNow) {
    displayedStations = [...allStations];
    const searchInput = document.getElementById("stationSearchInput");
    if (searchInput) searchInput.value = "";
    renderMarkers(displayedStations, { fitToBounds: false });
    updateMapSummary(displayedStations);
  }

  await selectStation(station.station_id, true);

  if (map && station.latitude != null && station.longitude != null) {
    map.panTo({
      lat: Number(station.latitude),
      lng: Number(station.longitude)
    });
    map.setZoom(16);
  }

  return true;
}

function resolveStationFromAi(selectedStation) {
  if (!allStations.length || selectedStation == null) return null;

  const possibleValues = [];

  if (typeof selectedStation === "object") {
    possibleValues.push(
      selectedStation.station_id,
      selectedStation.number,
      selectedStation.name
    );
  } else {
    possibleValues.push(selectedStation);
  }

  for (const value of possibleValues) {
    if (value == null || value === "") continue;

    const asNumber = Number(value);
    if (!Number.isNaN(asNumber)) {
      const byId = allStations.find((row) =>
        Number(row.station_id) === asNumber || Number(row.number) === asNumber
      );
      if (byId) return byId;
    }

    const normalized = String(value).trim().toLowerCase();

    const byExactName = allStations.find((row) =>
      String(row.name || "").trim().toLowerCase() === normalized
    );
    if (byExactName) return byExactName;

    const byPartialName = allStations.find((row) =>
      String(row.name || "").trim().toLowerCase().includes(normalized)
    );
    if (byPartialName) return byPartialName;
  }

  return null;
}

/* =========================
   HELPERS
========================= */

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

function getPredictionTag(bikes, docks, capacity) {
  const bikeNum = Number(bikes || 0);
  const dockNum = Number(docks || 0);
  const capNum = Number(capacity || 0);

  if (capNum <= 0) return "No prediction";
  if (bikeNum <= 3) return "Low bike availability";
  if (dockNum <= 2) return "Better for pickup";
  if (bikeNum / capNum >= 0.5) return "Good to pick up";
  return "Balanced availability";
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}