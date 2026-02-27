# WS2TCPLink 🌐

**WS2TCPLink** is a high-performance, universal WebSocket-to-TCP bridge designed for Docker environments. It features a beautiful "Frutiger Aero" glassmorphism interface and allows web-based clients to communicate with standard TCP socket servers.



## ✨ Features
* **Docker Native:** Designed to run in isolated containers with persistent configuration.
* **Auto-Protocol Detection:** Intelligently handles both binary and text streams.
* **Aero Glass UI:** Responsive web dashboard with real-time connection tracking.
* **Asynchronous Core:** Built on `asyncio` for high-concurrency handling.
* **Websocket SSL/TLS Support:** Supports TLS/SSL Certificate storage and usage with WSS

---
  
<img width="1515" height="810" alt="image" src="https://github.com/user-attachments/assets/01e00206-1800-4526-a9e7-aa896d8fae94" />


---

## 🚀 Deployment

### 1. Build and Run (Standard)
To build the image and run it with a range of ports enabled for bridges:

```bash
# Clone Repo
git clone https://github.com/comcad/WS2TCPLink.git
cd ws2tcplink
```

```bash
# Build the image
docker build -t ws2tcplink .
```
```
# Change Webui Username and password by editing the dockercompose.yml

sudo nano dockercompose.yml

# Change to your desired credentials
ADMIN_USER=
ADMIN_PASS=
```
```
# Run the container
docker compose up -d
```
```
# Access Web UI
http://localhost:8181/
```
