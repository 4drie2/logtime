# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    logtime.py                                         :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: abidaux <abidaux@student.42.fr>            +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/10/11 17:05:19 by abidaux           #+#    #+#              #
#    Updated: 2025/10/14 17:18:11 by abidaux          ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

from pathlib import Path
import requests
import calendar
from datetime import datetime, date, time, timedelta, timezone
from dateutil import parser
from typing import List, Dict
import os
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
API_BASE = "https://api.intra.42.fr/v2"
PER_PAGE = 100

_TOKEN = None
_TOKEN_EXP = datetime.min.replace(tzinfo=timezone.utc)

def get_token(session: requests.Session) -> str:
    global _TOKEN, _TOKEN_EXP
    now = datetime.now(timezone.utc)
    if _TOKEN and now < _TOKEN_EXP:
        return _TOKEN
    r = session.post(
        "https://api.intra.42.fr/oauth/token",
        data={"grant_type":"client_credentials","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()
    _TOKEN = data["access_token"]
    _TOKEN_EXP = now + timedelta(seconds=int(data.get("expires_in", 3600)) - 60)
    return _TOKEN

def fetch_all_locations(session: requests.Session, login: str) -> List[Dict]:
    token = get_token(session)
    headers = {"Authorization": f"Bearer {token}"}
    out = []
    page = 1
    while True:
        r = session.get(f"{API_BASE}/users/{login}/locations", headers=headers,
                        params={"page": page, "per_page": PER_PAGE}, timeout=10)
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        out.extend(data); page += 1
    return out

UTC = timezone.utc
def parse_dt(s: str) -> datetime:
    return parser.parse(s).astimezone(UTC)

def clamp_interval(a: datetime, b: datetime, start: datetime, end: datetime):
    s = max(a, start); e = min(b, end)
    return (s, e) if e > s else (None, None)

def overlap_seconds_interval(a: datetime, b: datetime) -> float:
    return max(0.0, (b - a).total_seconds())

# --- Core: logtime (with optional restriction 6h-22h lun-sam) ---
def daily_restricted_seconds(a: datetime, b: datetime) -> float:
    """Compte les secondes entre a et b qui tombent entre 06:00-22:00 du lundi au samedi."""
    total = 0.0
    start_day = a.date()
    end_day = b.date()
    for d_offset in range((end_day - start_day).days + 1):
        day = start_day + timedelta(days=d_offset)
        if day.weekday() >= 6:  # dimanche=6 -> exclu
            continue
        day_start = datetime.combine(day, time(6,0), tzinfo=UTC)
        day_end   = datetime.combine(day, time(22,0), tzinfo=UTC)
        s,e = clamp_interval(a, b, day_start, day_end)
        if s: total += overlap_seconds_interval(s,e)
    return total

def sum_logtime(locations: List[Dict], period_start: datetime, period_end: datetime, restricted: bool=False) -> float:
    total = 0.0
    for loc in locations:
        begin = parse_dt(loc["begin_at"])
        end = parse_dt(loc["end_at"]) if loc.get("end_at") else datetime.now(UTC)
        # limiter à la période demandée
        s,e = clamp_interval(begin, end, period_start, period_end)
        if not s: continue
        total += (daily_restricted_seconds(s,e) if restricted else overlap_seconds_interval(s,e))
    return total

# --- Petites fonctions utilitaires ---
def format_duration(seconds: float) -> str:
    h = int(seconds // 3600); m = int((seconds % 3600) // 60)
    return f"{h}h {m}min"

def days_in_month(dt: datetime) -> int:
    return calendar.monthrange(dt.year, dt.month)[1]

def working_days_between(start: date, end: date) -> List[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 6]

# --- Exemple d'utilisation / MAIN ---
if __name__ == "__main__":
    import tkinter as tk

    LOGIN = "abidaux"
    session = requests.Session()
    locs = fetch_all_locations(session, LOGIN)

    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    today_sec = sum_logtime(locs, day_start, now, restricted=False)
    month_sec = sum_logtime(locs, month_start, now, restricted=False)
    month_sec_restricted = sum_logtime(locs, month_start, now, restricted=True)

    dim = days_in_month(now)
    hr_req = 5 * dim  # 35h/semaine -> 5h/jour * jours du mois

    rem_hours = hr_req - (month_sec_restricted / 3600)
    end_of_month = (month_start + timedelta(days=dim-1)).replace(hour=23, minute=59, second=59)
    remaining_workdays = working_days_between((now + timedelta(days=1)).date(), end_of_month.date())
    n_days = len(remaining_workdays)
    per_day = (rem_hours / n_days) if n_days else 0

    # Affichage graphique stylisé avec Tkinter
    root = tk.Tk()
    root.title("Logtime 42")
    root.configure(bg="#f0f4f8")

    title = tk.Label(root, text="Résumé Logtime 42", font=("Arial", 18, "bold"), bg="#f0f4f8", fg="#2d415a")
    title.pack(pady=(18, 10))

    frame = tk.LabelFrame(root, text="Statistiques du mois", font=("Arial", 13, "bold"), bg="#e6ecf2", fg="#2d415a", bd=2, relief="groove", padx=18, pady=12, labelanchor='n')
    frame.pack(padx=24, pady=12)


    # Affichage séparé pour chaque donnée, mais regroupement visuel par espacement
    labels = [
        ("Mois", now.strftime('%B %Y')),
        ("Heures requises", f"{hr_req}h"),
        ("Tolérance (90%)", f"{hr_req*0.9:.1f}h"),
        ("Aujourd'hui", format_duration(today_sec)),
        ("Ce mois", format_duration(month_sec)),
        ("Heures restantes", f"{rem_hours:.1f}h"),
        ("Jours ouvrés restants", str(n_days)),
    ]
    if n_days:
        labels.append(("Par jour ouvré restant", format_duration(per_day * 3600)))


    # Espacement visuel entre groupes
    group_gaps = [1, 3, 6]  # après ces indices, on ajoute un espace plus grand

    for i, (label_txt, value) in enumerate(labels):
        pady = 12 if i in group_gaps else 4
        l = tk.Label(frame, text=label_txt, font=("Arial", 12, "bold"), bg="#e6ecf2", fg="#2d415a", bd=1, relief="solid", width=22, anchor="e")
        l.grid(row=i, column=0, sticky="e", padx=(0, 8), pady=pady, ipady=3)
        v = tk.Label(frame, text=value, font=("Arial", 12), bg="#ffffff", fg="#1a2733", bd=1, relief="solid", width=18, anchor="w")
        v.grid(row=i, column=1, sticky="w", padx=(0, 0), pady=pady, ipady=3)

    # Ajout de deux barres de progression : progression du mois (en jours) et progression du mois en logtime (non restreint)
    bar_width = 320
    bar_height = 18
    bar_bg = "#dbe6ee"
    bar_fg = "#4a90e2"

    # Progression du mois (en jours)
    total_days = days_in_month(now)
    current_day = now.day
    progress_days = min(1.0, current_day / total_days) if total_days > 0 else 0
    progress_label1 = tk.Label(frame, text="Progression du mois (en jours)", font=("Arial", 11, "bold"), bg="#e6ecf2", fg="#2d415a")
    progress_label1.grid(row=len(labels)+1, column=0, columnspan=2, pady=(18, 2))
    canvas1 = tk.Canvas(frame, width=bar_width, height=bar_height, bg="#e6ecf2", highlightthickness=0)
    canvas1.grid(row=len(labels)+2, column=0, columnspan=2, pady=(0, 10))
    canvas1.create_rectangle(0, 0, bar_width, bar_height, fill=bar_bg, outline=bar_bg, width=0)
    fill_width1 = int(bar_width * progress_days)
    if fill_width1 > 0:
        canvas1.create_rectangle(0, 0, fill_width1, bar_height, fill=bar_fg, outline=bar_fg, width=0)
    percent1 = int(progress_days * 100)
    canvas1.create_text(bar_width//2, bar_height//2, text=f"{percent1}%", fill="#2d415a", font=("Arial", 11, "bold"))

    # Progression du mois en logtime (non restreint)
    progress_logtime = min(1.0, month_sec / (hr_req * 3600)) if hr_req > 0 else 0
    progress_label2 = tk.Label(frame, text="Progression du mois en logtime", font=("Arial", 11, "bold"), bg="#e6ecf2", fg="#2d415a")
    progress_label2.grid(row=len(labels)+3, column=0, columnspan=2, pady=(8, 2))
    canvas2 = tk.Canvas(frame, width=bar_width, height=bar_height, bg="#e6ecf2", highlightthickness=0)
    canvas2.grid(row=len(labels)+4, column=0, columnspan=2, pady=(0, 10))
    canvas2.create_rectangle(0, 0, bar_width, bar_height, fill=bar_bg, outline=bar_bg, width=0)
    fill_width2 = int(bar_width * progress_logtime)
    if fill_width2 > 0:
        canvas2.create_rectangle(0, 0, fill_width2, bar_height, fill=bar_fg, outline=bar_fg, width=0)
    percent2 = int(progress_logtime * 100)
    canvas2.create_text(bar_width//2, bar_height//2, text=f"{percent2}%", fill="#2d415a", font=("Arial", 11, "bold"))

    root.mainloop()
