// login.js

function submitLogin() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    if (!email || !password) {
        alert("Please fill in all fields.");
        return;
    }

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({ email, password })
    })
    .then(res => {
        if (res.redirected) {
            window.location.href = res.url; // Redirect to dashboard or wherever
        } else {
            return res.text();
        }
    })
    .then(data => {
        if (data) alert("Login failed. Check credentials.");
    })
    .catch(err => console.error("Login error:", err));
}

// --- QR code scanning logic ---

const video = document.getElementById('qr-video');
const startBtn = document.getElementById('start-qr-btn');
const qrResult = document.getElementById('qr-result');
let scanning = false;
let videoStream = null;

startBtn.onclick = () => {
    qrResult.textContent = '';
    if (scanning) {
        stopScan();
    } else {
        startScan();
    }
};

function startScan() {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
        .then(function(stream) {
            scanning = true;
            videoStream = stream;
            video.srcObject = stream;
            video.setAttribute("playsinline", true); // required for iOS
            video.style.display = "block";
            video.play();
            tick();
            startBtn.textContent = "Stop QR Scanner";
        })
        .catch(err => {
            qrResult.style.color = "red";
            qrResult.textContent = "Camera access denied or not available.";
        });
}

function stopScan() {
    scanning = false;
    startBtn.textContent = "Login with QR Code";
    video.style.display = "none";
    qrResult.textContent = '';
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
}

function tick() {
    if (!scanning) return;

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);

        if (code) {
            // QR code detected
            stopScan();
            qrResult.style.color = "green";
            qrResult.textContent = "QR Code detected. Logging in...";
            sendQRCode(code.data.trim());
            return;
        }
    }
    requestAnimationFrame(tick);
}

function sendQRCode(studentId) {
    fetch("/login_qr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Redirect to scan or dashboard
            window.location.href = data.redirect_url;
        } else {
            qrResult.style.color = "red";
            qrResult.textContent = data.message || "Login failed.";
        }
    })
    .catch(() => {
        qrResult.style.color = "red";
        qrResult.textContent = "Server error during login.";
    });
}
