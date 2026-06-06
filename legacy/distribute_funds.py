#!/usr/bin/env python3
"""마스터 지갑에서 4개 지갑으로 MON 분배"""
import sys; sys.path.insert(0, '.')
from web3 import Web3
from eth_account import Account
import config, time

Account.enable_unaudited_hdwallet_features()

rpc = config.CHAIN_REGISTRY.get('monad', {}).get('rpc')
w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))

master_key = config.MASTER_PRIVATE_KEY
master_addr = config.MASTER_ADDRESS

wallets = []
for i in range(config.NUM_WALLETS):
    acct = Account.from_mnemonic(config.HD_MNEMONIC, account_path="m/44'/60'/0'/0/{}".format(i))
    wallets.append(acct)

print('💸 Monad 자금 분배 시작')
print('=' * 50)

SEND_AMOUNT = w3.to_wei(1.5, 'ether')
chain_id = w3.eth.chain_id
gas_price = w3.eth.gas_price

for i, acct in enumerate(wallets):
    if i == 0:
        continue
    nonce = w3.eth.get_transaction_count(master_addr)
    tx = {
        'to': acct.address,
        'value': SEND_AMOUNT,
        'gas': 21000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': chain_id,
    }
    signed = w3.eth.account.sign_transaction(tx, master_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print('  ✅ 지갑{} ({}...): 1.5 MON 전송'.format(i+1, acct.address[:10]))
    print('     TX: {}'.format(tx_hash.hex()))
    time.sleep(3)

print('\n⏳ 컨펌 대기...')
time.sleep(5)

print('\n📊 최종 잔액:')
total = 0
for i, acct in enumerate(wallets):
    bal = w3.eth.get_balance(acct.address)
    eth = float(w3.from_wei(bal, 'ether'))
    total += eth
    icon = '✅' if eth > 0 else '⚠️'
    role = '(마스터)' if i == 0 else '(지갑{})'.format(i+1)
    print('  {} {}: {:.4f} MON'.format(icon, role, eth))

print('  💰 총합: {:.4f} MON'.format(total))