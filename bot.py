import os
import asyncio
import logging
import aiohttp
import socket
import time
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ----- Logging -----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ----- Config -----
@dataclass
class NodeConfig:
    name: str
    dashboard: str
    public_address: str

@dataclass
class ChecksConfig:
    disk_free_min_gb: int
    disk_free_min_percent: int
    request_timeout_ms: int
    enable_quic_check: bool

@dataclass
class AppConfig:
    nodes: List[NodeConfig]
    checks: ChecksConfig

# ----- Helpers -----
def load_env_from_file(path: str = ".env"):
    load_dotenv(path)

def cooldown_ok(key: str, cooldown: int) -> bool:
    now = time.time()
    last = COOLDOWNS.get(key, 0)
    if now - last >= cooldown:
        COOLDOWNS[key] = now
        return True
    return False

async def http_check(url: str, timeout: float = 3.0) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as resp:
                return resp.status == 200
    except Exception:
        return False

def tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def udp_probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(b"ping", (host, port))
        sock.close()
        return True
    except Exception:
        return False

# ----- Globals -----
COOLDOWNS = {}
SUBSCRIBERS = set()

# ----- Bot commands -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text("✅ You are subscribed for Storj node alerts.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text("❌ You are unsubscribed from Storj node alerts.")

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sec = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /interval <seconds>")
        return
    context.bot_data["interval"] = max(15, min(sec, 3600))
    await update.message.reply_text(f"⏱ Interval set to {context.bot_data['interval']} sec")

# ----- Polling loop -----
async def poll_loop(app, cfg: AppConfig):
    interval = app.bot_data.get("interval", int(os.getenv("POLL_INTERVAL_SECONDS", "60")))
    cooldown = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))
    timeout = cfg.checks.request_timeout_ms / 1000
    allowed_ids = {int(x.strip()) for x in os.getenv("TELEGRAM_USER_IDS", "").split(",") if x.strip().isdigit()}

    while True:
        try:
            texts = []
            for n in cfg.nodes:
                host, port = n.public_address.split(":")
                dash_ok = await http_check(n.dashboard, timeout)
                tcp_ok = tcp_check(host, int(port), timeout)
                udp_ok = udp_probe(host, int(port), timeout) if cfg.checks.enable_quic_check else None

                if not dash_ok or not tcp_ok:
                    key = f"down:{n.name}"
                    if cooldown_ok(key, cooldown):
                        msg = f"⚠️ {n.name}: dashboard={'OK' if dash_ok else 'FAIL'}, tcp={'OK' if tcp_ok else 'FAIL'}"
                        if udp_ok is not None:
                            msg += f", udp={'OK' if udp_ok else 'FAIL'}"
                        texts.append(msg)

            if texts and SUBSCRIBERS:
                for uid in list(SUBSCRIBERS):
                    if allowed_ids and uid not in allowed_ids:
                        continue
                    for msg in texts:
                        try:
                            await app.bot.send_message(chat_id=uid, text=msg)
                        except Exception as e:
                            logging.warning(f"Send failed: {e}")

        except Exception as e:
            logging.exception(f"Poll loop error: {e}")

        await asyncio.sleep(interval)

# ----- Main -----
async def main():
    load_env_from_file(os.getenv("ENV_PATH", ".env"))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    cfg = AppConfig(
        nodes=[
            NodeConfig(
                name="node1",
                dashboard="http://localhost:14002",
                public_address="mynode.ddns.net:28967",
            )
        ],
        checks=ChecksConfig(
            disk_free_min_gb=20,
            disk_free_min_percent=5,
            request_timeout_ms=2500,
            enable_quic_check=True,
        ),
    )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("interval", set_interval))

    app.bot_data["interval"] = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

    loop = asyncio.get_event_loop()
    loop.create_task(poll_loop(app, cfg))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
