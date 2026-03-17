# app/data/load_openflights.py

import csv

def load_airports(path):

    airports = {}

    with open(path) as f:

        reader = csv.reader(f)

        for row in reader:

            airport_id = row[0]
            name = row[1]
            lat = float(row[6])
            lon = float(row[7])

            airports[airport_id] = {
                "name": name,
                "lat": lat,
                "lon": lon
            }

    return airports
