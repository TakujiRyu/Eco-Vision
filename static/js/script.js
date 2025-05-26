const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

const totalBottlesDisplay = document.getElementById('total-bottles');
const pointsDisplay = document.getElementById('points');
const bottleTypeDisplay = document.getElementById('bottle-type');

let scanning = false;
let scanInterval = null;
let totalBottles = 0;
let totalPoints = 0;
let detections = [];

// Load saved user data on page load
window.addEventListener('DOMContentLoaded', () => {
  fetch('/user_scan_stats')
    .then(res => {
      if (!res.ok) throw new Error('Unauthorized or error fetching stats');
      return res.json();
    })
    .then(data => {
      totalBottles = data.total_bottles || 0;
      totalPoints = data.total_points || 0;
      bottleTypeDisplay.textContent = data.last_bottle_type || '—';

      totalBottlesDisplay.textContent = totalBottles;
      pointsDisplay.textContent = totalPoints;
    })
    .catch(err => {
      console.warn('Could not load saved scan stats:', err);
    });
});

navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
        video.play();
        requestAnimationFrame(draw);
    })
    .catch(err => console.error("Webcam access failed:", err));

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    detections.forEach(det => {
        ctx.strokeStyle = `rgb(${det.color[0]},${det.color[1]},${det.color[2]})`;
        ctx.lineWidth = 3;
        ctx.strokeRect(det.x1, det.y1, det.x2 - det.x1, det.y2 - det.y1);

        ctx.fillStyle = ctx.strokeStyle;
        ctx.font = '18px Arial';
        ctx.fillText(det.label, det.x1, det.y1 > 20 ? det.y1 - 10 : det.y1 + 20);
    });

    requestAnimationFrame(draw);
}

function captureAndSend() {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
    const imageData = tempCanvas.toDataURL('image/jpeg');

    fetch('/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            console.error("Detection error:", data.error);
            return;
        }

        detections = data.detections || [];

        if (detections.length > 0) {
            totalBottles += 1;
            totalPoints += data.points || 0;

            pointsDisplay.textContent = totalPoints;
            totalBottlesDisplay.textContent = totalBottles;

            if (data.points === 2) {
                bottleTypeDisplay.textContent = "Plastic small";
            } else if (data.points === 1) {
                bottleTypeDisplay.textContent = "Crushed bottle";
            } else {
                bottleTypeDisplay.textContent = "Unknown";
            }

            // Save updated stats to server
            fetch('/update_scan_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    total_bottles: totalBottles,
                    total_points: totalPoints,
                    last_bottle_type: bottleTypeDisplay.textContent
                })
            })
            .then(res => {
                if (!res.ok) {
                    console.error('Failed to update scan data on server');
                }
            })
            .catch(err => {
                console.error('Error updating scan data:', err);
            });
        }
    })
    .catch(err => console.error("Fetch error:", err));
}

function startScanning() {
    if (!scanning) {
        scanning = true;
        scanInterval = setInterval(captureAndSend, 3000);
    }
}

function resetMetrics() {
    clearInterval(scanInterval);
    scanning = false;
    detections = [];
    totalBottles = 0;
    totalPoints = 0;

    pointsDisplay.textContent = "0";
    totalBottlesDisplay.textContent = "0";
    bottleTypeDisplay.textContent = "—";

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Reset data on server
    fetch('/update_scan_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            total_bottles: 0,
            total_points: 0,
            last_bottle_type: '—'
        })
    }).catch(err => console.warn('Failed to reset scan data on server:', err));
}
