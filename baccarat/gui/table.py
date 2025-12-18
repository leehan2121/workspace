# -*- coding: utf-8 -*-
"""
TableFrame for Baccarat Complete GUI
- Cards, Result, Message display
"""
import tkinter as tk

class TableFrame(tk.Frame):
    """
    바카라 테이블 화면(View)
    """

    def __init__(self, parent):
        super().__init__(parent, bg="#0b3d2e")

        # ===== PLAYER =====
        self.player_label = tk.Label(
            self,
            text="PLAYER",
            fg="white",
            bg="#0b3d2e",
            font=("Arial", 16, "bold")
        )
        self.player_label.pack(pady=(20, 5))

        self.player_cards = tk.Label(
            self,
            text="",
            fg="white",
            bg="#0b3d2e",
            font=("Arial", 16, "bold")
        )
        self.player_cards.pack()

        # ===== BANKER =====
        self.banker_label = tk.Label(
            self,
            text="BANKER",
            fg="white",
            bg="#0b3d2e",
            font=("Arial", 16, "bold")
        )
        self.banker_label.pack(pady=(30, 5))

        self.banker_cards = tk.Label(
            self,
            text="",
            fg="white",
            bg="#0b3d2e",
            font=("Arial", 16, "bold")
        )
        self.banker_cards.pack()

        # ===== RESULT =====
        self.result_label = tk.Label(
            self,
            text="",
            fg="yellow",
            bg="#0b3d2e",
            font=("Arial", 16, "bold")
        )
        self.result_label.pack(pady=20)

        # ===== MESSAGE =====
        self.message_label = tk.Label(
            self,
            text="",
            fg="lightgray",
            bg="#0b3d2e",
            font=("Arial", 14)
        )
        self.message_label.pack(pady=10)

    # -------------------------------------------------
    def show_cards(self, player_hand, banker_hand):
        """
        카드 표시
        player_hand, banker_hand : [(suit, rank), ...]
        """
        self.player_cards.config(text=self._format_cards(player_hand))
        self.banker_cards.config(text=self._format_cards(banker_hand))

    # -------------------------------------------------
    def show_result(self, winner, payout, player_money):
        """
        승자 및 배당 결과 표시
        """
        self.result_label.config(
            text=f"WINNER : {winner} | PAYOUT : {payout} | PLAYER MONEY : {player_money}"
        )

    # -------------------------------------------------
    def show_message(self, message):
        """
        상태 메시지 표시
        """
        self.message_label.config(text=message)

    # -------------------------------------------------
    def _format_cards(self, hand):
        """
        카드 리스트를 사람이 읽을 수 있는 문자열로 변환
        예: [('♠','A'), ('♦','9')] → "♠A  ♦9"
        """
        return "  ".join(f"{suit}{rank}" for suit, rank in hand)