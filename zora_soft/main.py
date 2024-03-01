import csv
import random
import asyncio
import aiofiles
from web3 import Web3, AsyncHTTPProvider
from datetime import datetime
from web3.eth import AsyncEth
from termcolor import cprint
from decimal import Decimal
from loguru import logger

from modules.client import Client
from datas.DATA import headers, proxy, rpc
from utils.utils import PrivatesSet, wallets_filework, get_eth_price
from modules import (Create, L2Pass, MintFun, MintZora, Merkly, Zerius)
from settings.settings import MODULES_PROBABILITY, L2PASS_PROBABILITY
from settings.general_settings import (EXECUTION_SPEED,BATCH_PART, ASYNC_MODE, DELAY_BTW_ACCOUNTS, DELAY_FAST_MODE,
                                       DELAY_MEDIUM_MODE, DELAY_SLOW_MODE, TOTAL_NONCE_MODE)


class RandomActivity:

    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    def choice(weights: dict):
        total_weight = sum(weights.values())
        random_number = random.random()
        cumulative_weight = 0
        for module, probability in weights.items():
            cumulative_weight += probability / total_weight
            if random_number <= cumulative_weight:
                return module

    async def run_random_activity(self):
        module_name = self.choice(MODULES_PROBABILITY)

        if module_name == 'CreateNFT':
            return await Create(self.client).create()
        elif module_name == 'L2pass':
            activity_name = self.choice(L2PASS_PROBABILITY)

            if activity_name == 'refuel':
                return await L2Pass(self.client).refuel()
            elif activity_name == 'mint':
                return await L2Pass(self.client).mint()
            elif activity_name == 'gas_station':
                return await L2Pass(self.client).gas_station()
            elif activity_name == 'bridge':
                return await L2Pass(self.client).bridge()
        elif module_name == 'Merkly':
            return await Merkly(self.client).refuel()
        elif module_name == 'MintZora':
            return await MintZora(self.client).mint()
        elif module_name == 'MintFun':
            return await MintFun(self.client).mint()
        elif module_name == 'Zerius':
            return await Zerius(self.client).refuel()

