import fake_useragent


rpc = 'https://rpc.zora.energy'
ETH_rpc = 'https://rpc.ankr.com/eth'

proxy = 'http://log:passwd:@ip:port'


proxies = {
    'private_key' : 'http://log:passwd:@ip:port'
    }

headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'user-agent': fake_useragent.UserAgent().random
        }

    

        
