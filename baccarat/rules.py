# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 11:45:25 2025

@author: hyunilPark , leehan2121@gmail.com
"""

#바카라 규칙 파일 

def card_value(card):
    """
    카드 한잔의 점수 반환
    A=1 , 2~9 = 그대로 , 10/J/Q/K = 10
    
    Parameters
    ----------
    card : TYPE
        DESCRIPTION.
    Returns int
    
    -------
    None.

    """
    if card == 'A':
        return 1
    
    if card in ['10','J','Q','K']:
        return 0
    
    return int(card)

def hand_score(hand):
    """
    핸드(카드 리스트)의 최종 점수 계산
    (합계 % 10)

    Parameters
    ----------
    hand : TYPE
        DESCRIPTION.
    Returns
    -------
    None.

    """
    total = sum(card_value(card) for card in hand)
    return total % 10    
    
def is_natural(player_hand, banker_hand):

    """
    플레이어 또는 뱅커가 내추럴(8 or 9)인지 판단

    Parameters
    ----------
    player_hand : TYPE
        DESCRIPTION.
    banker_hand : TYPE
        DESCRIPTION.
            

    Returns True / False
    -------
    None.

    """
    
    player_score = hand_score(player_hand)
    banker_score = hand_score(banker_hand)

    return player_score in (8, 9) or banker_score in (8, 9)

def should_player_draw(player_hand):
    """
    플레이어가 3번째 카드를 뽑아야 하는지 판단

    Parameters
    ----------
    player_hand : TYPE
        DESCRIPTION.

    Returns True / False
    -------
    None.

    """
    score = hand_score(player_hand)
    return score <= 5
    
def should_banker_draw(banker_hand, player_third_card):
    """
    뱅커가 3번째 카드를 뽑아야 하는지 판단
    
    banker_hand: 뱅커의 현재 핸드 (2장 또는 3장)
    player_third_card:
      - 플레이어가 3번째 카드를 안 뽑았으면 None
    Parameters
    ----------
    player_third_card: TYPE
        - 뽑았으면 해당 카드
    
    Returns True / False
    ----------
    None.
    
    """
        
    banker_score = hand_score(banker_hand)
    
    #플레이어가 3번째 카드를 뽑지 않은 경우
    if player_third_card is None:
        return banker_score <= 5
    
    # 플레이어가 3번째 카드를 뽑은 경우 
    player_third_card_value = card_value(player_third_card)
    
    if banker_score <= 2:
        return True
    elif banker_score == 3:
        return player_third_card_value != 8
    elif banker_score == 4:
        return 2 <= player_third_card_value <= 7
    elif banker_score == 5:
        return 4 <= player_third_card_value <= 7
    elif banker_score == 6:
        return player_third_card_value in (6,7)
    else:
        #banker_score == 7
        return False
    
    
def determine_winner(player_hand,banker_hand)    :
    """
    최종 승자 판정

    Parameters
    ----------
    player_hand : TYPE
        DESCRIPTION.
    banker_hand : TYPE
        DESCRIPTION.

    Returns "PLAYER" | "BANKER" | "TIE"
    -------
    None.

    """
    
    player_score = hand_score(player_hand)
    banker_score = hand_score(banker_hand)
    
    if player_score > banker_score:
        return 'PLAYER'
    elif player_score < banker_score:
        return 'BANKER'
    else:
        return 'TIE'
    
#%%

# card_value
#    ↓
# hand_score
#    ↓
# is_natural
#    ↓
# should_player_draw
#    ↓
# should_banker_draw
#    ↓
# determine_winner

#%%    
    
    
    
    
    
    
    
    
    
    