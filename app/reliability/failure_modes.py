import random


class FailureMode:

    def __init__(self, name, failure_rate, delay_impact):

        self.name = name
        self.failure_rate = failure_rate  # probability per flight
        self.delay_impact = delay_impact  # minutes


class FailureLibrary:

    def __init__(self):

        self.modes = [
            FailureMode("flight_control_failure", 0.002, 180),
            FailureMode("actuation_system_fault", 0.003, 120),
            FailureMode("hydraulic_issue", 0.004, 90),
            FailureMode("avionics_fault", 0.005, 60)
        ]

    def sample_failure(self):

        for mode in self.modes:

            if random.random() < mode.failure_rate:
                return mode

        return None
