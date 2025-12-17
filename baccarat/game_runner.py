# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 17:20:26 2025

@author: hyunilPark
"""

from deck import Deck
from game import play_round
from bankroll import Bankroll

deck = Deck()
deck.shuffle()

bankroll = Bankroll(
    player_money=100_000,
    banker_money=100_000,
    )

round_no = 1

while True:
    print(f"\n🎲 ROUND {round_no}")
    
    result = play_round(
        deck=deck, 
        bet_type="PLAYER", 
        bet_amount=10_000
    )
    
    bankroll.apply_result("PLAYER" , result["payout"])
    
    print("결과" , result["winner"])
    print("지급금" , result["payout"])
    print("잔액" , bankroll.snapshot())
    
    if result["last_round"]:
        print("🛑 슈 종료. 덱 재셔플")
        deck.reset()
        deck.shuffle()
        
    if bankroll.player_money <= 0:
        print("💀 플레이어 파산")
        break
    
    round_no += 1
    
    