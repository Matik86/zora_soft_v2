import random
import asyncio
from eth_abi import abi
from loguru import logger

from modules.client import Client
from utils.utils import gas_checker
from settings.settings import DST_CHAIN_MERKLY_REFUEL
from modules.config import (
    MERKLY_ABI,
    MERKLY_CONTRACTS_PER_CHAINS,
    LAYERZERO_NETWORKS_DATA,
    LAYERZERO_WRAPED_NETWORKS
)


class Merkly():

    def __init__(self, client: Client):
        self.client = client
        self.chain_from_id = next((k for k, v in LAYERZERO_NETWORKS_DATA.items() if v[0] == 'Zora'), None)

    @gas_checker
    async def refuel(self):
        dst_data = random.choice(list(DST_CHAIN_MERKLY_REFUEL.items()))

        dst_chain_name, dst_chain_id, dst_native_name, dst_native_api_name = LAYERZERO_NETWORKS_DATA[dst_data[0]]
        dst_amount = self.client.round_amount(*dst_data[1])

        refuel_info = f'{dst_amount} {dst_native_name} to {dst_chain_name} from Zora'
        logger.info(f'Refuel on Merkly: {refuel_info}')

        merkly_contracts = MERKLY_CONTRACTS_PER_CHAINS[self.chain_from_id]

        refuel_contract = self.client.get_contract(merkly_contracts['refuel'], MERKLY_ABI['refuel'])

        dst_native_gas_amount = int(dst_amount * 10 ** 18)
        dst_contract_address = MERKLY_CONTRACTS_PER_CHAINS[LAYERZERO_WRAPED_NETWORKS[dst_data[0]]]['refuel']

        gas_limit = await refuel_contract.functions.minDstGasLookup(dst_chain_id, 0).call()

        if gas_limit == 0:
            logger.error('This refuel path is not active!')

        adapter_params = abi.encode(["uint16", "uint64", "uint256"],
                                    [2, gas_limit, dst_native_gas_amount])

        adapter_params = self.client.w3.to_hex(adapter_params[30:]) + self.client.address[2:].lower()

        try:
            estimate_send_fee = (await refuel_contract.functions.estimateSendFee(
                dst_chain_id,
                dst_contract_address,
                adapter_params
            ).call())[0]

            transaction = await refuel_contract.functions.bridgeGas(
                dst_chain_id,
                self.client.address,
                adapter_params
            ).build_transaction(await self.client.prepare_transaction(value=estimate_send_fee))

            tx_hash = await self.client.send_tx(transaction)

            return await self.client.verif_tx(tx_hash)

        except Exception as error:
            logger.error(f'Error during the refuel!. Error: {error}')
