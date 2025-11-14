# Backend/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pickle

from Helper import (
    ROWS, COLS,
    drop_koin, cek_winner, is_draw,
    pilih_aksi_ai
)

LUTS_PATH = "luts_dual.pkl"

with open(LUTS_PATH, "rb") as f:
    data = pickle.load(f)

# sesuai format save_checkpoint_dual di notebook
LUTsP1 = data["lutsP1"]
LUTsP2 = data["lutsP2"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    board: list[list[int]]  # 6x7
    player: int             # 1 atau 2


class MoveResponse(BaseModel):
    column: int      # kolom yang dipilih AI
    winner: int      # 0: belum, 1/2: pemenang, 3: seri
    is_terminal: bool


@app.post("/api/move", response_model=MoveResponse)
def get_move(req: MoveRequest):
    board_np = np.array(req.board, dtype=np.int8)
    player = req.player

    col = pilih_aksi_ai(board_np, player, LUTsP1, LUTsP2)
    if col is None:
        # tidak ada aksi legal, anggap game selesai (seri)
        return MoveResponse(column=-1, winner=3, is_terminal=True)

    board_after, row = drop_koin(board_np, col, player)
    win = cek_winner(board_after, row, col)

    if win != 0:
        return MoveResponse(column=col, winner=win, is_terminal=True)
    if is_draw(board_after):
        return MoveResponse(column=col, winner=3, is_terminal=True)

    return MoveResponse(column=col, winner=0, is_terminal=False)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
