const video = document.getElementById('video');
const canvas = document.createElement('canvas');
const resultImg = document.getElementById('result');
const pointsDisplay = document.getElementById('points');

navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;

        // Start scanning every 3 seconds
        setInterval(captureAndSend, 3000);
    })
    .catch(err => {
        console.error("Failed to access webcam:", err);
    });

function captureAndSend() {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg');

    fetch('/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error("Detection error:", data.error);
            } else {
                pointsDisplay.textContent = "Points: " + data.points;
                resultImg.src = data.image;
            }
        })
        .catch(err => console.error("Fetch error:", err));
}