class Run:
    
    num_of_done = 0
    accounts_results = {}
    
    def __init__(self, privates_dict):
        self.w3 = Web3(AsyncHTTPProvider(rpc, request_kwargs={'proxy': proxy, 'headers':headers}), modules={"eth": (AsyncEth)}, middlewares=[])
        self.privates_dict = privates_dict
        self.wallets_num = len(list(privates_dict.keys()))
        
    async def random_tx(self): # задает многопоточное выполнение транзакций
        try:            
            if self.privates_dict:
                private_keys = list(self.privates_dict.keys())
                random.shuffle(private_keys)
                if not ASYNC_MODE:
                    for private_key in private_keys:
                        await self.process_account(private_key)

                        if self.accounts_results[private_key]:
                            a, b = DELAY_BTW_ACCOUNTS
                            delay = random.randint(a, b)
                            logger.info(f'waiting for another account...({delay//60} min {delay%60} sec)')
                            await asyncio.sleep(delay)

                        else:
                            await asyncio.sleep(1)

                else:
                    await asyncio.gather(*[self.process_account(private_key) for private_key in private_keys])

        except Exception as err:
            logger.info(f'{err}')
            
        finally:
            if self.accounts_results:
                    logger.success(f'{self.num_of_done} accounts completed')
                    await self.generate_csv()
            else:
                if self.num_of_done == 0:    
                   logger.warning('The program did not have time to execute any of the accounts')
                else:
                   logger.success(f'{self.num_of_done} accounts completed')
                 
    async def process_account(self, private_key): # проверяет критерии
        try:
            address = Web3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)
            if not TOTAL_NONCE_MODE:
                count = self.accounts_results.get(private_key, {}).get('count', 0)

                if count < self.privates_dict[private_key][0]:
                    logger.info(f'{address} | {self.privates_dict[private_key][0] - count} transactions left to complete')
                    await self.transaction_manager(private_key)
                    return await self.process_account(private_key)

                else:
                    self.num_of_done += 1
                    self.privates_dict.pop(private_key)
                    logger.success(f'{self.num_of_done}/{self.wallets_num} accounts completed')
                    return

            else:
                    nonce = await self.w3.eth.get_transaction_count(address)

                    if nonce < self.privates_dict[private_key][0]:
                        logger.info(f'{address} | {self.privates_dict[private_key][0] - nonce} transactions left to complete')
                        await self.transaction_manager(private_key)
                        return await self.process_account(private_key)

                    else:
                        self.num_of_done += 1
                        self.privates_dict.pop(private_key)
                        logger.success(f'{self.num_of_done}/{self.wallets_num} accounts completed')
                        return
                
        except Exception as err:
            logger.error(f'{err}')

    async def transaction_manager(self, private_key, result: bool=None): # проверяет/делает задержки между транзакциями
        address = Web3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)

        if result or result is None:
            if self.privates_dict[private_key][1] == 'slow':
                a, b = DELAY_SLOW_MODE
                delay = random.randint(a, b)
            elif self.privates_dict[private_key][1] == 'medium':
                a, b = DELAY_MEDIUM_MODE
                delay = random.randint(a, b)
            elif self.privates_dict[private_key][1] == 'fast':
                a, b = DELAY_FAST_MODE
                delay = random.randint(a, b)

            logger.info(f'{address} | waiting for transaction...({delay//60} min {delay%60} sec)')

            await asyncio.sleep(delay)

            return await self.init_tx(private_key)

        else:
            await self.init_tx(private_key)

    async def init_tx(self, private_key): # инициализаций транзакций/запись результата
        if private_key not in self.accounts_results:
           self.accounts_results[private_key] = {}
           self.accounts_results[private_key]['count'] = 0
           self.accounts_results[private_key]['gas'] = 0
           self.accounts_results[private_key]['value'] = 0

        try:
            client = Client(private_key)
            result = await RandomActivity(client).run_random_activity()
            if result['status']:
                self.accounts_results[private_key]['count'] += 1
                self.accounts_results[private_key]['gas'] += result['gas']
                self.accounts_results[private_key]['value'] += result['value']
                return

            else:
                return await self.transaction_manager(private_key, False)

        except Exception as err:
            logger.error(f'{err}')
            return await self.transaction_manager(private_key, False)
    async def generate_csv(self):
        time = datetime.now().strftime('%d.%m.%Y_%H`%M')
        async with aiofiles.open(f"./results./results_{time}.csv", 'w', newline='') as file:
            writer = csv.writer(file, delimiter=';')
            headers = ['num', 'address', 'tx total count', 'tx count', 'eth value', 'usd value', 'average gas']
            await writer.writerow(headers)
            
            for i, private_key in enumerate(list(self.accounts_results.keys())):
                address = Web3.to_checksum_address(self.w3.eth.account.from_key(private_key).address)
                nonce = await self.w3.eth.get_transaction_count(address)
                row = [i + 1, address]
                row.append(nonce)
                row.append(self.accounts_results[private_key]['count'])
                value = self.w3.from_wei(self.accounts_results[private_key]['value'], 'ether')
                eth = self.w3.from_wei(self.accounts_results[private_key]['gas']*10**9 / 2, 'ether') + value # расчет комсы
                row.append(f'{round(eth, 5)} ETH')
                row.append(f'${(eth * Decimal(get_eth_price())):,.2f}')
                row.append(self.accounts_results[private_key]['gas'] / self.accounts_results[private_key]['count'])
                
                await writer.writerow(row)
                
        return cprint(f'\nAll results are written to a file: results_{time}.csv\n', 'blue')


async def run():
    try:
        privates_lst = await wallets_filework()
        if not TOTAL_NONCE_MODE:
            nonce = int(input('\nEnter the required number of transactions to do: '))
        else:
            nonce = int(input('\nEnter the required number of transactions(total nonce): '))
        set = PrivatesSet(privates_lst, nonce, EXECUTION_SPEED, BATCH_PART)
        privates_dict = set.privates_set()
        action = Run(privates_dict)
        return await action.random_tx()

    except Exception as err:
        logger.error(f'{err}')


if __name__ == '__main__':
    asyncio.run(run())

