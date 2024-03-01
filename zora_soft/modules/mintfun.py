import random
import asyncio
from web3 import Web3
from loguru import logger

from utils.utils import gas_checker
from modules.client import Client
from modules.config import MINTFUN_CONTRACTS, MINTFUN_ABI


class MintFun:
    
    def __init__(self, client: Client):
        self.client = client
        self.address = self.client.address

    @gas_checker
    async def mint(self):

        contract_name = random.choice(list(MINTFUN_CONTRACTS.keys()))
        contract_address = Web3.to_checksum_address(MINTFUN_CONTRACTS[contract_name]['contract'])
        quantity = MINTFUN_CONTRACTS[contract_name]['quantity']

        logger.info(f'Mint {contract_name} on MintFun')

        contract = self.client.get_contract(contract_address,
                                            MINTFUN_ABI)
        
        try:
            tx_params = await self.client.prepare_transaction()

            transaction = await contract.functions.mint(
                quantity,
            ).build_transaction(tx_params)

            tx_hash = await self.client.send_tx(transaction)

            return await self.client.verif_tx(tx_hash)

        except Exception as err:
            logger.error(f'{self.address} | {err}: {contract_name}')
