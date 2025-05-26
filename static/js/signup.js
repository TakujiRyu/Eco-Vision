let scanning = false;
let qrVideo, qrResult;

function validateSignupForm() {
    const emailInput = document.getElementById('email');
    const email = emailInput.value.trim();
    const emailValidationMsg = document.getElementById('emailValidation');

    const emailPattern = /^[a-zA-Z0-9]+\.gcit@rub\.edu\.bt$/;

    if (!emailPattern.test(email)) {
        emailValidationMsg.textContent = "Email must be in the format: studentid.gcit@rub.edu.bt";
        emailValidationMsg.style.color = "red";
        emailInput.focus();
        return false;
    }

    emailValidationMsg.textContent = "";
    return true;
}

function submitSignup() {
    if (!validateSignupForm()) return;

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    if (!email || !password) {
        alert("Please fill in all fields.");
        return;
    }

    fetch('/signUp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ email, password })
    })
    .then(res => {
        if (res.redirected) {
            window.location.href = res.url;
        } else {
            return res.text();
        }
    })
    .then(data => {
        if (data) alert("Signup failed. Email may already be in use.");
    })
    .catch(err => console.error("Signup error:", err));
}

// QR Code Signup Logic
document.getElementById('start-qr-btn').addEventListener('click', startScan);
document.getElementById('email').addEventListener('input', () => {
    document.getElementById('emailValidation').textContent = '';
});

function startScan() {
    qrVideo = document.getElementById('qr-video');
    qrResult = document.getElementById('qr-result');
    qrVideo.style.display = 'block';
    qrResult.textContent = "Scanning for QR code...";

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => {
            qrVideo.srcObject = stream;
            qrVideo.setAttribute('playsinline', true); // required to tell iOS safari we don't want fullscreen
            qrVideo.play();
            scanning = true;
            requestAnimationFrame(tick);
        })
        .catch(err => {
            qrResult.textContent = "Camera access denied.";
            console.error("Camera error:", err);
        });
}

function stopScan() {
    scanning = false;
    qrVideo.pause();
    if (qrVideo.srcObject) {
        qrVideo.srcObject.getTracks().forEach(track => track.stop());
    }
    qrVideo.style.display = 'none';
}

function tick() {
    if (!scanning) return;

    if (qrVideo.readyState !== qrVideo.HAVE_ENOUGH_DATA) {
        requestAnimationFrame(tick);
        return;
    }

    if (qrVideo.videoWidth === 0 || qrVideo.videoHeight === 0) {
        console.log("Waiting for video dimensions...");
        requestAnimationFrame(tick);
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = qrVideo.videoWidth;
    canvas.height = qrVideo.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(qrVideo, 0, 0, canvas.width, canvas.height);

    try {
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, canvas.width, canvas.height, {
            inversionAttempts: "dontInvert",
        });

        if (code) {
            const studentId = code.data.trim().toLowerCase();
            const email = `${studentId}.gcit@rub.edu.bt`;

            stopScan();
            qrResult.textContent = "QR Code detected! Filling up details...";

            // Autofill email and focus password field
            document.getElementById('email').value = email;
            document.getElementById('password').focus();
        } else {
            requestAnimationFrame(tick);
        }
    } catch (e) {
        console.error("Canvas/image processing error:", e);
        requestAnimationFrame(tick);
    }
}
