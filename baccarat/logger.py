# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 09:37:03 2025

@author: hyunilPark
"""

import csv
import os
from datetime import datetime

class GameLogger:
    def __init__(self , base_filename="baccarat_log.csv"):
        """
        날짜별 csv 로그파일 생성
        ex : baccarat_2025_12_16.csv
        """
        date_str = datetime.now().strftime("%Y_%m_%d")
        self.filename = f"{base_filename}_{date_str}.csv"
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
                    "banker_money",
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
                " ".join(result["player_hand"]),
                " ".join(result["banker_hand"]),
                bankroll.player_money,
                bankroll.banker_money,
                result["natural"],
                result["last_round"]
                ])
                