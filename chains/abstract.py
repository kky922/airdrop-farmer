# -*- coding: utf-8 -*-
"""Abstract Chain"""
from chains.base import BaseChain

class AbstractChain(BaseChain):
    def __init__(self):
        super().__init__("abstract")
