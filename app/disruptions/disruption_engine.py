import random

DISRUPTION_TYPES = [
    "weather_delay",
    "technical_issue",
    "crew_unavailable",
    "airport_congestion"
]


def generate_disruption():
    disruption = random.choice(DISRUPTION_TYPES)

    delay = random.choice([15, 30, 60, 120])

    return {
        "type": disruption,
        "delay_minutes": delay
    }
