from Models.Block import Block as BaseBlock


class Block(BaseBlock):
    """
    Defines the Ethereum Block model.

    Adds optional energy + CO2 metrics (Bitcoin-style accounting).
    """

    def __init__(
        self,
        depth: int = 0,
        id: int = 0,
        previous: int = -1,
        timestamp: float = 0,
        miner=None,
        transactions=None,
        size: float = 1.0,
        uncles=None,
        gaslimit: int = 8000000,
        usedgas: int = 0,
        energy_kwh: float = 0.0,
        co2_kg: float = 0.0,
        mining_duration_s: float = 0.0,
    ):
        if transactions is None:
            transactions = []
        if uncles is None:
            uncles = []

        super().__init__(depth, id, previous, timestamp, miner, transactions, size)
        self.uncles = uncles
        self.gaslimit = gaslimit
        self.usedgas = usedgas

        # Energy/CO2 metrics (optional)
        self.energy_kwh = energy_kwh
        self.co2_kg = co2_kg
        self.mining_duration_s = mining_duration_s
