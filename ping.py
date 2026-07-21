class Ping:
    def __init__(self, ticker, name, target_price, direction="below"):
        self.ticker = ticker
        self.name = name
        self.target_price = target_price
        self.direction = direction
        self.current_price = None
        self._triggered = False
    
    def update(self, price):
        self.current_price = price
        if price is None:
            return False
        
        if self.direction == "below":
            triggered = price <= self.target_price
        else:
            triggered = price >= self.target_price
        
        if triggered and not self._triggered:
            self._triggered = True
            return True
        
        if not triggered:
            self._triggered = False
        
        return False
    
    @property
    def is_triggered(self):
        return self._triggered
    
    def get_alert(self):
        d = "УПАЛ ДО" if self.direction == "below" else "ВЫРОС ДО"
        return f"[!!!] {self.name} ({self.ticker}) {d} {self.target_price:.2f} | Текущая: {self.current_price:.2f}"