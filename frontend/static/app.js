const stopsEl = document.querySelector("#stops");
const vehiclesEl = document.querySelector("#vehicles");
const form = document.querySelector("#plan-form");

const vehicleTypeDefaults = {
  bike: { capacityKg: 40 },
  ev: { capacityKg: 300 },
  van: { capacityKg: 350 },
  truck: { capacityKg: 1500 },
};

function stopRow(stop = {}) {
  const row = document.createElement("div");
  row.className = "item-row stop-row";
  row.innerHTML = `
    <label>Name<input class="stop-name" value="${stop.name || ""}" required></label>
    <label>Address<input class="stop-address" value="${stop.address || ""}" required></label>
    <label>Demand kg<input class="stop-demand" type="number" min="0" value="${stop.demand || 0}" required></label>
    <button class="remove" type="button" aria-label="Remove stop">Remove</button>`;
  row.querySelector(".remove").onclick = () => row.remove();
  stopsEl.appendChild(row);
}

function vehicleRow(vehicle = {}) {
  const row = document.createElement("div");
  const initialType = vehicle.type || "van";
  const initialCapacity = vehicle.capacity ?? vehicleTypeDefaults[initialType].capacityKg;
  row.className = "item-row vehicle-row";
  row.innerHTML = `
    <label>ID<input class="vehicle-id" value="${vehicle.id || ""}" required></label>
    <label>Type<select class="vehicle-type"><option>van</option><option>truck</option><option>bike</option><option>ev</option></select></label>
    <label>Capacity kg<input class="vehicle-capacity" type="number" min="1" value="${initialCapacity}" required></label>
    <button class="remove" type="button" aria-label="Remove vehicle">Remove</button>`;
  const typeSelect = row.querySelector(".vehicle-type");
  const capacityInput = row.querySelector(".vehicle-capacity");
  typeSelect.value = initialType;
  capacityInput.max = vehicleTypeDefaults[initialType].capacityKg;
  typeSelect.addEventListener("change", () => {
    const maximumCapacity = vehicleTypeDefaults[typeSelect.value].capacityKg;
    capacityInput.max = maximumCapacity;
    capacityInput.value = maximumCapacity;
  });
  row.querySelector(".remove").onclick = () => row.remove();
  vehiclesEl.appendChild(row);
}

[
  { name: "Kreuzberg Store", address: "Oranienstraße, Berlin", demand: 180 },
  { name: "Mitte Office", address: "Friedrichstraße, Berlin", demand: 120 },
  { name: "Charlottenburg Shop", address: "Kurfürstendamm, Berlin", demand: 210 },
  { name: "Neukölln Market", address: "Karl-Marx-Straße, Berlin", demand: 95 },
  { name: "Prenzlauer Berg Café", address: "Kollwitzstraße, Berlin", demand: 70 },
  { name: "Friedrichshain Studio", address: "Warschauer Straße, Berlin", demand: 130 },
].forEach(stopRow);
[
  { id: "VAN-01", type: "van", capacity: 350 },
  { id: "EV-02", type: "ev", capacity: 300 },
  { id: "TRUCK-03", type: "truck", capacity: 1500 },
].forEach(vehicleRow);

document.querySelector("#add-stop").onclick = () => stopRow();
document.querySelector("#add-vehicle").onclick = () => vehicleRow();

fetch("/api/health").then(r => r.json()).then(data => {
  document.querySelector("#provider").textContent =
    `${data.llm_provider.toUpperCase()} LLM · ${data.routing_provider.toUpperCase()} roads · ${data.llm_enabled ? "enabled" : "fallback"}`;
}).catch(() => document.querySelector("#provider").textContent = "API unavailable");

