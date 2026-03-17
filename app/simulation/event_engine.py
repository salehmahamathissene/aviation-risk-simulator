import heapq


class EventEngine:

    def __init__(self):

        self.time = 0
        self.events = []

    def schedule(self, time, event):

        heapq.heappush(self.events, (time, event))

    def run(self):

        while self.events:

            time, event = heapq.heappop(self.events)

            self.time = time

            event.process(self)
