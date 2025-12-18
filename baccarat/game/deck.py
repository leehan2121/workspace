# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 14:14:11 2025

@author: hyunilPark , leehan2121@gmail.com
"""

import random

class Deck:
    """
    Deck 클래스

    역할:
        - 4 / 6 / 8 덱 생성
        - 카드 셔플
        - 카드 한 장 뽑기
        - 남은 카드 수 확인
    """

    SUITS = ['♠', '♥', '♣', '♦']

    def __init__(self, num_decks=8):
        """
        Parameters
        ----------
        num_decks : int
            사용할 덱 개수 (보통 4, 6, 8)
        """
        self.num_decks = num_decks
        self.cards = []
        self._build_deck()
        self.shuffle()

    def _build_deck(self):
        """
        카드 풀 생성 (내부 전용)
        """
        card_types = ['A','2','3','4','5','6','7','8','9','10','J','Q','K']
        self.cards = []
        for _ in range(self.num_decks):
            for card in card_types:
                for _ in range(4):  # 각 카드 4장
                    self.cards.append(card)

    def shuffle(self):
        """
        카드 섞기
        """
        random.shuffle(self.cards)

    def draw(self):
        """
        카드 한 장 뽑기

        Returns
        -------
        tuple : (suit, rank)
        """
        if not self.cards:
            raise RuntimeError("덱에 카드가 없습니다.")
        card = self.cards.pop()
        suit = random.choice(self.SUITS)
        return (suit, card)

    def remaining_cards(self):
        """
        덱에 남은 카드 수 확인
        """
        return len(self.cards)