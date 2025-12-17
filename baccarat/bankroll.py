# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 16:26:57 2025

@author: hyunilPark
"""

class Bankroll:
    def __init__(self, player_money, banker_money):
        self.player_money = player_money
        self.banker_money = banker_money
        
    def apply_result(self , bet_type , payout):
        """
        payout 기준으로 실제 돈 반영
        """
        
        if bet_type == "PLAYER":
            self.player_money += payout
        elif bet_type == "BANKER":
            self.banker_money += payout
            
            
    def snapshot(self):
        return {
            "player_money": self.player_money,
            "banker_money": self.banker_money
            }