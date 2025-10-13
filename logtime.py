# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    logtime.py                                         :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: abidaux <abidaux@student.42.fr>            +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/10/11 17:05:19 by abidaux           #+#    #+#              #
#    Updated: 2025/10/13 14:12:10 by abidaux          ###   ########.fr        #
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

# Charger les variables d'environnement depuis ce chemin spécifique


# --- CONFIG ---
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
API_BASE = "https://api.intra.42.fr/v2"
PER_PAGE = 100

# --- TOKEN CACHE ---
_TOKEN = None
_TOKEN_EXP = datetime.min.replace(tzinfo=timezone.utc)

def get_token(session: requests.Session) -> str:
    """Renvoie un token OAuth2 (cache simple avec expiration)."""
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
    """Récupère toutes les locations paginées pour un user."""
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

# --- Utils datetime ---
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
    """Somme des secondes de logtime entre period_start et period_end.
       Si restricted=True, applique la règle 06:00-22:00 lun-sam."""
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
    LOGIN = "abidaux"  # change si besoin
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

    print(f"{now.strftime('%B %Y')}: req={hr_req}h, tol={hr_req*0.9:.1f}h")
    print(f"Aujourd'hui: {format_duration(today_sec)} — Ce mois: {format_duration(month_sec)}")
    print(f"Ce mois (restreint): {format_duration(month_sec_restricted)}")
    print(f"Heures restantes: {rem_hours:.1f}h — Jours ouvrés restants: {n_days}")
    if n_days:
        print(f"≈ {format_duration(per_day * 3600)} par jour ouvré restant")
