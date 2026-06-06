# -*- coding: utf-8 -*-
"""Monad Testnet - free gas!"""
from chains.base import BaseChain

class MonadChain(BaseChain):
    def __init__(self):
        super().__init__("monad")

    async def swap(self, pk, token_in, token_out, amount):
        addr = self._get_address(pk)
        tx = self._build_tx(addr, to=addr, value=0)
        return self._send_tx(pk, tx)

    async def lend(self, pk, token, amount):
        addr = self._get_address(pk)
        tx = self._build_tx(addr, to=addr, value=0)
        return self._send_tx(pk, tx)