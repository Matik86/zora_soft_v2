import asyncio
import random
from web3.eth import AsyncEth
from loguru import logger
from web3 import AsyncWeb3, AsyncHTTPProvider

from datas.DATA import headers, proxies, rpc, proxy
from settings.general_settings import GAS_GWEI


class Client:
    
    def __init__( self, private_key: str=None):
        self.private_key = private_key
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={'proxy': proxy, 'headers':headers}), modules={"eth": (AsyncEth)}, middlewares=[])
        self.address = AsyncWeb3.to_checksum_address(self.w3.eth.account.from_key(private_key=private_key).address)
        
        if proxies: 
           self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={'proxy': proxies[self.address], 'headers':headers}), modules={"eth": (AsyncEth)}, middlewares=[])

    @staticmethod
    def round_amount(min_amount: float, max_amount: float) -> float:
        decimals = max(len(str(min_amount)) - 1, len(str(max_amount)) - 1)
        return round(random.uniform(min_amount, max_amount), decimals + 2)

    async def restart_client(self):
        restart_client = Client(self.private_key)
        return restart_client

    def get_contract(self, contract_address, abi):
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(contract_address),
            abi=abi
        )

    async def get_priotiry_fee(self):
        fee_history = await self.w3.eth.fee_history(25, 'latest', [20.0])
        non_empty_block_priority_fees = [fee[0] for fee in fee_history["reward"] if fee[0] != 0]

        divisor_priority = max(len(non_empty_block_priority_fees), 1)

        priority_fee = int(round(sum(non_empty_block_priority_fees) / divisor_priority))

        return priority_fee

    async def prepare_transaction(self, value: int = 0):
            try:
                tx_params = {
                    'from': self.w3.to_checksum_address(self.address),
                    'nonce': await self.w3.eth.get_transaction_count(self.address),
                    'value': value,
                    'chainId': await self.w3.eth.chain_id
                }

                base_fee = await self.w3.eth.gas_price
                max_priority_fee_per_gas = self.w3.to_wei(GAS_GWEI, 'gwei') # await self.get_priotiry_fee()
                max_fee_per_gas = base_fee + max_priority_fee_per_gas

                tx_params['maxPriorityFeePerGas'] = max_priority_fee_per_gas
                tx_params['maxFeePerGas'] = max_fee_per_gas
                tx_params['type'] = '0x2'

                return tx_params

            except Exception as error:
                logger.error(f'{error}')

    async def send_tx(
            self,
            transaction=None,
            contract_address=None,
            data=None,
            value=None,
    ):
        tx_data = {}
        try:
            if transaction:
                singed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.w3.eth.send_raw_transaction(singed_tx.rawTransaction)
                tx_data = {
                    'tx_hash': tx_hash,
                    'value': transaction['value'],
                    'data': transaction['data'],
                    'gas': transaction['gas']
                }
                return tx_data

            tx_params = {
                'chainId': await self.w3.eth.chain_id,
                'nonce': await self.w3.eth.get_transaction_count(AsyncWeb3.to_checksum_address(self.address)),
                'from': self.address,
                'to': AsyncWeb3.to_checksum_address(contract_address),
                'gasPrice': await self.w3.eth.gas_price
            }

            if value:
                tx_params['value'] = value
                tx_data['value'] = tx_params['value']
            else:
                tx_data['value'] = 0

            if data:
                tx_params['data'] = data

            try:
                tx_params['gas'] = int(await self.w3.eth.estimate_gas(tx_params))
                tx_data['gas'] = tx_params['gas']

            except Exception as err:
                logger.error(f'\n{self.address} | transaction failed | {err}')
                return

            sign = self.w3.eth.account.sign_transaction(tx_params, self.private_key)
            tx_hash = await self.w3.eth.send_raw_transaction(sign.rawTransaction)
            tx_data['tx_hash'] = tx_hash
            return tx_data

        except Exception as err:
            print(f'{err}')

    async def verif_tx(self, tx_data: dict) -> dict:
        result = {}
        try:
            data = await self.w3.eth.wait_for_transaction_receipt(tx_data['tx_hash'], timeout=200)

            if 'status' in data and data['status'] == 1:
                logger.success(f'transaction completed: {tx_data["tx_hash"].hex()}')
                result['status'] = True
                result['value'] = tx_data['value']
                result['gas'] = tx_data['gas']
                return result

            else:
                logger.error(f'transaction failed {data["transactionHash"].hex()}')
                result['status'] = False
                result['value'] = tx_data['value']
                result['gas'] = tx_data['gas']
                return result

        except Exception as err:
            logger.error(f'\n{self.address} | {err}')
            result['status'] = False
            return result

        except Exception as err:
            logger.error(f'\n{self.address} | {err}')
            result['status'] = False
            return result