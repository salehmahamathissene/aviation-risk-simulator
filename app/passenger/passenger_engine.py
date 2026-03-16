def passenger_impact(delay):

    passengers = 180

    if delay < 30:
        missed_connections = 5
    elif delay < 60:
        missed_connections = 20
    else:
        missed_connections = 50

    compensation_cost = missed_connections * 250

    return {
        "passengers": passengers,
        "missed_connections": missed_connections,
        "compensation_cost": compensation_cost
    }
