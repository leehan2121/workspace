# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 15:05:52 2025

@author: hyunilPark
"""

from logger import GameLogger
from rules import (
    hand_score,
    is_natural,
    should_player_draw,
    should_banker_draw,
    determine_winner
)

logger = GameLogger()

# 베팅 배당률 상수
PAYOUT_RATES = {
    "PLAYER": 1.0,
    "BANKER": 0.95,   # 5% 커미션
    "TIE": 8.0
}

MIN_CARDS_FOR_ROUND = 6


def calculate_payout(winner, bet_type, bet_amount):
    """
    베팅 정산 공통 로직
    """
    if winner == "TIE" and bet_type != "TIE":
        return 0
    elif bet_type == winner:
        return bet_amount * PAYOUT_RATES[bet_type]
    else:
        return bet_amount



def play_round(round_no , deck, bet_type, bet_amount , bankroll):
    # 1. 플레이어 / 뱅커 패 초기화
    player_hand = []
    banker_hand = []

    # 2. 덱 상태 확인 (마지막 판 여부)
    last_round = deck.remaining_cards() < MIN_CARDS_FOR_ROUND

    # 3. 카드 배분
    for _ in range(2):
        player_hand.append(deck.draw())
        banker_hand.append(deck.draw())

    # 4. 내추럴 체크
    if is_natural(player_hand, banker_hand):
        player_score = hand_score(player_hand)
        banker_score = hand_score(banker_hand)
        winner = determine_winner(player_score, banker_score)
        payout = calculate_payout(winner, bet_type, bet_amount)

        bankroll.player_money += payout
        bankroll.banker_money -= payout
        
        result = {
            "player_hand": player_hand,
            "banker_hand": banker_hand,
            "player_score": player_score,
            "banker_score": banker_score,
            "winner": winner,
            "payout": payout,
            "natural": True,
            "last_round": last_round
        }

        logger.log_round(
            round_no ,
            bet_type , 
            bet_amount , 
            result ,
            bankroll
        )
        
        return result
    
    # 5. 플레이어 3rd 카드
    player_third_card = None
    if should_player_draw(player_hand):
        player_third_card = deck.draw()
        player_hand.append(player_third_card)

    # 6. 뱅커 3rd 카드
    if should_banker_draw(banker_hand, player_third_card):
        banker_hand.append(deck.draw())

    # 7. 최종 점수 및 승자
    player_score = hand_score(player_hand)
    banker_score = hand_score(banker_hand)
    winner = determine_winner(player_score, banker_score)

    # 8. 베팅 정산
    payout = calculate_payout(winner, bet_type, bet_amount)

    bankroll.player_money += payout
    bankroll.banker_money -= payout
  
    # 9. 결과 반환
    result = {
        "player_hand": player_hand,
        "banker_hand": banker_hand,
        "player_score": player_score,
        "banker_score": banker_score,
        "winner": winner,
        "payout": payout,
        "natural": False,
        "last_round": last_round
    }

    logger.log_round(
        round_no = round_no ,
        bet_type = bet_type , 
        bet_amount = bet_amount , 
        result = result ,
        bankroll=bankroll
    )

    return result