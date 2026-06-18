class InputsConfig:

    """ Select the model to be simulated.
    0 : The base model
    1 : Bitcoin model (PoW)
    2 : Ethereum model
    3 : PoCol model (nonce-space partitioning; PoW-comparable)
    4 : AppendableBlock model (optional / legacy)
    """
    model = 3

    LightTxPoolMax = 200000  # cap

    GridEF_kgCO2e_per_kWh = 0.445

    # ---------------- Energy + CO2 instrumentation ----------------
    EnableEnergy = True

    # Interpret Node.hashPower as a SHARE/WEIGHT (e.g., 50/20/30), not absolute H/s
    HashPowerIsShare = True

    # Absolute network hashrate (hashes/second). Example: 141 TH/s = 141e12 H/s
    # Choose any value; energy scales linearly with this.
    NetworkHashRate_Hps = 141e12

    # Miner efficiency in Joules per terahash (J/TH).
    # Example hardware spec: Antminer S19 XP ~ 21.5 J/TH (Bitmain).
    MinerEfficiency_J_per_TH = 21.5

    # Grid emission factor (kg CO2e per kWh). Set based on your region/year.
    # Official sources: UK Gov GHG conversion factors, US EPA eGRID.
    # GridEF_kgCO2e_per_kWh = 0.0

    # --- Aliases required by Ethereum energy patch ---

    # kgCO2e/kWh -> gCO2/kWh
    GRID_GCO2_PER_KWH = GridEF_kgCO2e_per_kWh * 1000

    # Use your existing hashrate + efficiency to compute W = H/s * J/hash
    TOTAL_HASHRATE_HS = NetworkHashRate_Hps
    J_PER_HASH = MinerEfficiency_J_per_TH / 1e12   # because 1 TH = 1e12 hashes


    UseTxDistFit = False



    ''' Input configurations for the base model '''
    if model == 0:

        ''' Block Parameters '''
        Binterval = 600
        Bsize = 1.0
        Bdelay = 0.42
        Breward = 12.5

        ''' Transaction Parameters '''
        hasTrans = True
        Ttechnique = "Light"
        Tn = 10
        Tdelay = 5.1
        Tfee = 0.000062
        Tsize = 0.000546

        ''' Node Parameters '''
        Nn = 3
        NODES = []
        from Models.Node import Node
        NODES = [Node(id=0), Node(id=1)]

        ''' Simulation Parameters '''
        simTime = 1000
        Runs = 2

    ''' Input configurations for Bitcoin model '''
    if model == 1:

        ''' Block Parameters '''
        Binterval = 600
        Bsize = 1.0
        Bdelay = 0.42
        Breward = 12.5

        ''' Transaction Parameters '''
        hasTrans = True
        Ttechnique = "Light"
        Tn = 3
        Tdelay = 5.1
        Tfee = 0.000062
        Tsize = 0.000546

        ''' Node Parameters '''
        Nn = 1000
        # NODES = []
        from Models.Bitcoin.Node import Node
        # NODES = [Node(id=0, hashPower=33),
        #          Node(id=1, hashPower=33),
        #          Node(id=2, hashPower=33)]

        NODES = []
        for i in range(Nn):
            NODES.append(Node(id=i, hashPower=1))


        ''' Simulation Parameters '''
        simTime = 10000
        Runs = 1

    ''' Input configurations for Ethereum model '''
    if model == 2:

        ''' Block Parameters '''
        Binterval = 12.42
        Bsize = 1.0
        Blimit = 8000000
        Bdelay = 6
        Breward = 2

        ''' Transaction Parameters '''
        hasTrans = True
        Ttechnique = "Light"
        Tn = 20
        Tdelay = 3
        Tsize = 0.000546

        ''' Uncles Parameters '''
        hasUncles = True
        Buncles = 2
        Ugenerations = 7
        Ureward = 0
        UIreward = Breward / 32

        ''' Node Parameters '''
        Nn = 1000
        # NODES = []
        from Models.Ethereum.Node import Node
        # NODES = [Node(id=0, hashPower=33),
        #          Node(id=1, hashPower=33),
        #          Node(id=2, hashPower=33)]

        NODES = []
        for i in range(Nn):
            NODES.append(Node(id=i, hashPower=1))

        POWER_WATTS = {i: 2500 for i in range(Nn)}  # 2500W per miner (example)
        GRID_GCO2_PER_KWH = GridEF_kgCO2e_per_kWh * 1000


        ''' Simulation Parameters '''
        simTime = 10000
        Runs = 1

    ''' Input configurations for PoCol model '''
    if model == 3:

        # Keep Bitcoin-like block/tx defaults for apples-to-apples comparison
        # (Bitcoin targets ~10 minutes per block.) :contentReference[oaicite:2]{index=2}
        ''' Block Parameters '''
        Binterval = 600
        Bsize = 1.0
        Bdelay = 0.42
        Breward = 12.5

        ''' Transaction Parameters '''
        hasTrans = True
        Ttechnique = "Light"
        Tn = 10
        Tdelay = 5.1
        Tfee = 0.000062
        Tsize = 0.000546

        # Binterval = 600
        PoCol_AutoCalibrate = True
        # PoCol_NonceSpace = 3000
        

        ''' PoCol Parameters (new) '''
        # Nonce-space size per round. If too small, blocks will be found too fast.
        PoCol_NonceSpace = 3000

        # How nonce space is partitioned among miners: "equal" (default), "weighted" (future)
        PoCol_AssignStrategy = "equal"

        # Extra delay for miners that do NOT contain the solution nonce (prevents them “winning”)
        # PoCol_Backoff = Binterval * 5
        PoCol_Backoff = max(5 * Bdelay, 1.0)

        # Optional scaling factor (difficulty-like). If you later apply it in PoCol.Consensus:
        # time = attempts * PoCol_DifficultyFactor / hashPower
        PoCol_DifficultyFactor = 1.0

        ''' Node Parameters '''
        Nn = 500
        # NODES = []
        from Models.PoCol.Node import Node
        # NODES = [Node(id=0, hashPower=33),
        #          Node(id=1, hashPower=33),
        #          Node(id=2, hashPower=33)]
        
        NODES = []
        for i in range(Nn):
            NODES.append(Node(id=i, hashPower=1))

        ''' Simulation Parameters '''
        simTime = 10000
        Runs = 1

    ''' Input configurations for AppendableBlock model (moved to model == 4) '''
    if model == 4:

        ''' Transaction Parameters '''
        hasTrans = True
        Ttechnique = "Full"
        Tn = 10
        txListSize = 100

        ''' Node Parameters '''
        Dn = 10
        Gn = 2
        Nn = Gn + (Gn * Dn)
        NODES = []
        GATEWAYIDS = [chr(x + 97) for x in range(Gn)]
        from Models.AppendableBlock.Node import Node

        for i in GATEWAYIDS:
            otherGatewayIds = GATEWAYIDS.copy()
            otherGatewayIds.remove(i)
            NODES.append(Node(i, "g", otherGatewayIds))

        deviceNodeId = 1
        for i in GATEWAYIDS:
            for j in range(Dn):
                NODES.append(Node(deviceNodeId, "d", i))
                deviceNodeId += 1

        ''' Simulation Parameters '''
        propTxDelay = 0.000690847927
        propTxListDelay = 0.00864894
        insertTxDelay = 0.000010367235
        simTime = 500
        Runs = 5

        ''' Verification '''
        VerifyImplemetation = True
        maxTxListSize = 0
