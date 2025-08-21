🚀 Storj Node on Windows (Docker) — Step-by-Step Guide + Telegram Monitor Bot

Production-ready, hand-holding tutorial from zero to a working Storj node AND a monitoring Telegram bot. Covers: Identity on Windows (the AppData\Roaming gotcha), public IP vs CGNAT, DDNS (No-IP), router port forwarding, Windows Firewall, Docker run, QUIC (UDP), verification, scaling to node2/node3, and a complete step-by-step Telegram bot setup (BotFather → .env → config.yaml → python bot.py → Windows autostart).

✅ All node examples start with Node #1 canonical ports: 28967 (TCP/UDP) for traffic and 14002 (TCP) for dashboard (local only).

⸻

0) Prerequisites
	•	Windows 10/11 (Admin), stable internet.
	•	Public IP (static or dynamic) or DDNS (No-IP). If CGNAT → ask ISP for a public IP (port forwarding won’t work under CGNAT).
	•	Access to your home router (you can edit port forwarding).
	•	Docker Desktop installed (WSL2 engine enabled).
	•	Free disk space (e.g., 4.5TB).
	•	Wallet (EVM) and email.

⸻

1) Install Docker Desktop (Windows)
	1.	Download Docker Desktop for Windows from the official site.
	2.	Install → enable “Use the WSL 2 based engine”.
	3.	Reboot if prompted.
	4.	Open Docker Desktop → Settings → Resources → File Sharing → add the drive/folder you’ll use (for example D:\) so Docker can mount it.

⸻

2) Identity — Download, Authorize, Verify (Windows)

Storj requires a node identity. The Windows tool is identity.exe.

IMPORTANT: After generation, identity files are created in
%AppData%\Storj\Identity\storagenode
(example: C:\Users\<User>\AppData\Roaming\Storj\Identity\storagenode).
You MUST move them into your identity folder (example D:\identity_node1).

Steps:

	1.	Download the Windows identity CLI (identity_windows_amd64.zip) from the official Storj docs → Identity → Windows.
 
Extract to C:\identity_windows_amd64\ (so you have identity.exe there).

	2.	Request an auth token in Storj web UI (satellite). Format looks like you@email.com:LONG_TOKEN.
 
	3.	PowerShell as Administrator:
 
& "C:\identity_windows_amd64\identity.exe" create storagenode
& "C:\identity_windows_amd64\identity.exe" authorize storagenode you@example.com:YOUR_AUTH_TOKEN
(Optional) & "C:\identity_windows_amd64\identity.exe" verify storagenode

	4.	Move the created files (ca.cert, ca.key, identity.cert, identity.key) from
%AppData%\Storj\Identity\storagenode → D:\identity_node1.

Rule: One node = one identity. Never reuse the same identity for multiple nodes.

⸻

3) Prepare Node #1 folders

Create:
	•	D:\identity_node1  (put identity files here)
	•	D:\storj-node1     (node config + data root; “storage” will be created by setup)

Mount the ROOT D:\storj-node1 to /app/config (do NOT mount directly to .../storage).

⸻

4) Networking — Public IP / DDNS (No-IP) / Router Forwarding / Firewall

Storj must reach you externally on port 28967 (TCP and UDP).

Public IP vs CGNAT:
	•	Check your router’s WAN IP; compare with “what is my IP”.
	•	If router shows private/CGNAT ranges (10.x, 172.16–31.x, 192.168.x, or 100.64.0.0/10) → CGNAT. Ask ISP for a public IP; otherwise port forwarding won’t work.

DDNS (No-IP) if your public IP is dynamic:
	•	Create a No-IP account and hostname (e.g., mynode.ddns.net).
	•	Configure DDNS in your router (preferred) or install No-IP DUC updater on Windows.
	•	You will use ADDRESS="mynode.ddns.net:28967".

Reserve a static LAN IP:
	•	In router DHCP reservation, bind your PC MAC to a fixed LAN IP (e.g., 192.168.1.50).

Port forwarding (router):
	•	Forward 28967 TCP → 192.168.1.50
	•	Forward 28967 UDP → 192.168.1.50

Windows Firewall (PowerShell as Admin):
	•	Allow inbound TCP 28967
	•	Allow inbound UDP 28967
	•	Optionally allow local dashboard TCP 14002 for Private profile
(Keep dashboard 14002 closed to the internet.)

⸻

5) Run Node #1 with Docker — Setup then Run

Ensure Docker Desktop is running and D:\ is shared in Docker settings.

Setup (one-time; creates config and storage in D:\storj-node1):
	•	docker run --rm -it -p 28967:28967/tcp -p 28967:28967/udp -p 14002:14002 --name storagenode1 --mount type=bind,source=D:\identity_node1,destination=/app/identity --mount type=bind,source=D:\storj-node1,destination=/app/config storjlabs/storagenode:latest setup

Run (persistent service):
	•	docker run -d -p 28967:28967/tcp -p 28967:28967/udp -p 14002:14002 --restart unless-stopped --name storagenode1 --mount type=bind,source=D:\identity_node1,destination=/app/identity --mount type=bind,source=D:\storj-node1,destination=/app/config --env WALLET="0xYOUR_WALLET" --env EMAIL="you@example.com" --env ADDRESS="mynode.ddns.net:28967" --env STORAGE="4.5TB" storjlabs/storagenode:latest

