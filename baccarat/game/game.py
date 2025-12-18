# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 15:05:52 2025

@author: hyunilPark
"""

from game.logger import GameLogger
from game.rules import (
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
    if bet_type == "PLAYER":
        if winner == "PLAYER":
            payout_player = bet_amount
            payout_casino = -bet_amount
        elif winner == "BANKER":
            payout_player = -bet_amount
            payout_casino = bet_amount
        else:  # TIE
            payout_player = 0
            payout_casino = 0
    elif bet_type == "BANKER":
        if winner == "BANKER":
            payout_player = bet_amount * 0.95  # 커미션 5%
            payout_casino = -payout_player
        elif winner == "PLAYER":
            payout_player = -bet_amount
            payout_casino = bet_amount
        else:  # TIE
            payout_player = 0
            payout_casino = 0
    elif bet_type == "TIE":
        if winner == "TIE":
            payout_player = bet_amount * 8
            payout_casino = -payout_player
        else:  # PLAYER / BANKER 승
            payout_player = -bet_amount
            payout_casino = bet_amount
    else:
        # 안전 장치
        payout_player = 0
        payout_casino = 0

    # 함수 끝에서 항상 return
    return payout_player, payout_casino


def play_round(round_no , deck, bet_type, bet_amount , bankroll , reveal=True):
    # 1. 플레이어 / 뱅커 패 초기화
    player_hand = []
    banker_hand = []

    # 2. 덱 상태 확인 (마지막 판 여부)
    last_round = deck.remaining_cards() < MIN_CARDS_FOR_ROUND

    # 3. 카드 배분
    for _ in range(2):
        now_card = deck.draw()
        player_hand.append(now_card)
        now_card = deck.draw()
        banker_hand.append(now_card)

    # 4. 내추럴 체크
    if is_natural(player_hand, banker_hand):
        player_score = hand_score(player_hand)
        banker_score = hand_score(banker_hand)
        winner = determine_winner(player_score, banker_score)
        # 정산
        payout_player, payout_casino = calculate_payout(winner, bet_type, bet_amount)
        bankroll.player_money += payout_player
        bankroll.casino_money += payout_casino

        result = {
            "player_hand": player_hand,
            "banker_hand": banker_hand,
            "player_score": player_score,
            "banker_score": banker_score,
            "winner": winner,
            "payout": payout_player,
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
    payout_player, payout_casino = calculate_payout(winner, bet_type, bet_amount)
    bankroll.player_money += payout_player
    bankroll.casino_money += payout_casino
  
    # 9. 결과 반환
    result = {
        "player_hand": player_hand,
        "banker_hand": banker_hand,
        "player_score": player_score,
        "banker_score": banker_score,
        "winner": winner,
        "payout": payout_player,
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