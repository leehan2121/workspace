# -*- coding: utf-8 -*-
"""
Baccarat Complete GUI App
- Full functionality: bet, cards, result, bankroll, logs, deck reset
"""
import tkinter as tk
from tkinter import messagebox, ttk
import csv
import os
from game.deck import Deck
from game.bankroll import Bankroll
from game.game import play_round
from game.logger import GameLogger
from gui.table import TableFrame

class BaccaratApp:
    def __init__(self):
        # ===== Tk 루트 =====
        self.root = tk.Tk()
        self.root.title("Baccarat Complete Casino")
        self.root.geometry("1000x700")

        # ===== 게임 상태 =====
        self.deck = Deck()
        self.bankroll = Bankroll(player_money=100_000, casino_money=100_000)
        self.logger = GameLogger()
        self.round_no = 1
        self.bet_type = None
        self.bet_amount = 1000

        # ===== 테이블 UI =====
        self.table = TableFrame(self.root)
        self.table.pack(fill="both", expand=True)

        # ===== 잔액 표시 =====
        self.balance_label = tk.Label(self.root, text=self.get_balance_text(), font=("Arial", 12, "bold"))
        self.balance_label.pack(pady=5)

        # ===== 컨트롤 버튼 =====
        self._create_controls()

        # ===== 로그 확인 버튼 =====
        tk.Button(self.root, text="Show Last 10 Rounds", command=lambda: self.show_logs(all_logs=False)).pack(pady=5)
        tk.Button(self.root, text="Show All Logs", command=lambda: self.show_logs(all_logs=True)).pack(pady=5)

    # -------------------------------------------------
    def get_balance_text(self):
        return f"PLAYER MONEY: {self.bankroll.player_money}  |  CASINO MONEY: {self.bankroll.casino_money}"

    # -------------------------------------------------
    def _create_controls(self):
        control = tk.Frame(self.root)
        control.pack(pady=10)

        # 베팅 대상 버튼
        tk.Button(control, text="PLAYER", width=12, command=lambda: self.select_bet("PLAYER")).pack(side="left", padx=5)
        tk.Button(control, text="BANKER", width=12, command=lambda: self.select_bet("BANKER")).pack(side="left", padx=5)
        tk.Button(control, text="TIE", width=12, command=lambda: self.select_bet("TIE")).pack(side="left", padx=5)

        # 베팅 금액 Entry
        tk.Label(control, text="BET AMOUNT:").pack(side="left", padx=5)
        self.bet_entry = tk.Entry(control, width=12)
        self.bet_entry.insert(0, "1000")
        self.bet_entry.pack(side="left", padx=5)

        # 베팅 금액 설정
        tk.Button(control, text="SET BET", command=self.set_bet_amount).pack(side="left", padx=5)

        # 게임 실행
        tk.Button(control, text="PLAY", width=12, bg="#444", fg="white", command=self.play_game).pack(side="left", padx=20)

    # -------------------------------------------------
    def set_bet_amount(self):
        try:
            amount = int(self.bet_entry.get())
            if amount < 1000:
                raise ValueError
            if amount > self.bankroll.player_money:
                raise ValueError
            self.bet_amount = amount
            self.table.show_message(f"BET AMOUNT SET → {self.bet_amount}")
        except ValueError:
            messagebox.showwarning("경고", "올바른 금액을 입력하세요 (1,000 이상, 잔액 이하)")

    # -------------------------------------------------
    def select_bet(self, bet_type):
        self.bet_type = bet_type
        self.table.show_message(f"BET → {bet_type} / AMOUNT → {self.bet_amount}")

    # -------------------------------------------------
    def play_game(self):
        if not self.bet_type:
            messagebox.showwarning("경고", "베팅을 먼저 선택하세요")
            return

        # 덱 자동 리셋
        if self.deck.remaining_cards() < 6:
            self.deck = Deck()
            messagebox.showinfo("Deck Reset", "카드가 부족하여 새 덱으로 리셋되었습니다!")

        # 잔액 체크
        if self.bet_amount > self.bankroll.player_money:
            messagebox.showwarning("경고", "잔액이 부족합니다")
            return
        self.bankroll.player_money -= self.bet_amount

        # 게임 실행
        result = play_round(
            round_no=self.round_no,
            deck=self.deck,
            bet_type=self.bet_type,
            bet_amount=self.bet_amount,
            bankroll=self.bankroll
        )

        # 카드 UI 표시
        self.table.show_cards(result["player_hand"], result["banker_hand"])
        self.table.show_result(result["winner"], result["payout"], self.bankroll.player_money)

        # 잔액 갱신
        self.balance_label.config(text=self.get_balance_text())

        # 다음 라운드 준비
        self.round_no += 1
        self.bet_type = None

    # -------------------------------------------------
    def show_logs(self, all_logs=False):
        logs_file = self.logger.filename
        if not os.path.exists(logs_file):
            messagebox.showinfo("Logs", "로그 파일이 존재하지 않습니다.")
            return

        with open(logs_file, newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            headers = reader[0]
            rows = reader[1:]  # 헤더 제외
            rows = rows if all_logs else rows[-10:]

        # 새로운 창에 표시
        log_window = tk.Toplevel(self.root)
        log_window.title("Baccarat Logs")
        tree = ttk.Treeview(log_window, columns=headers, show="headings")
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, width=90, anchor="center")
        tree.pack(fill="both", expand=True)

        for row in rows:
            tree.insert("", "end", values=row)

    # -------------------------------------------------
    def run(self):
        self.root.mainloop()


# ---------------- 실행 ----------------
if __name__ == "__main__":
    app = BaccaratApp()
    app.run()