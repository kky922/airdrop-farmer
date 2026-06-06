# -*- coding: utf-8 -*-
"""MegaETH Testnet"""
from chains.base import BaseChain

class MegaETHChain(BaseChain):
    def __init__(self):
        super().__init__("megaeth")
