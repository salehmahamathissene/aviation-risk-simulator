class Airport:

    def __init__(self, code, capacity):

        self.code = code
        self.capacity = capacity
        self.current_traffic = 0

    def congestion_factor(self):

        if self.current_traffic > self.capacity:
            return 2.0

        return 1.0
