#!/usr/bin/env bash
# نصب ربات گپ روی Ubuntu/Debian
set -e
APP_DIR=/opt/gap-bot
SERVICE=gap-bot

if [ "$EUID" -ne 0 ]; then echo "با root اجرا کنید: sudo bash install.sh"; exit 1; fi

apt update -y
apt install -y python3 python3-venv python3-pip

mkdir -p "$APP_DIR"
cp -r ./* "$APP_DIR"/
cd "$APP_DIR"

if [ ! -f .env ]; then
  read -rp "توکن ربات (از BotFather): " TOKEN
  read -rp "آیدی عددی ادمین (چندتا را با کاما جدا کنید): " ADMINS
  read -rp "پروکسی (اختیاری، مثل socks5://127.0.0.1:1080؛ خالی = بدون پروکسی): " PROXY
  cat > .env <<ENV
BOT_TOKEN=$TOKEN
ADMIN_IDS=$ADMINS
PROXY=$PROXY
DB_PATH=data/bot.db
ENV
fi

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

cat > /etc/systemd/system/$SERVICE.service <<UNIT
[Unit]
Description=Telegram Gap Bot
After=network-online.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now $SERVICE
echo ""
echo "انجام شد. وضعیت: systemctl status $SERVICE"
echo "لاگ‌ها: journalctl -u $SERVICE -f"
