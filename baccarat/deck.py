# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 14:14:11 2025

@author: hyunilPark , leehan2121@gmail.com
"""

# ✔ 카드 생성
# ✔ 셔플
# ✔ 카드 한 장 제공

import random

class Deck:
       
    """
    Deck 클래스
    
    역할: 
        - 4 / 6 / 8 /덱을 받아서 카드 풀을 생성
        - 카드 순서를 섞음
        - 카드 한 장을 뽑아 제공
        
        return  
    
    ----------
    deck : Deck
        카드 덱 객체
    
    Returns
    -------
    result : str
        'PLAYER' | 'BANKER' | 'TIE'
    player_hand : list
        플레이어 카드 목록
    banker_hand : list
        뱅커 카드 목록
    last_round : bool
        이번 판이 덱의 마지막 판인지 여부
    """
    
    def __init__(self , num_decks=8) :
        
        """
        생성자
            Parameters
        ----------
        num_decks : int
            사용할 덱 개수 (보통 4, 6, 8)
    
        내부 동작
        ----------
        1. 카드 풀 생성
        2. 셔플 수행
    
        주의:
        - 덱 생성과 셔플은 자동으로 일어난다
        - game.py에서는 바로 draw()만 호출하면 된다
        """
        self.num_decks = num_decks  #   덱 개수 저장
        self.cards = []             #   실제 카드가 담길 리스트
        
        self._build_deck()           #   카드 풀 생성
        self.shuffle()              #   생성 직후 바로 섞기
        
    def _build_deck(self):
        """
        카드 풀 생성 (내부 전용 메서드)
        
        - 외부에서 호출하지 않는다
        - 생성자에서만 사용
        
        구성:
        - 카드 종류 13개
        - 각 카드당 4장
        - num_decks 만큼 반복
        
        반환값 없음
        결과는 self.cards 에 저장된다
        
        # 8덱 → 416
        # 6덱 → 312
        # 4덱 → 208
        """    
        card_types = ['A' ,'2','3','4','5','6','7','8','9','10','J','Q','K']
          
        self.cards = []
          
         
        for _ in range(self.num_decks):
            for card in card_types:
                for _ in range(4):
                    self.cards.append(card)
    
    
    def shuffle(self):
    
        """
        카드 섞기
        
        - 현재 self.cards 리스트를 무작위로 섞는다
        - random.shuffle 사용
        - 반환값 없음 (in-place 변경)
        
        주의
        ----
        - 반드시 카드가 생성된 이후에만 호출해야 한다
        - 덱 상태만 변경하고, 게임 규칙은 전혀 모른다
        """
    
        random.shuffle(self.cards)
                      
        
          
    def draw(self):
        
        """
        카드 한 장 뽑기
        
        Returns
        -------
        card : str
            카드 한 장 ('A', '7', 'K' 등)
        
        주의:
        - 덱이 비었을 경우 예외 처리 필요
        - pop() 사용 → 덱의 상태가 줄어든다
        
        이 메서드는 게임의 모든 흐름의 시작점이다.
        """      
        if not self.cards:
            raise RuntimeError("덱에 카드가 없습니다.")
            
        return self.cards.pop()
        
    def remaining_cards(self):
        """
        카드가 6장 남았을 경우를 체크하기 위해 length 함수를 추가함
    
        Returns
        -------
        TYPE
            DESCRIPTION.
    
        """
        
        return len(self.cards)