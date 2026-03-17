import numpy as np


def weather_delay():

    return int(np.random.lognormal(mean=3.2, sigma=0.7))


def technical_delay():

    return int(np.random.lognormal(mean=4.0, sigma=0.6))


def crew_delay():

    return int(np.random.lognormal(mean=2.8, sigma=0.5))
