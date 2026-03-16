class Airport:
    def __init__(self, code, name):
        self.code = code
        self.name = name

    def info(self):
        return {
            "code": self.code,
            "name": self.name
        }
