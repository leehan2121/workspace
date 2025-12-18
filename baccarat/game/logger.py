# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 09:37:03 2025

@author: hyunilPark
"""

import csv
import os
from datetime import datetime

class GameLogger:
    def __init__(self):
        """
        logs/baccarat_YYYY_MM_DD.csv 형태로 로그 생성
        """
        base_dir = os.path.dirname(os.path.dirname(__file__))  # baccarat/
        logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y_%m_%d")
        self.filename = os.path.join(
            logs_dir, f"baccarat_{date_str}.csv"
        )
        
        self._init_file()
    def _init_file(self):
        """
        파일 없으면 헤더 생성
        """
        
        if not os.path.exists(self.filename):
            with open(self.filename, "w" , newline="" , encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "round",
                    "bet_type",
                    "bet_amount",
                    "winner",
                    "payout",
                    "player_score",
                    "banker_score",
                    "player_hand",
                    "banker_hand",
                    "player_money",
                    "casino_money",
                    "natural",
                    "last_round"
                    ])
                
    def log_round(self , round_no , bet_type , bet_amount , result , bankroll):
        """
        한 판 로그 기록
        """
        with open(self.filename , mode="a" , newline="",encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                round_no,
                bet_type,
                bet_amount,
                result["winner"],
                result["payout"],
                result.get("player_score"),
                result.get("banker_score"),
                " ".join(f"{suit}{rank}" for suit, rank in result["player_hand"]),
                " ".join(f"{suit}{rank}" for suit, rank in result["banker_hand"]),
                bankroll.player_money,
                bankroll.casino_money,
                result["natural"],
                result["last_round"]
                ])
                