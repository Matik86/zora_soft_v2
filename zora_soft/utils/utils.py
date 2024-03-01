import functools
import io
import random
import string
import aiofiles
import asyncio
import json
import requests
import numpy as np
from typing import Optional
from loguru import logger
from web3.eth import AsyncEth
from web3 import AsyncWeb3, AsyncHTTPProvider
from requests_toolbelt import MultipartEncoder

from datas.DATA import proxy, ETH_rpc
from settings.general_settings import (GAS_CONTROL, SLEEP_TIME_GAS, CONTROL_TIMES_FOR_SLEEP, MAX_GWEI,
                                       NONCE_RANGE, ASYNC_MODE)

def read_json(path: str, encoding: Optional[str] = None) -> list | dict:
    return json.load(open(path, encoding=encoding))

async def wallets_filework() -> list:  
    async with aiofiles.open('./datas./private_keys.txt', 'r') as file:
        privates_lst = []
        async for private_key in file:
            privates_lst.append(private_key.rstrip())
            
    return privates_lst

def get_eth_price():
        url = 'https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USDT'
        response = requests.get(url)
        data = response.json()
        
        return data['USDT']
    
def short_address(address):
    return address[:6] + '...' + address[-3:]

def gas_checker(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        if GAS_CONTROL:
            await asyncio.sleep(1)
            print()
            flag = False
            counter = 0

            w3 = AsyncWeb3(AsyncHTTPProvider(ETH_rpc),
                                                 modules={"eth": (AsyncEth)}, middlewares=[])
            while True:
                gas = round(AsyncWeb3.from_wei(await w3.eth.gas_price, 'gwei'), 3)
                if flag and counter == CONTROL_TIMES_FOR_SLEEP:
                    logger.warning(f'Over the last {(counter * SLEEP_TIME_GAS) // 60} min, gas price has not returned to normal')
                    return await func(self, *args, **kwargs)
                if gas < MAX_GWEI:
                    await asyncio.sleep(1)
                    return await func(self, *args, **kwargs)
                else:
                    flag = True
                    counter += 1
                    await asyncio.sleep(1)
                    logger.warning(f'{gas} Gwei | Gas is too high. Next check in {SLEEP_TIME_GAS} second')
                    await asyncio.sleep(SLEEP_TIME_GAS)
        return await func(self, *args, **kwargs)
    return wrapper

class PrivatesSet:

    def __init__(self, privates_lst: list, nonce: int, execution_speed: str =None, batch_part: int =100):
        self.privates_lst = privates_lst
        self.nonce = nonce
        self.execution_speed = execution_speed
        self.batch_part = batch_part


    def generate_privates_set(self) -> dict:
        all_privates_amount = len(self.privates_lst)
        privates_amount = int(all_privates_amount * (self.batch_part / 100))
        new_privates_lst = random.sample(self.privates_lst, privates_amount)

        privates_set = {}
        for private_key in new_privates_lst:
            privates_set[private_key] = []
            num = NONCE_RANGE
            privates_set[private_key].append(random.randint(self.nonce - num, self.nonce + num))
            speed_mapping = {
                None: ['slow', 'medium', 'fast'],
                'slow': ['slow'],
                'medium': ['medium'],
                'fast': ['fast']
            }

            if not ASYNC_MODE:
                    speed_mapping[None].remove('slow')

            privates_set[private_key].append(random.choice(speed_mapping[self.execution_speed]))



        return privates_set

    def fix_privates_set(self, privates_set: dict) -> dict:
        if self.execution_speed:
            return privates_set
        else:
            nonces = [[v[0] for k, v in privates_set.items() if v[1] != 'slow']]
            average = np.mean(nonces)
            for private_key in privates_set.keys():
                if privates_set[private_key][1] == 'slow' and privates_set[private_key][0] > average:
                    privates_set[private_key][0] = int(average) - random.randint(1, NONCE_RANGE)

            return privates_set

    def privates_set(self):
        privates_set_raw = self.generate_privates_set()
        privates_set = self.fix_privates_set(privates_set_raw)

        return privates_set

class IPFS:

    def __init__(self):
        self.proxy = {'http' : proxy,
                      'https': proxy}

    def upload_ipfs(self, filename, data, ext):
        fields = {
            'file': (filename, io.BytesIO(data), ext),
        }
        boundary = '------WebKitFormBoundary' + ''.join(random.sample(string.ascii_letters + string.digits, 16))
        m = MultipartEncoder(fields=fields, boundary=boundary)
        resp = requests.post('https://ipfs-uploader.zora.co/api/v0/add?stream-channels=true&cid-version=1&progress=false',
                             data=m, headers={'content-type': m.content_type}, proxies=self.proxy, timeout=60)

        if resp.status_code != 200:
            raise Exception(f'status_code = {resp.status_code}, response = {resp.text}')
        try:
            return resp.json()['Hash']
        except Exception:
            raise Exception(f'status_code = {resp.status_code}, response = {resp.text}')

    def upload_image_ipfs(self, name):
        img_szs = [i for i in range(500, 1001, 50)]
        url = f'https://picsum.photos/{random.choice(img_szs)}/{random.choice(img_szs)}'
        resp = requests.get(url, proxies=self.proxy, timeout=60)

        if resp.status_code != 200:
            raise Exception(f'Get random image failed, status_code = {resp.status_code}, response = {resp.text}')

        filename = name.replace(' ', '_').lower() + '.jpg'
        return self.upload_ipfs(filename, resp.content, 'image/jpg')

    def get_image_uri(self, name):
        return 'ipfs://' + self.upload_image_ipfs(name)

    def get_json_uri(self, body):
        return 'ipfs://' + self.upload_ipfs('', bytes(body, 'utf-8'), '')
