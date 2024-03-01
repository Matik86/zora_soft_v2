import random
import asyncio
from web3 import Web3
from loguru import logger

from utils.utils import gas_checker
from modules.client import Client
from modules.config import MINT_ZORA_CONTRACTS, MINT_ZORA_ABI, ZERO_ADDRESS


class MintZora:

    def __init__(self, client: Client):
        self.client = client
        self.address = self.client.address
        self.minter_address = Web3.to_checksum_address('0x04e2516a2c207e84a1839755675dfd8ef6302f0a')

    @gas_checker
    async def mint(self):

        contract_name = random.choice(list(MINT_ZORA_CONTRACTS.keys()))
        contract_address = Web3.to_checksum_address(MINT_ZORA_CONTRACTS[contract_name]['contract'])

        logger.info(f'Mint {contract_name} on Zora.co')

        contract = self.client.get_contract(contract_address,MINT_ZORA_ABI)
        mint_price = await contract.functions.mintFee().call()

        try:
            tx_params = await self.client.prepare_transaction(value=mint_price)

            transaction = await contract.functions.mintWithRewards(
                self.minter_address,
                1,
                1,
                '0x000000000000000000000000' + self.address[2:],
                ZERO_ADDRESS,
            ).build_transaction(tx_params)

            tx_hash = await self.client.send_tx(transaction)

            return await self.client.verif_tx(tx_hash)

        except Exception as err:
            logger.error(f'{err}: {contract_name}')
