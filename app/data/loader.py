import pandas as pd


def load_flights(path="data/flights_sample.csv"):

    df = pd.read_csv(path)

    return df.to_dict(orient="records")
