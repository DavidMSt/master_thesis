import asyncio
from aiohttp import web, ClientSession, ClientWebSocketResponse
from typing import Dict
import os
import json
import signal

# Static routes
STATIC_HOSTNAME_TO_PORT = {
    "app1.local": 9001,
    "app2.local": 9002,
    "app3.local": 9003,
}

ROUTES_FILE = os.path.join(os.path.dirname(__file__), "routes.json")

# Dynamic routes
DYNAMIC_HOSTNAME_TO_PORT: Dict[str, int] = {}
HOSTS_LOCK = asyncio.Lock()


def is_valid_hostname(hostname: str) -> bool:
    return bool(hostname and "." in hostname and " " not in hostname)


def is_valid_port(port: int) -> bool:
    return isinstance(port, int) and 1 <= port <= 65535


async def get_port_for_host(hostname: str) -> int:
    async with HOSTS_LOCK:
        return DYNAMIC_HOSTNAME_TO_PORT.get(hostname) or STATIC_HOSTNAME_TO_PORT.get(hostname)


async def load_routes_from_disk():
    if os.path.exists(ROUTES_FILE):
        try:
            with open(ROUTES_FILE, "r") as f:
                data = json.load(f)
                async with HOSTS_LOCK:
                    DYNAMIC_HOSTNAME_TO_PORT.clear()
                    DYNAMIC_HOSTNAME_TO_PORT.update(data)
            print(f"📥 Loaded {len(DYNAMIC_HOSTNAME_TO_PORT)} routes from disk")
        except Exception as e:
            print(f"⚠️ Failed to load routes from disk: {e}")


async def save_routes_to_disk():
    try:
        print("💾 Attempting to save routes...")
        with open(ROUTES_FILE, "w") as f:
            json.dump(DYNAMIC_HOSTNAME_TO_PORT, f, indent=2)
        print(f"💾 Saved {len(DYNAMIC_HOSTNAME_TO_PORT)} routes to disk")
    except Exception as e:
        print(f"⚠️ Failed to save routes: {e}")


async def handle_proxy(request):
    hostname = request.headers.get("Host", "")
    port = await get_port_for_host(hostname)

    if not port:
        return web.Response(status=502, text=f"Unknown host: {hostname}")

    if request.headers.get("Upgrade", "").lower() == "websocket":
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(request)

        ws_url = f"http://127.0.0.1:{port}{request.rel_url}"
        async with ClientSession() as session:
            async with session.ws_connect(ws_url.replace("http", "ws")) as ws_client:

                async def ws_forward(ws_from, ws_to):
                    async for msg in ws_from:
                        if msg.type == web.WSMsgType.TEXT:
                            await ws_to.send_str(msg.data)
                        elif msg.type == web.WSMsgType.BINARY:
                            await ws_to.send_bytes(msg.data)
                        elif msg.type == web.WSMsgType.CLOSE:
                            await ws_to.close()
                        elif msg.type == web.WSMsgType.ERROR:
                            break

                await asyncio.gather(
                    ws_forward(ws_server, ws_client),
                    ws_forward(ws_client, ws_server)
                )

        return ws_server

    # Regular HTTP forward
    target_url = f"http://127.0.0.1:{port}{request.rel_url}"
    async with ClientSession() as session:
        async with session.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                data=await request.read()
        ) as resp:
            body = await resp.read()
            return web.Response(
                status=resp.status,
                body=body,
                headers=resp.headers
            )


async def register_host(request):
    data = await request.json()
    hostname = data.get("hostname")
    port = data.get("port")

    if not is_valid_hostname(hostname) or not is_valid_port(port):
        return web.Response(status=400, text="Invalid hostname or port")

    if hostname in STATIC_HOSTNAME_TO_PORT:
        return web.Response(status=400, text="Cannot overwrite static route")

    async with HOSTS_LOCK:
        DYNAMIC_HOSTNAME_TO_PORT[hostname] = port
        print(f"✅ Registered: {hostname} -> {port}")
        await save_routes_to_disk()

    return web.Response(text=f"Registered {hostname} -> {port}")


async def unregister_host(request):
    data = await request.json()
    hostname = data.get("hostname")

    if not is_valid_hostname(hostname):
        return web.Response(status=400, text="Invalid hostname")

    async with HOSTS_LOCK:
        removed = DYNAMIC_HOSTNAME_TO_PORT.pop(hostname, None)
        if removed:
            print(f"❌ Unregistered: {hostname}")
            await save_routes_to_disk()
            return web.Response(text=f"Unregistered {hostname}")
        else:
            return web.Response(status=404, text="Hostname not found in dynamic routes")


async def list_routes(request):
    async with HOSTS_LOCK:
        combined = {**STATIC_HOSTNAME_TO_PORT, **DYNAMIC_HOSTNAME_TO_PORT}
        return web.json_response(combined)


