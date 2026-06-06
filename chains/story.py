# -*- coding: utf-8 -*-
"""Story Protocol"""
from chains.base import BaseChain

class StoryChain(BaseChain):
    def __init__(self):
        super().__init__("story")
