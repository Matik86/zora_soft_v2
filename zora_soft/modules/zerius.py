import random
import asyncio
from eth_abi import encode
from loguru import logger

from utils.utils import gas_checker
from modules.client import Client
from settings.settings import DST_CHAIN_ZERIUS_NFT, DST_CHAIN_ZERIUS_REFUEL
from modules.config import (ZERIUS_CONTRACT_PER_CHAINS, ZERIUS_ABI,
                            ZERO_ADDRESS, LAYERZERO_NETWORKS_DATA,
                            LAYERZERO_WRAPED_NETWORKS)


class Zerius():

    def __init__(self, client: Client):
        self.client = client
        self.chain_from_id = next((k for k, v in LAYERZERO_NETWORKS_DATA.items() if v[0] == 'Zora'), None)

    async def get_nft_id(self, contract):
        balance_nft = await contract.functions.balanceOf(self.client.address).call()
        nft_ids = []
        for i in range(balance_nft):
            nft_ids.append(await contract.functions.tokenOfOwnerByIndex(self.client.address, i).call())
        if nft_ids:
            return nft_ids[-1]
        return False

    async def get_estimate_send_fee(self, contract, adapter_params, dst_chain_id, nft_id):

        estimate_send_fee = (await contract.functions.estimateSendFee(
            dst_chain_id,
            self.client.address,
            nft_id,
            False,
            adapter_params
        ).call())[0]

        return estimate_send_fee

    @gas_checker
    async def mint(self):
        onft_contract = self.client.get_contract(ZERIUS_CONTRACT_PER_CHAINS[self.chain_from_id]['ONFT'],
                                                 ZERIUS_ABI['ONFT'])

        mint_price = await onft_contract.functions.mintFee().call()

        logger.info(f'Mint Zerius NFT on Zora '
                    f'Mint Price: {(mint_price / 10 ** 18):.5f} ETH')

        tx_params = await self.client.prepare_transaction(value=mint_price)

        transaction = await onft_contract.functions.mint(
            '0x000000a679C2FB345dDEfbaE3c42beE92c0Fb7A5'
        ).build_transaction(tx_params)

        tx_hash = await self.client.send_tx(transaction)

        return await self.client.verif_tx(tx_hash)


    @gas_checker
    async def bridge(self):
        dst_chain = random.choice(DST_CHAIN_ZERIUS_NFT)

        onft_contract = self.client.get_contract(ZERIUS_CONTRACT_PER_CHAINS[self.chain_from_id]['ONFT'],
                                                 ZERIUS_ABI['ONFT'])

        dst_chain_name, dst_chain_id, _, _ = LAYERZERO_NETWORKS_DATA[dst_chain]

        nft_id = await self.get_nft_id(onft_contract)

        if not nft_id:
            new_client = await self.client.restart_client()
            await Zerius(new_client).mint()
            nft_id = await self.get_nft_id(onft_contract)
            await asyncio.sleep(random.randint(5, 10))

        logger.info(f'Bridge Zerius NFT from Zora to {dst_chain_name}. ID: {nft_id}')

        version, gas_limit = 1, await onft_contract.functions.minDstGasLookup(dst_chain_id, 1).call()

        adapter_params = encode(["uint16", "uint256"],
                                [version, gas_limit])

        adapter_params = self.client.w3.to_hex(adapter_params[30:])

        base_bridge_fee = await onft_contract.functions.bridgeFee().call()
        estimate_send_fee = await self.get_estimate_send_fee(onft_contract, adapter_params, dst_chain_id, nft_id)

        tx_params = await self.client.prepare_transaction(value=estimate_send_fee + base_bridge_fee)

        transaction = await onft_contract.functions.sendFrom(
            self.client.address,
            dst_chain_id,
            self.client.address,
            nft_id,
            self.client.address,
            ZERO_ADDRESS,
            adapter_params
        ).build_transaction(tx_params)

        tx_hash = await self.client.send_tx(transaction)

        return await self.client.verif_tx(tx_hash)

    @gas_checker
    async def refuel(self):
        formatted_zerius_refuel = DST_CHAIN_ZERIUS_REFUEL
        dst_data = random.choice(list(formatted_zerius_refuel.items()))

        dst_chain_name, dst_chain_id, dst_native_name, dst_native_api_name = LAYERZERO_NETWORKS_DATA[dst_data[0]]
        dst_amount = self.client.round_amount(*dst_data[1])

        refuel_info = f'{dst_amount} {dst_native_name} to {dst_chain_name} from Zora'
        logger.info(f'Refuel on Zerius: {refuel_info}')

        l2pass_contracts = ZERIUS_CONTRACT_PER_CHAINS[self.chain_from_id]
        refuel_contract = self.client.get_contract(l2pass_contracts['refuel'], ZERIUS_ABI['refuel'])

        dst_native_gas_amount = int(dst_amount * 10 ** 18)
        dst_contract_address = ZERIUS_CONTRACT_PER_CHAINS[LAYERZERO_WRAPED_NETWORKS[dst_data[0]]]['refuel']

        gas_limit = await refuel_contract.functions.minDstGasLookup(dst_chain_id, 0).call()

        if gas_limit == 0:
            logger.error('This refuel path is not active!')

        adapter_params = encode(["uint16", "uint64", "uint256"],
                                [2, gas_limit, dst_native_gas_amount])

        adapter_params = self.client.w3.to_hex(adapter_params[30:]) + self.client.address[2:].lower()

        try:
            estimate_send_fee = (await refuel_contract.functions.estimateSendFee(
                dst_chain_id,
                dst_contract_address,
                adapter_params
            ).call())[0]

            tx_params = await self.client.prepare_transaction(value=estimate_send_fee)

            transaction = await refuel_contract.functions.refuel(
                dst_chain_id,
                dst_contract_address,
                adapter_params
            ).build_transaction(tx_params)

            tx_hash = await self.client.send_tx(transaction)

            return await self.client.verif_tx(tx_hash)

        except Exception as error:
            logger.error(f'Error during the refuel!. Error: {error}')