⸻

6) Verify Node

Logs:
	•	docker logs -f storagenode1
Look for “Node started”, “listening on …:28967”, “quic server is enabled”, then later PUT, PUT_REPAIR, UPLOADED.

Dashboard:
	•	http://localhost:14002 (keep local)

External port test:
	•	Confirm TCP 28967 from outside your LAN. QUIC uses UDP 28967 (see notes).

⸻

7) QUIC (UDP) Notes

QUIC requires UDP 28967 forwarded in the router and allowed in Windows Firewall. If warnings persist, re-check rules and ask your ISP whether UDP is blocked/shaped. Node still works on TCP but less optimal.

⸻

8) Scale to Node #2 / Node #3 (quick reference)

Each extra node needs a NEW identity, new folders, and UNIQUE ports.

Node #2:
	•	Open/forward 28968 TCP+UDP, map dashboard 14003
	•	Run with -p 28968:28967/tcp -p 28968:28967/udp -p 14003:14002
	•	ADDRESS="mynode.ddns.net:28968"

Node #3:
	•	Open/forward 28969 TCP+UDP, map dashboard 14004
	•	ADDRESS="mynode.ddns.net:28969"

⸻

9) Telegram Monitor Bot — Step-by-Step

Create the bot (BotFather):
	1.	In Telegram, open @BotFather → /start → /newbot.
	2.	Choose a bot name and unique username (must end with “bot”).
	3.	Copy the HTTP API token (format 123456:ABC-...). Keep it secret.

Prepare the project on Windows:
	•	Create a folder for the bot, example D:\storj-bot\.
	•	You will put these files into it: bot.py, requirements.txt, .env.example, .env, config.yaml (see file contents in this repository).

Python & dependencies:
	•	Install Python 3.11+ if needed.
	•	Create venv and install deps:
	•	python -m venv D:\storj-bot\.venv
	•	D:\storj-bot\.venv\Scripts\activate
	•	pip install -r D:\storj-bot\requirements.txt

Configure environment:
	•	Copy .env.example → .env and edit values (token, your Telegram user ID(s), etc.)

Configure nodes:
	•	Edit config.yaml for your dashboard URL and public address/port (see example in this repository).

Run the bot:
	•	Activate venv: D:\storj-bot\.venv\Scripts\activate
	•	Start: python D:\storj-bot\bot.py

Test in Telegram:
	•	Send /start, then /status, /nodes, /node node1.

Autostart on Windows (two options):
	•	Task Scheduler → Create Task → Trigger “At log on” → Action: D:\storj-bot\.venv\Scripts\python.exe with arguments D:\storj-bot\bot.py, Start in: D:\storj-bot\.
	•	Or NSSM service: nssm install storj-bot "D:\storj-bot\.venv\Scripts\python.exe" "D:\storj-bot\bot.py"

⸻

10) Troubleshooting (read me first)

Identity / files:
	•	Files are under %AppData%\Storj\Identity\storagenode → move to D:\identity_node1.
	•	Not authorized? Re-run authorize with correct email:token, then verify.
	•	Never reuse one identity for multiple nodes.

Mounts / paths:
	•	Mount /app/config to the ROOT node folder (e.g., D:\storj-node1), not directly to storage.
	•	If Docker can’t see your drive, add it in Docker Desktop → File Sharing.
	•	Paths with spaces must be quoted.

Ports / networking:
	•	No traffic → router forwarding missing/incorrect, firewall blocked, CGNAT, or wrong ADDRESS (DDNS not updated).
	•	CGNAT → request public IP or switch plan/provider.
	•	Double NAT (ISP modem + your router) → bridge the modem or set DMZ to your router.
	•	QUIC warning → UDP 28967 not forwarded/blocked; TCP still works.

Dashboard:
	•	http://localhost:14002 unavailable → ensure -p 14002:14002 and firewall local allow; check docker ps.

Docker / service:
	•	Docker not running → start Desktop first.
	•	Update the container:
	•	docker pull storjlabs/storagenode:latest
	•	docker stop storagenode1 && docker rm storagenode1
	•	re-run the same docker run command.

Storage / data:
	•	Intentional reset may require removing old DBs in storage (advanced; risk of data loss).
	•	Disable Windows sleep while node runs (Power Options).

DDNS:
	•	Dynamic IP changed → ensure router DDNS client or No-IP DUC is updating your hostname.

⸻

11) Useful commands
	•	Running containers: docker ps
	•	Follow logs: docker logs -f storagenode1
	•	Restart node: docker restart storagenode1
	•	Stop & remove container (data stays on disk): docker stop storagenode1 && docker rm storagenode1
	•	Quick TCP check from the node: Test-NetConnection mynode.ddns.net -Port 28967

⸻

12) License

Guide: CC BY 4.0
Bot code: MIT

Contact for setup/custom monitoring: Telegram @isparksg • Email isparksg@gmail.com

⸻

13) Repository Files (this project)
	•	README.md (this file)
	•	bot.py (Telegram monitor)
	•	.env.example
	•	config.yaml
	•	requirements.txt
	•	LICENSE (MIT suggested for the bot code)

