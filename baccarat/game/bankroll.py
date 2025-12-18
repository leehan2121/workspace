# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 16:26:57 2025

@author: hyunilPark
"""

class Bankroll:
    def __init__(self, player_money, casino_money):
        self.player_money = player_money
        self.casino_money = casino_money  # 기존 banker_money 대신 casino_money 사용
    
    def apply_result(self, payout_player, payout_casino):
        """
        플레이어/카지노 금액 동시 업데이트
        payout_player : 플레이어 수익/손실
        payout_casino : 카지노 수익/손실
        """
        self.player_money += payout_player
        self.casino_money += payout_casino
    
    def snapshot(self):
        return {
            "player_money": self.player_money,
            "casino_money": self.casino_money
        }