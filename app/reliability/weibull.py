import numpy as np


class WeibullFailure:

    def __init__(self, beta, eta):
        """
        beta: shape parameter
        eta: scale parameter (life characteristic)
        """
        self.beta = beta
        self.eta = eta

    def failure_probability(self, t):
        """
        CDF of Weibull → probability of failure by time t
        """
        return 1 - np.exp(-(t / self.eta) ** self.beta)

    def sample_time_to_failure(self):
        """
        Generate time to failure
        """
        return np.random.weibull(self.beta) * self.eta