function payload() {
  return {
    objective: document.querySelector("#objective").value,
    depot: {
      name: document.querySelector("#depot-name").value,
      address: document.querySelector("#depot-address").value,
    },
    stops: [...document.querySelectorAll(".stop-row")].map(row => ({
      name: row.querySelector(".stop-name").value,
      address: row.querySelector(".stop-address").value,
      demand_kg: Number(row.querySelector(".stop-demand").value),
    })),
    vehicles: [...document.querySelectorAll(".vehicle-row")].map(row => ({
      id: row.querySelector(".vehicle-id").value,
      type: row.querySelector(".vehicle-type").value,
      capacity_kg: Number(row.querySelector(".vehicle-capacity").value),
    })),
  };
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
}

function safeSourceUrl(value = "") {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

function render(data) {
  document.querySelector("#empty").classList.add("hidden");
  document.querySelector("#results").classList.remove("hidden");
  document.querySelector("#summary").textContent = data.summary;
  const distance = data.routes.reduce((sum, route) => sum + route.total_distance_km, 0);
  const cost = data.routes.reduce((sum, route) => sum + route.estimated_cost, 0);
  document.querySelector("#metrics").innerHTML = `
    <div class="metric"><strong>${data.routes.length}</strong><span>ACTIVE ROUTES</span></div>
    <div class="metric"><strong>${distance.toFixed(1)} km</strong><span>TOTAL DISTANCE</span></div>
    <div class="metric"><strong>${cost.toFixed(2)}</strong><span>ESTIMATED COST</span></div>`;
  document.querySelector("#weather").innerHTML = data.weather ? `
    <article class="weather-card ${data.weather.severe ? "severe" : ""}">
      <div>
        <small>CURRENT BERLIN WEATHER · ${escapeHtml(data.weather.source)}</small>
        <strong>${escapeHtml(data.weather.condition)} · ${data.weather.temperature_c.toFixed(1)}°C</strong>
      </div>
      <div class="weather-details">
        <span>Feels ${data.weather.apparent_temperature_c.toFixed(1)}°C</span>
        <span>Wind ${data.weather.wind_speed_kmh.toFixed(0)} km/h</span>
        <span>Gusts ${data.weather.wind_gust_kmh.toFixed(0)} km/h</span>
        <span>Rain ${data.weather.precipitation_mm.toFixed(1)} mm</span>
      </div>
    </article>` : "";
  document.querySelector("#timeline").innerHTML = data.events.map(event => `
    <div class="event"><strong>${event.agent}</strong> &middot; ${event.action.replaceAll("_", " ")}
      <small>${event.summary}</small></div>`).join("");
  const colors = ["#176b4d", "#ed7d4b", "#5973cc", "#a45ab5", "#b58a24"];
  document.querySelector("#routes").innerHTML = data.routes.map((route, index) => `
    <article class="route" data-route-index="${index}" tabindex="0" role="button" aria-label="Animate ${route.vehicle_id}">
      <div class="route-head"><strong><i class="route-swatch" style="background:${colors[index % colors.length]}"></i>${route.vehicle_id}<small class="traffic-tag">${route.traffic_level}</small></strong><span>${route.total_load_kg} kg &middot; ${route.total_distance_km} km</span></div>
      <div class="route-path">Hub &rarr; ${route.stops.map(stop => stop.name).join(" &rarr; ")} &rarr; Hub</div>
    </article>`).join("");
  const disruptions = data.disruptions || [];
  document.querySelector("#disruptions").innerHTML = disruptions.length ? `
    <h3 class="section-label">Live Berlin disruption intelligence</h3>
    ${disruptions.map(signal => `
      <article class="disruption">
        <div class="disruption-head">
          <strong>${escapeHtml(signal.title)}</strong>
          <span class="confidence">${Math.round(signal.confidence * 100)}% confidence</span>
        </div>
        <p>${escapeHtml(signal.summary)}</p>
        <small>${escapeHtml(signal.status)} · ${escapeHtml(signal.disruption_type)}
          ${signal.affected_vehicle_ids.length ? ` · Vehicles: ${escapeHtml(signal.affected_vehicle_ids.join(", "))}` : ""}
        </small>
        <a href="${safeSourceUrl(signal.source_url)}" target="_blank" rel="noopener noreferrer">Verify source ↗</a>
      </article>`).join("")}` : "";
  document.querySelector("#issues").innerHTML = data.issues.map(issue =>
    `<div class="issue"><strong>${issue.code}</strong> &mdash; ${issue.message}</div>`).join("") +
    (data.approval_required ? `<div class="approval"><span><strong>Dispatcher approval required</strong><br><small>${
      data.issues.some(issue => ["LIVE_ROAD_DISRUPTION", "SEVERE_WEATHER"].includes(issue.code))
        ? "Verify live disruption and weather safety before dispatch."
        : "Replanning changed the route sequence or assignment."
    }</small></span><button id="approve-plan">Approve plan</button></div>` : "");
  if (data.approval_required) {
    document.querySelector("#approve-plan").onclick = async () => {
      const response = await fetch(`/api/plans/${data.run_id}/approve`, {method: "POST"});
      if (!response.ok) return;
      const approved = await response.json();
      document.querySelector(".approval").innerHTML = "<strong>Plan approved by dispatcher</strong>";
      document.querySelector("#run-status").textContent = approved.status.toUpperCase();
      document.querySelector("#run-status").className = "badge done";
    };
  }
  renderRouteMap(data.routes, colors);
  renderFreeMap(data.routes, colors);
}

let logisticsMap;
let mapVehicleMarker;
let vehicleAnimationFrame;

function renderFreeMap(routes, colors) {
  if (!window.maplibregl || !routes.length) return;
  if (logisticsMap) logisticsMap.remove();
  cancelAnimationFrame(vehicleAnimationFrame);
  document.querySelector("#route-canvas").classList.remove("map-ready");
  logisticsMap = new maplibregl.Map({
    container: "free-map",
    style: "https://tiles.openfreemap.org/styles/liberty",
    center: [13.405, 52.52],
    zoom: 10,
    attributionControl: true,
  });
  logisticsMap.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-left");
  logisticsMap.on("load", () => {
    const bounds = new maplibregl.LngLatBounds();
    routes.forEach((route, index) => {
      const coordinates = route.route_coordinates.map(point => [point.longitude, point.latitude]);
      coordinates.forEach(point => bounds.extend(point));
      logisticsMap.addSource(`vehicle-${index}`, {
        type: "geojson",
        data: {type: "Feature", properties: {}, geometry: {type: "LineString", coordinates}},
      });
      logisticsMap.addLayer({
        id: `vehicle-${index}`,
        type: "line",
        source: `vehicle-${index}`,
        paint: {
          "line-color": colors[index % colors.length],
          "line-width": 5,
          "line-opacity": .58,
        },
      });
    });
    logisticsMap.fitBounds(bounds, {padding: 35, duration: 0});
    document.querySelector("#route-canvas").classList.add("map-ready");
    activateMapRoute(0, routes, colors);
  });
  document.querySelectorAll(".route").forEach((card, index) =>
    card.addEventListener("click", () => activateMapRoute(index, routes, colors)));
}

function activateMapRoute(index, routes, colors) {
  if (!logisticsMap?.loaded()) return;
  routes.forEach((_, routeIndex) => {
    logisticsMap.setPaintProperty(
      `vehicle-${routeIndex}`,
      "line-color",
      routeIndex === index ? "#79bd2d" : colors[routeIndex % colors.length],
    );
    logisticsMap.setPaintProperty(
      `vehicle-${routeIndex}`,
      "line-width",
      routeIndex === index ? 9 : 4,
    );
  });
  cancelAnimationFrame(vehicleAnimationFrame);
  mapVehicleMarker?.remove();
  const points = routes[index].route_coordinates.map(point => [point.longitude, point.latitude]);
  const markerElement = document.createElement("div");
  markerElement.className = "map-truck";
  markerElement.textContent = "🚚";
  mapVehicleMarker = new maplibregl.Marker({element: markerElement}).setLngLat(points[0]).addTo(logisticsMap);
  let started;
  const animate = timestamp => {
    started ??= timestamp;
    const progress = ((timestamp - started) % 9000) / 9000;
    const scaled = progress * (points.length - 1);
    const segment = Math.min(Math.floor(scaled), points.length - 2);
    const fraction = scaled - segment;
    const start = points[segment], end = points[segment + 1];
    mapVehicleMarker.setLngLat([
      start[0] + (end[0] - start[0]) * fraction,
      start[1] + (end[1] - start[1]) * fraction,
    ]);
    vehicleAnimationFrame = requestAnimationFrame(animate);
  };
  vehicleAnimationFrame = requestAnimationFrame(animate);
}

function renderRouteMap(routes, colors) {
  const svg = document.querySelector("#route-map");
  const coordinates = routes.flatMap(route => route.route_coordinates || []);
  if (!coordinates.length) {
    svg.innerHTML = "";
    return;
  }
  const lats = coordinates.map(point => point.latitude);
  const lngs = coordinates.map(point => point.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const project = point => {
    const x = 42 + ((point.longitude - minLng) / (maxLng - minLng || 1)) * 500;
    const y = 190 - ((point.latitude - minLat) / (maxLat - minLat || 1)) * 155;
    return [x.toFixed(1), y.toFixed(1)];
  };
  const routePaths = routes.map((route, index) => {
    const points = route.route_coordinates.map(project);
    const path = points.map((point, pointIndex) =>
      `${pointIndex ? "L" : "M"} ${point[0]} ${point[1]}`).join(" ");
    return { path, points, color: colors[index % colors.length] };
  });
  const allNodes = routePaths.flatMap(item => item.points.slice(1, -1));
  const hub = routePaths[0].points[0];
  svg.innerHTML = `
    ${routePaths.map((item, index) => `<path id="route-line-${index}" class="map-route" d="${item.path}" stroke="${item.color}"></path>`).join("")}
    ${allNodes.map((point, index) => `<circle class="map-node" cx="${point[0]}" cy="${point[1]}" r="6" stroke="${colors[index % colors.length]}"></circle>`).join("")}
    <circle class="map-hub" cx="${hub[0]}" cy="${hub[1]}" r="12"></circle>
    <text x="${Number(hub[0]) + 17}" y="${Number(hub[1]) + 4}" font-size="10" font-weight="800" fill="#1d5b46">HUB</text>
    <g id="animated-vehicle"></g>`;

  const cards = [...document.querySelectorAll(".route")];
  const selectRoute = index => {
    document.querySelectorAll(".map-route").forEach((path, pathIndex) =>
      path.classList.toggle("selected", pathIndex === index));
    cards.forEach((card, cardIndex) =>
      card.classList.toggle("selected", cardIndex === index));
    const marker = document.querySelector("#animated-vehicle");
    marker.innerHTML = `<text class="vehicle-marker" x="-10" y="7">&#128666;
      <animateMotion dur="${Math.max(5, routePaths[index].points.length * 1.5)}s" repeatCount="indefinite" path="${routePaths[index].path}"></animateMotion>
    </text>`;
  };
  cards.forEach((card, index) => {
    card.onclick = () => selectRoute(index);
    card.onkeydown = event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectRoute(index);
      }
    };
  });
  if (routes.length) selectRoute(0);
}

form.onsubmit = async event => {
  event.preventDefault();
  const button = form.querySelector(".primary");
  const status = document.querySelector("#run-status");
  button.disabled = true;
  status.textContent = "RUNNING";
  status.className = "badge running";
  try {
    const response = await fetch("/api/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail?.[0]?.msg || data.detail || "Planning failed");
    render(data);
    status.textContent = data.status.toUpperCase();
    status.className = `badge ${data.status === "completed" ? "done" : "partial"}`;
  } catch (error) {
    document.querySelector("#empty").classList.remove("hidden");
    document.querySelector("#empty").innerHTML = `<h3>Could not run workflow</h3><p>${error.message}</p>`;
    status.textContent = "ERROR";
    status.className = "badge partial";
  } finally {
    button.disabled = false;
  }
};
