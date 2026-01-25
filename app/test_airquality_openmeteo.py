import requests

LAT = 43.6045
LON = 1.4440

def main():
    url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LAT}&longitude={LON}"
        "&hourly=pm2_5"
        "&past_days=7"
        "&forecast_days=1"
        "&timezone=Europe%2FParis"
    )

    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    pm25 = data["hourly"]["pm2_5"]

    reference = pm25[:48]
    current = pm25[-48:]

    payload = {
        "reference": {"pm25": reference},
        "current": {"pm25": current},
        "alpha": 0.05
    }

    res = requests.post("http://localhost:8000/drift-data", json=payload)
    print("Status =", res.status_code)
    print(res.json())

if __name__ == "__main__":
    main()