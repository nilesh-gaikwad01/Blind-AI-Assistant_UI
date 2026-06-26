// Start webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        const video = document.getElementById("video");
        video.srcObject = stream;
        video.play();
    })
    .catch(err => {
        document.getElementById("status").innerText = "Camera access denied: " + err.message;
    });

// Send frame to Flask every 800ms
function sendFrame() {
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const preview = document.getElementById("preview");

    if (video.videoWidth === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    const data = canvas.toDataURL("image/jpeg", 0.7);
    preview.src = data;

    fetch(window.location.origin + "/upload_frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: data })
    }).catch(err => console.log("Frame upload error:", err));
}

setInterval(sendFrame, 800);

// Switch mode
function setMode(newMode) {
    fetch("/set_mode/" + newMode, { method: "POST" })
        .then(() => {
            document.getElementById("status").innerText = "Mode: " + newMode.toUpperCase();
        })
        .catch(err => console.log("Mode error:", err));
}

// Send SOS WhatsApp
function sendWhatsApp() {
    document.getElementById("status").innerText = "Sending SOS...";
    fetch("/whatsapp", { method: "POST" })
        .then(() => {
            document.getElementById("status").innerText = "SOS Sent!";
        })
        .catch(err => {
            document.getElementById("status").innerText = "Failed to send SOS";
        });
}