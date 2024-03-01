MODULES_PROBABILITY = {
    # 'CreateNFT': 0.01,
    'L2pass': 0.12,
    'Merkly': 0.08,
    'MintZora': 0.02,
    'MintFun': 0.7,
    'Zerius': 0.08,
}

L2PASS_PROBABILITY = {
    'refuel': 0.5,
    'mint': 0.1,
    'bridge': 0.1,
    'gas_station': 0.3,
}

DST_CHAIN_L2PASS_NFT = [2, 7, 9, 11, 14, 15, 17, 18, 20, 21, 26, 27, 28, 29, 33, 41, 44]  # Входящая сеть для L2PASS Mint NFT

DST_CHAIN_L2PASS_REFUEL = {
    33: (0.001, 0.01),  # Chain ID: (минимум, максимум) в нативном токене входящей сети (кол-во)
    7: (0.00001, 0.00002),
}

L2PASS_GAS_STATION_DATA = [
    # Gas Station на L2Pass https://l2pass.com/gas-station. Указываете в списках сеть и сумму к refuel
    [7, 0.000001],
    [33, 0.00001]
]

DST_CHAIN_L2TELEGRAPH = [2, 7, 9, 11, 14, 15, 17, 18, 20, 21, 26, 27, 28, 29, 33, 41, 44]

DST_CHAIN_ZERIUS_NFT = [2, 7, 9, 11, 14, 15, 17, 18, 20, 21, 26, 27, 28, 29, 33, 41,
                        44]  # Входящая сеть для Zerius Mint NFT

DST_CHAIN_ZERIUS_REFUEL = {
    7: (0.000001, 0.000005), # Chain ID: (минимум, максимум) в нативном токене dst сети (кол-во)
    33: (0.0001, 0.001),
    18: (0.01, 0.02),
}

DST_CHAIN_MERKLY_REFUEL = {
    33: (0.001, 0.001),  # Chain ID: (минимум, максимум) в нативном токене входящей сети (кол-во)
    7: (0.00001, 0.00002),
}
