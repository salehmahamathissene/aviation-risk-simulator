from app.reliability.weibull import WeibullFailure


class FailureProfiles:

    def __init__(self):

        self.systems = {
            "flight_control": WeibullFailure(beta=1.5, eta=5000),
            "actuation": WeibullFailure(beta=1.8, eta=4000),
            "hydraulics": WeibullFailure(beta=2.2, eta=3000),
            "avionics": WeibullFailure(beta=1.2, eta=6000)
        }

    def sample_failure(self, flight_time):

        failures = []

        for name, model in self.systems.items():

            prob = model.failure_probability(flight_time)

            if prob > 0 and prob > 0.01:  # threshold
                failures.append((name, prob))

        return failures
