from app.disruptions.disruption_engine import generate_disruption
from app.passenger.passenger_engine import passenger_impact


def run_simulation(runs=1000):

    total_cost = 0

    for i in range(runs):

        disruption = generate_disruption()

        impact = passenger_impact(disruption["delay_minutes"])

        total_cost += impact["compensation_cost"]

    average_cost = total_cost / runs

    return {
        "runs": runs,
        "average_cost": average_cost
    }
