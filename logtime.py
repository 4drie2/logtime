import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timedelta, time
import calendar
from zoneinfo import ZoneInfo  # Nécessite Python 3.9+

# --- ⚠️ Configuration ---
# REMPLACEZ AVEC VOS PROPRES IDENTIFIANTS
# NE PARTAGEZ JAMAIS CES INFORMATIONS
UID = "u-s4t2ud-feee8fe2e486c5b8283d09761378064997fd711c91d4f369429ef11967eb5df3"
SECRET = "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"
LOGIN_42 = "abidaux"
# -------------------------

# Configuration de l'API et du fuseau horaire
API_URL = "https://api.intra.42.fr"
TOKEN_URL = f"{API_URL}/oauth/token"
LOCAL_TZ_NAME = "Europe/Paris"  # Fuseau horaire pour la restriction 6h-22h

class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Tracker d'heures 42 - {LOGIN_42}")
        self.root.geometry("350x435")

        self.style = ttk.Style(self.root)
        self.style.configure("TLabel", padding=5, font=("Arial", 10))
        self.style.configure("Header.TLabel", padding=5, font=("Arial", 12, "bold"))
        self.style.configure("Error.TLabel", foreground="red", font=("Arial", 10, "italic"))

        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        # Variables pour stocker les résultats
        self.status_var = tk.StringVar(value="Chargement...")
        self.raw_total_var = tk.StringVar(value="--")
        self.counted_total_var = tk.StringVar(value="--")
        self.quota_var = tk.StringVar(value="--")
        self.remaining_days_var = tk.StringVar(value="--")
        self.remaining_hours_var = tk.StringVar(value="--")
        self.avg_needed_var = tk.StringVar(value="--")
        self.quota_90_var = tk.StringVar(value="--")
        self.remaining_hours_90_var = tk.StringVar(value="--")
        self.avg_needed_90_var = tk.StringVar(value="--")

        self.create_widgets()

        # Lancer le rafraîchissement des données après l'affichage de la fenêtre
        self.root.after(100, self.refresh_data)

    def create_widgets(self):
        # --- Section Stats Actuelles ---
        ttk.Label(self.main_frame, text="📈 Vos Statistiques (Mois en cours)", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(self.main_frame, text="Quota du mois :").grid(row=1, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.quota_var).grid(row=1, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Temps comptabilisé (6h-22h, Lun-Sam) :").grid(row=2, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.counted_total_var, font=("Arial", 10, "bold")).grid(row=2, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Temps total brut (24/7) :").grid(row=3, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.raw_total_var).grid(row=3, column=1, sticky="e")

        # --- Séparateur ---
        ttk.Separator(self.main_frame, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)

        # --- Section Objectif 100% ---
        ttk.Label(self.main_frame, text="🎯 Objectif 100%", style="Header.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(self.main_frame, text="Heures restantes :").grid(row=6, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.remaining_hours_var).grid(row=6, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Jours ouvrés restants :").grid(row=7, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.remaining_days_var).grid(row=7, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Moyenne/jours requise :").grid(row=8, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.avg_needed_var, font=("Arial", 10, "bold")).grid(row=8, column=1, sticky="e")

        # --- Séparateur ---
        ttk.Separator(self.main_frame, orient="horizontal").grid(row=9, column=0, columnspan=2, sticky="ew", pady=10)

        # --- Section Objectif 90% ---
        ttk.Label(self.main_frame, text="🚩 Objectif 90%", style="Header.TLabel").grid(row=10, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(self.main_frame, text="Quota (90%) :").grid(row=11, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.quota_90_var).grid(row=11, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Heures restantes (90%) :").grid(row=12, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.remaining_hours_90_var).grid(row=12, column=1, sticky="e")

        ttk.Label(self.main_frame, text="Moyenne/jours (90%) :").grid(row=13, column=0, sticky="w")
        ttk.Label(self.main_frame, textvariable=self.avg_needed_90_var).grid(row=13, column=1, sticky="e")

        # --- Status Bar ---
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, style="Error.TLabel")
        self.status_label.grid(row=14, column=0, columnspan=2, sticky="w", pady=10)

        # Configurer l'expansion des colonnes
        # Configurer l'expansion des colonnes
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

    def refresh_data(self):
        try:
            self.status_label.config(style="TLabel") # Style normal
            self.status_var.set("Authentification en cours...")
            self.root.update_idletasks() # Forcer la mise à jour de l'UI

            # Vérifier les identifiants
            if UID == "VOTRE_UID" or SECRET == "VOTRE_SECRET":
                raise ValueError("Veuillez configurer votre UID et SECRET en haut du script.")

            token = self.get_api_token()

            self.status_var.set("Récupération de l'ID utilisateur...")
            self.root.update_idletasks()
            user_id = self.get_user_id(token)

            # Définir le fuseau horaire et les dates
            local_tz = ZoneInfo(LOCAL_TZ_NAME)
            utc_tz = ZoneInfo("UTC")
            now_local = datetime.now(local_tz)

            start_of_month_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # L'API 42 utilise des plages inclusives/exclusives étranges.
            # Prenons le premier jour du mois prochain pour la fin.
            next_month = (start_of_month_local + timedelta(days=32)).replace(day=1)
            end_of_month_utc = next_month.astimezone(utc_tz) # Fin = 1er du mois prochain UTC
            start_of_month_utc = start_of_month_local.astimezone(utc_tz)

            self.status_var.set("Récupération des sessions (peut prendre du temps)...")
            self.root.update_idletasks()
            locations = self.get_locations(token, user_id, start_of_month_utc, end_of_month_utc)

            self.status_var.set("Calcul des heures...")
            self.root.update_idletasks()
            raw_hours, counted_hours = self.calculate_hours(locations, local_tz)

            self.status_var.set("Calcul des objectifs...")
            self.root.update_idletasks()
            stats = self.get_quota_stats(counted_hours, now_local)

            # Mettre à jour l'interface graphique
            self.raw_total_var.set(f"{raw_hours:.2f} h")
            self.counted_total_var.set(f"{counted_hours:.2f} h")
            self.quota_var.set(f"{stats['quota']} h")
            self.remaining_days_var.set(f"{stats['remaining_open_days']} jours")

            self.remaining_hours_var.set(f"{stats['hours_remaining']:.2f} h")
            self.avg_needed_var.set(f"{stats['avg_per_day']:.2f} h / jours")

            self.quota_90_var.set(f"{stats['quota_90']:.2f} h")
            self.remaining_hours_90_var.set(f"{stats['hours_remaining_90']:.2f} h")
            self.avg_needed_90_var.set(f"{stats['avg_per_day_90']:.2f} h / jours")

            if stats['avg_per_day'] > 16: # Seuil d'alerte
                self.avg_needed_var.set(f"{stats['avg_per_day']:.2f} h / jours (Impossible ?)")
            elif stats['avg_per_day'] < 0:
                 self.avg_needed_var.set("Objectif atteint ! 🎉")

            self.status_var.set("Terminé.")

        except Exception as e:
            self.status_label.config(style="Error.TLabel") # Style erreur
            self.status_var.set(f"Erreur : {e}")
            messagebox.showerror("Erreur", str(e))

    def get_api_token(self):
        payload = {
            'grant_type': 'client_credentials',
            'client_id': UID,
            'client_secret': SECRET
        }
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()['access_token']

    def get_user_id(self, token):
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f"{API_URL}/v2/users/{LOGIN_42}", headers=headers)
        response.raise_for_status()
        return response.json()['id']

    def get_locations(self, token, user_id, start_date, end_date):
        locations = []
        page = 1
        headers = {'Authorization': f'Bearer {token}'}

        while True:
            params = {
                'page[size]': 100,
                'page[number]': page,
                'range[begin_at]': f'{start_date.isoformat()},{end_date.isoformat()}',
                'sort': 'begin_at'
            }
            try:
                response = requests.get(
                    f"{API_URL}/v2/users/{user_id}/locations",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    break  # Plus de données

                locations.extend(data)

                if len(data) < 100:
                    break  # C'était la dernière page

                page += 1
            except requests.RequestException as e:
                raise Exception(f"Erreur API (page {page}): {e.response.text}")

        return locations

    def calculate_hours(self, locations, local_tz):
        total_raw_seconds = 0
        total_counted_seconds = 0
        utc_tz = ZoneInfo('UTC')
        now_utc = datetime.now(utc_tz)

        # Heures de début et de fin (en heure locale)
        valid_start_time = time(6, 0, 0)
        valid_end_time = time(22, 0, 0)

        for session in locations:
            try:
                start_utc = datetime.fromisoformat(session['begin_at'].replace('Z', '+00:00'))

                if session['end_at']:
                    end_utc = datetime.fromisoformat(session['end_at'].replace('Z', '+00:00'))
                else:
                    end_utc = now_utc # Toujours connecté

                # 1. Calcul du temps total brut
                total_raw_seconds += (end_utc - start_utc).total_seconds()

                # 2. Calcul du temps comptabilisé (plus complexe)
                local_start = start_utc.astimezone(local_tz)
                local_end = end_utc.astimezone(local_tz)

                # Itérer jour par jour pour les sessions qui durent plusieurs jours
                current_time = local_start
                while current_time < local_end:
                    # Vérifier si le jour est valide (0=Lundi, 5=Samedi, 6=Dimanche)
                    if current_time.weekday() < 6:
                        # Définir la fenêtre de temps valide pour CE jour
                        day_allowed_start = current_time.replace(
                            hour=valid_start_time.hour, minute=valid_start_time.minute, second=0, microsecond=0)
                        day_allowed_end = current_time.replace(
                            hour=valid_end_time.hour, minute=valid_end_time.minute, second=0, microsecond=0)

                        # Calculer le chevauchement (overlap)
                        overlap_start = max(current_time, day_allowed_start)
                        overlap_end = min(local_end, day_allowed_end)

                        # Ajouter le temps si le chevauchement est valide
                        if overlap_end > overlap_start:
                            total_counted_seconds += (overlap_end - overlap_start).total_seconds()

                    # Passer au début du jour suivant
                    current_time = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

            except Exception as e:
                print(f"Erreur en traitant la session {session.get('id')}: {e}")

        return (total_raw_seconds / 3600, total_counted_seconds / 3600)

    def get_quota_stats(self, counted_hours, now_local):
        # 1. Déterminer le quota
        days_in_month = calendar.monthrange(now_local.year, now_local.month)[1]

        if now_local.month == 2:
            quota = 135
        elif days_in_month == 30:
            quota = 150
        else: # 31 jours
            quota = 155

        # 2. Calculer les jours ouvrés restants (à partir de DEMAIN)
        remaining_open_days = 0
        day_to_check = (now_local + timedelta(days=1)).replace(hour=0, minute=0)
        end_of_month = now_local.replace(day=days_in_month, hour=23, minute=59)

        while day_to_check <= end_of_month:
            # 0=Lundi, 5=Samedi, 6=Dimanche
            if day_to_check.weekday() < 6:
                remaining_open_days += 1
            day_to_check += timedelta(days=1)

        # 3. Calculer les stats
        hours_remaining = quota - counted_hours

        if remaining_open_days > 0:
            avg_per_day = hours_remaining / remaining_open_days
        else:
            avg_per_day = 0 if hours_remaining <= 0 else float('inf') # Infini si on a pas fini

        # 4. Stats pour 90%
        quota_90 = quota * 0.90
        hours_remaining_90 = quota_90 - counted_hours

        if remaining_open_days > 0:
            avg_per_day_90 = hours_remaining_90 / remaining_open_days
        else:
            avg_per_day_90 = 0 if hours_remaining_90 <= 0 else float('inf')

        return {
            "quota": quota,
            "hours_remaining": hours_remaining,
            "remaining_open_days": remaining_open_days,
            "avg_per_day": avg_per_day,
            "quota_90": quota_90,
            "hours_remaining_90": hours_remaining_90,
            "avg_per_day_90": avg_per_day_90
        }

if __name__ == "__main__":
    # Vérifier les dépendances
    try:
        import requests
        from zoneinfo import ZoneInfo
    except ImportError:
        print("Erreur : La bibliothèque 'requests' ou 'zoneinfo' (Python 3.9+) n'est pas installée.")
        print("Veuillez installer requests : pip install requests")
        print("Assurez-vous d'utiliser Python 3.9 ou plus récent pour 'zoneinfo'.")
        exit(1)

    # Vérifier les identifiants
    if UID == "VOTRE_UID" or SECRET == "VOTRE_SECRET":
        print("############################################################")
        print(" ERREUR DE CONFIGURATION")
        print(" Vous devez modifier ce script et insérer votre UID et")
        print(" votre SECRET aux lignes 12 et 13.")
        print(" NE PARTAGEZ JAMAIS CES IDENTIFIANTS.")
        print("############################################################")
        # On ouvre quand même la fenêtre pour afficher l'erreur

    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()
