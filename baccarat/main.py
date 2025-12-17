# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 11:43:15 2025

@author: hyunilPark
"""
from deck import Deck
from game import play_round
from bankroll import Bankroll

# =======================
# 설정값
# =======================
INITIAL_MONEY = 100_000
BET_AMOUNT = 1_000


# 덱 생성 (8 deck)

deck = Deck()
bankroll = Bankroll(
    player_money=INITIAL_MONEY, 
    banker_money=INITIAL_MONEY
)

round_no = 1
print("Baccarat Game START")

while deck.remaining_cards() >= 6:
    
    print(f"\n=== ROUND {round_no} ===")
    print("Player Money:", bankroll.player_money)
    print("Banker Money:", bankroll.banker_money)
    
    #실제 선택
    bet_type = input("Bet on (1) PLAYER / 2) BANKER / 3) TIE): ").strip().upper()
    
    if bet_type not in (1 , 2 , 3):
        print("Invalid bet type")
        continue
    
    if bankroll.player_money < BET_AMOUNT:
        print("Player money insufficient")
        break
    
    result = play_round(
        round_no=round_no, 
        deck=deck, 
        bet_type=bet_type, 
        bet_amount=BET_AMOUNT, 
        bankroll=bankroll
        )
    
    
    print("Player hand:" , result["player_hand"] , "score:" , result.get("player_scope") )
    print("banker_hand:" , result["banker_hand"] , "score:" , result.get("banker_scope") )
    print("Winner:" , result["winner"])
    print("Payout:" , result["payout"])
    print("Banker Money:" , bankroll.banker_money)
    
    if result["natural"]:
        print("-> Natural")
        
    if result["last_round"]:
        print("⚠️ This was the LAST round of the shoe")
        break
    
    round_no += 1
    
    print("\n Game Over")
    print("Final Player Money :", bankroll.player_money)
    print("Final Player Money :", bankroll.banker_money)