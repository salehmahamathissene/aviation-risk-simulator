def compute_costs(delays, cancellations):
    cost_per_min_delay = 75  # USD
    cost_per_cancellation = 5000

    total_delay_cost = sum(delays) * cost_per_min_delay
    total_cancel_cost = cancellations * cost_per_cancellation

    return {
        "delay_cost": total_delay_cost,
        "cancel_cost": total_cancel_cost,
        "total_cost": total_delay_cost + total_cancel_cost
    }
