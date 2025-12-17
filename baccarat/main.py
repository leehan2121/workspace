# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 11:43:15 2025

@author: hyunilPark
"""
from deck import Deck
from game import play_round


# 덱 생성 (8 deck)

deck = Deck(num_decks=8)

round_count = 1

while True:
    print(f"\n=== ROUND {round_count} ===")
    
    result = play_round(deck)
    
    print("Player hand:" , result["player_hand"] , "score:" , result.get("player_scope") )
    print("banker_hand:" , result["banker_hand"] , "score:" , result.get("banker_scope") )
    print("Winner:" , result["winner"])
    
    if result["natural"]:
        print("-> Natural win")
        
    if result["last_round"]:
        print("⚠️ This was the LAST round of the shoe")
        break
    
    round_count += 1