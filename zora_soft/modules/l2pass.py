import random
import asyncio
from loguru import logger

from eth_abi import encode
from modules.client import Client
from utils.utils import gas_checker
from settings.settings import DST_CHAIN_L2PASS_REFUEL, DST_CHAIN_L2PASS_NFT, L2PASS_GAS_STATION_DATA
from modules.config import (
    L2PASS_CONTRACTS_PER_CHAINS, L2PASS_ABI,
    LAYERZERO_NETWORKS_DATA, ZERO_ADDRESS, LAYERZERO_WRAPED_NETWORKS
)


class L2Pass():

    def __init__(self, client: Client):
        self.client = client
        self.chain = 'Zora'
        self.chain_from_id = next((k for k, v in LAYERZERO_NETWORKS_DATA.items() if v[0] == self.chain), None)

    async def get_nft_id(self, contract):  
        balance_nft = await contract.functions.balanceOf(self.client.address).call()
        nft_ids = []
        for i in range(balance_nft):
            nft_ids.append(await contract.functions.tokenOfOwnerByIndex(self.client.address, i).call())
        if nft_ids:
            return nft_ids[-1]
        return False

    async def get_estimate_send_fee(self, contract, adapter_params, dst_chain_id,
                                    nft_id):  
        estimate_gas_bridge_fee = (await contract.functions.estimateSendFee(
            dst_chain_id,
            self.client.address,
            nft_id,
            False,
            adapter_params
        ).call())[0]

        return estimate_gas_bridge_fee

    @gas_checker
    async def refuel(self):  
        dst_data = random.choice(list(DST_CHAIN_L2PASS_REFUEL.items()))  

        dst_chain_name, dst_chain_id, dst_native_name, dst_native_api_name = LAYERZERO_NETWORKS_DATA[
            dst_data[0]]  
        dst_amount = self.client.round_amount(*dst_data[1])

        refuel_info = f'{dst_amount} {dst_native_name} to {dst_chain_name} from {self.chain}'
        logger.info(f'Refuel on L2Pass: {refuel_info}')

        l2pass_contracts = L2PASS_CONTRACTS_PER_CHAINS[self.chain_from_id]
        refuel_contract = self.client.get_contract(l2pass_contracts['refuel'], L2PASS_ABI['refuel'])

        dst_native_gas_amount = int(dst_amount * 10 ** 18)
        dst_contract_address = L2PASS_CONTRACTS_PER_CHAINS[LAYERZERO_WRAPED_NETWORKS[dst_data[0]]][
            'refuel']  

        try:
            estimate_send_fee = (await refuel_contract.functions.estimateGasRefuelFee(  
                dst_chain_id,
                dst_native_gas_amount,
                dst_contract_address,
                False
            ).call())[0]

            transaction = await refuel_contract.functions.gasRefuel(
                dst_chain_id,
                ZERO_ADDRESS,
                dst_native_gas_amount,
                self.client.address
            ).build_transaction(await self.client.prepare_transaction(value=estimate_send_fee))

            tx_hash = await self.client.send_tx(transaction)

            return await self.client.verif_tx(tx_hash)

        except Exception as err:
            logger.error(err)

    @gas_checker
    async def mint(self):
        onft_contract = self.client.get_contract(L2PASS_CONTRACTS_PER_CHAINS[self.chain_from_id]['ONFT'],
                                                 L2PASS_ABI['ONFT'])

        mint_price = await onft_contract.functions.mintPrice().call()  

        logger.info(
            f"Mint L2Pass NFT on {self.chain}. "
            f"Mint Price: {(mint_price / 10 ** 18):.5f} ETH")

        tx_params = await self.client.prepare_transaction(value=mint_price)

        transaction = await onft_contract.functions.mintWithReferral(
            1,
            '0x000000a679C2FB345dDEfbaE3c42beE92c0Fb7A5'
        ).build_transaction(tx_params)

        tx_hash = await self.client.send_tx(transaction)

        return await self.client.verif_tx(tx_hash)

    @gas_checker
    async def bridge(self):
        dst_chain = random.choice(DST_CHAIN_L2PASS_NFT)

        onft_contract = self.client.get_contract(L2PASS_CONTRACTS_PER_CHAINS[self.chain_from_id]['ONFT'],
                                                 L2PASS_ABI['ONFT'])

        dst_chain_name, dst_chain_id, _, _ = LAYERZERO_NETWORKS_DATA[dst_chain]

        nft_id = await self.get_nft_id(onft_contract)

        if not nft_id:
            restart_client = await self.client.restart_client()
            await L2Pass(restart_client).mint()
            nft_id = await self.get_nft_id(onft_contract)
            await asyncio.sleep(random.randint(5, 10))

        logger.info(f'Bridge L2Pass NFT from {self.chain} to {dst_chain_name}. ID: {nft_id}')

        version, gas_limit = 1, 200000

        adapter_params = encode(["uint16", "uint256"],
                                [version, gas_limit])

        adapter_params = self.client.w3.to_hex(adapter_params[30:])

        send_price = await onft_contract.functions.sendPrice().call()

        estimate_send_fee = await self.get_estimate_send_fee(onft_contract, adapter_params, dst_chain_id, nft_id)

        tx_params = await self.client.prepare_transaction(value=int(estimate_send_fee + send_price))

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
    async def gas_station(self):
        num = random.randint(1, 2)
        gas_data = [item for item in L2PASS_GAS_STATION_DATA if item[0] != 41]
        gas_data = random.sample(gas_data, num)
        random.shuffle(gas_data) 
        total_gas = 0
        refuel_list = []

        logger.info(f"Refuel with Gas Station from {self.chain}. Destination networks count: {len(gas_data)}")

        gas_contract = self.client.get_contract(
            L2PASS_CONTRACTS_PER_CHAINS[self.chain_from_id]['gas_station'],
            L2PASS_ABI['gas_station'],
        )

        for chain_id_to, amount in gas_data:
            if isinstance(chain_id_to, list):  #
                chain_id_to = random.choice(chain_id_to)
            dst_chain_name, dst_chain_id, dst_native_name, dst_native_api_name = LAYERZERO_NETWORKS_DATA[chain_id_to]
            dst_amount = int(self.client.round_amount(*(amount, amount * 1.2)) * 10 ** 18)
            adapter_params = await gas_contract.functions.createAdapterParams(
                dst_chain_id,
                dst_amount,
                self.client.address
            ).call()

            gas_for_refuel = await gas_contract.functions.estimateFees(
                dst_chain_id,
                adapter_params
            ).call()

            refuel_list.append([dst_chain_id, dst_amount])
            total_gas += gas_for_refuel

        transaction = await gas_contract.functions.useGasStation(
            refuel_list,
            self.client.address
        ).build_transaction(await self.client.prepare_transaction(value=total_gas))

        tx_hash = await self.client.send_tx(transaction)

        return await self.client.verif_tx(tx_hash)
