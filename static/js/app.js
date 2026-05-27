console.log("Subaharan Detector 3000 website loaded.");

const profileBtn = document.getElementById("profileBtn");
const profileDropdown = document.getElementById("profileDropdown");

if (profileBtn && profileDropdown) {
  profileBtn.addEventListener("click", function (event) {
    event.stopPropagation();
    profileDropdown.classList.toggle("open");
  });

  document.addEventListener("click", function () {
    profileDropdown.classList.remove("open");
  });

  profileDropdown.addEventListener("click", function (event) {
    event.stopPropagation();
  });
}

async function refreshStatus() {
  try {
    const response = await fetch("/status");

    if (!response.ok) {
      console.error("Status request failed");
      return;
    }

    const data = await response.json();

    const serverStatus = document.getElementById("serverStatus");
    const cameraStatus = document.getElementById("cameraStatus");
    const piIp = document.getElementById("piIp");
    const temperature = document.getElementById("temperature");
    const fps = document.getElementById("fps");
    const lastDetection = document.getElementById("lastDetection");
    const connectedApps = document.getElementById("connectedApps");
    const detectionsToday = document.getElementById("detectionsToday");

    if (serverStatus) serverStatus.textContent = data.server ?? "Unknown";
    if (piIp) piIp.textContent = data.ip_address ?? "Unknown";
    if (temperature)
      temperature.textContent = data.temperature ?? "Unavailable";

    if (data.camera) {
      if (cameraStatus)
        cameraStatus.textContent = data.camera.status ?? "Unknown";
      if (fps) fps.textContent = data.camera.fps ?? "0";
      if (lastDetection)
        lastDetection.textContent = data.camera.latest_detection ?? "None";
      if (connectedApps)
        connectedApps.textContent = data.camera.connected_clients ?? "0";
      if (detectionsToday) {
        detectionsToday.textContent = data.camera.detections_today ?? "0";
      }
    }
  } catch (error) {
    console.error("Could not refresh status:", error);
  }
}

if (document.querySelector(".detection-layout")) {
  refreshStatus();
  setInterval(refreshStatus, 3000);
}
