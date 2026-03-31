# DublinBikes

UCD COMP30830 Group Project (Group 8): a web application that displays Dublin Bikes station availability with weather context to support commuter decisions.

## What this repository provides
- **Bike data ingestion (JCDecaux)** → stores static station metadata and dynamic availability records in **MySQL**.
- **Weather data ingestion (OpenWeather)** → stores time-series weather snapshots (including precipitation probability) in **MySQL**.
- A shared codebase for the group’s final deliverables (code + schema + ingestion pipelines).

---

## Quick start (local)

### 1) Create and activate a Python virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure database connection (local-only)
Create a file **dbinfo.py** in the project root (**do NOT commit**; it is ignored by `.gitignore`):

```python
# dbinfo.py (LOCAL ONLY - DO NOT COMMIT)
DB_USER = "root"
DB_PASS = "YOUR_MYSQL_PASSWORD"
DB_URI  = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "dublin_bikes_project"
```

### 3) Set OpenWeather API key (local-only)
```bash
export OWM_API_KEY="YOUR_OPENWEATHER_KEY"
```

---

## Weather ingestion (OpenWeather → MySQL)

### Sanity check: insert one row
Runs a single API call and inserts one weather snapshot into the `weather` table:
```bash
python weather_one_shot.py
```

### Scheduled ingestion (recommended)
Runs continuous ingestion and inserts snapshots into the `weather` table at a fixed interval:
```bash
python weather_scraper.py
```

Run in background and log output:
```bash
OWM_API_KEY="YOUR_OPENWEATHER_KEY" nohup python weather_scraper.py > weather.log 2>&1 &
tail -f weather.log
```

**Design note (for assessment):** weather is stored as **time-series snapshots every 30 minutes** (current conditions + `precip_prob` derived from forecast `pop`) to balance data quality with API request limits while meeting the requirement to update at least hourly.

---

## Security and repo hygiene
- Secrets (e.g., `dbinfo.py`, `.env`, API keys) are **not committed**.
- Local virtual environments and logs are ignored via `.gitignore`.