async def static_routes(request):
    return web.json_response(STATIC_HOSTNAME_TO_PORT)


async def admin_ui(request):
    return web.Response(content_type="text/html", text="""
<!DOCTYPE html>
<html>
<head>
    <title>Reverse Proxy Admin</title>
    <style>
        body {
            font-family: sans-serif;
            padding: 2rem;
            background: #f9f9f9;
        }
        h1 {
            color: #333;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 1rem;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 0.5rem;
            text-align: left;
        }
        th {
            background-color: #eee;
        }
        input, button {
            margin: 0.5rem 0;
            padding: 0.5rem;
            font-size: 1rem;
        }
    </style>
</head>
<body>
    <h1>🛠 Reverse Proxy Admin</h1>
      <div>
        <h3>Add Route</h3>
        <input id="hostname" placeholder="Hostname (e.g. myapp.local)" />
        <input id="port" type="number" placeholder="Port (e.g. 8080)" />
        <button onclick="registerRoute()">Register</button>
        <div id="message" style="color: red; margin-top: 0.5rem;"></div>
    </div>

    <h3>Active Routes</h3>
    <table id="routesTable">
        <thead><tr><th>Hostname</th><th>Port</th><th>Type</th><th>Action</th></tr></thead>
        <tbody></tbody>
    </table>

    <script>
    let staticHosts = [];

    async function fetchStaticRoutes() {
        const res = await fetch('/_static_routes');
        staticHosts = Object.keys(await res.json());
    }

    async function fetchRoutes() {
        const res = await fetch('/_routes');
        const data = await res.json();
        const table = document.querySelector("#routesTable tbody");
        table.innerHTML = "";
        for (const [host, port] of Object.entries(data)) {
            const isStatic = staticHosts.includes(host);
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${host}</td>
                <td>${port}</td>
                <td>${isStatic ? "static" : "dynamic"}</td>
                <td>
                    ${isStatic ? "-" : `<button onclick="unregisterRoute('${host}')">Remove</button>`}
                </td>
            `;
            table.appendChild(row);
        }
    }

    function showMessage(text, isError = true) {
        const msg = document.getElementById("message");
        msg.style.color = isError ? "red" : "green";
        msg.textContent = text;
    }

    function clearMessage() {
        document.getElementById("message").textContent = "";
    }

    async function registerRoute() {
        clearMessage();
        const hostname = document.getElementById("hostname").value.trim();
        const port = parseInt(document.getElementById("port").value);
        if (!hostname || !port) {
            showMessage("Please enter a valid hostname and port.");
            return;
        }

        const res = await fetch('/_register', {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname, port })
        });

        if (res.ok) {
            showMessage("✅ Route registered.", false);
            await fetchRoutes();
        } else {
            const text = await res.text();
            showMessage(`❌ ${text}`);
        }
    }

    async function unregisterRoute(hostname) {
        clearMessage();
        if (!confirm(`Remove ${hostname}?`)) return;

        const res = await fetch('/_unregister', {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname })
        });

        if (res.ok) {
            showMessage("✅ Route removed.", false);
            await fetchRoutes();
        } else {
            const text = await res.text();
            showMessage(`❌ ${text}`);
        }
    }

    (async () => {
        await fetchStaticRoutes();
        await fetchRoutes();
    })();
</script>

</body>
</html>
""")


async def start_reverse_proxy():
    await load_routes_from_disk()
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handle_proxy)
    app.router.add_post('/_register', register_host)
    app.router.add_post('/_unregister', unregister_host)
    app.router.add_get('/_routes', list_routes)
    app.router.add_get('/_static_routes', static_routes)
    app.router.add_get('/admin', admin_ui)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=80)
    await site.start()
    print("🔁 Reverse proxy listening on port 80")

    stop_event = asyncio.Event()

    def shutdown():
        print("🛑 Gracefully shutting down...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    await stop_event.wait()
    await runner.cleanup()
    print("✅ Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(start_reverse_proxy())
    except PermissionError:
        print("❌ You need sudo to bind to port 80 on macOS/Linux")

"""
======================
💡 EXAMPLE USAGE (cURL)
======================

# Register a new route:
curl -X POST http://localhost/_register \
     -H "Content-Type: application/json" \
     -d '{"hostname": "myapp.local", "port": 8080}'

# Unregister a route:
curl -X POST http://localhost/_unregister \
     -H "Content-Type: application/json" \
     -d '{"hostname": "myapp.local"}'

# List all routes:
curl http://localhost/_routes

==========================
💡 EXAMPLE USAGE (Python)
==========================

import requests

# Register a new route
requests.post("http://localhost/_register", json={
    "hostname": "myapp.local",
    "port": 8080
})

# Unregister a route
requests.post("http://localhost/_unregister", json={
    "hostname": "myapp.local"
})

# List all routes
response = requests.get("http://localhost/_routes")
print(response.json())
"""
