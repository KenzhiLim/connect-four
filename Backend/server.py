from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pickle

from Helper import (
    ROWS, COLS,
    drop_koin, cek_winner, is_draw,
    pilih_aksi_ai, q_afterstate,
    reward_shaping_detail,
)

# Load LUT

LUTS_SHAPING_PATH = "luts_dual_shaping.pkl"
LUTS_NO_SHAPING_PATH = "luts_dual_no_shaping.pkl"

with open(LUTS_SHAPING_PATH, "rb") as f:
    data_shaping = pickle.load(f)
LUTsP1_SHAPING = data_shaping["lutsP1"]
LUTsP2_SHAPING = data_shaping["lutsP2"]

with open(LUTS_NO_SHAPING_PATH, "rb") as f:
    data_no_shaping = pickle.load(f)
LUTsP1_NO_SHAPING = data_no_shaping["lutsP1"]
LUTsP2_NO_SHAPING = data_no_shaping["lutsP2"]

# ------------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    board: list[list[int]]
    player: int
    use_shaping: bool = True


class MoveResponse(BaseModel):
    column: int
    winner: int
    is_terminal: bool
    q_value: float
    reward: float
    reward_type: str


@app.post("/api/move", response_model=MoveResponse)
def get_move(req: MoveRequest):
    board_np = np.array(req.board, dtype=np.int8)
    player = req.player

    if req.use_shaping:
        LUTsP1 = LUTsP1_SHAPING
        LUTsP2 = LUTsP2_SHAPING
    else:
        LUTsP1 = LUTsP1_NO_SHAPING
        LUTsP2 = LUTsP2_NO_SHAPING

    col = pilih_aksi_ai(
    board_np,
    player,
    LUTsP1,
    LUTsP2,
    use_threat_rule=req.use_shaping,
)

    if col is None:
        return MoveResponse(
            column=-1,
            winner=3,
            is_terminal=True,
            q_value=0.0,
            reward=0.0,
            reward_type="no_move",
        )

    board_after, row = drop_koin(board_np, col, player)
    win = cek_winner(board_after, row, col)

    luts_active = LUTsP1 if player == 1 else LUTsP2
    q_value = q_afterstate(board_after, luts_active)

    # Hitung reward
    terminal_reward = 1.0 if win != 0 else 0.0

    shaping = 0.0
    kinds = []
    if req.use_shaping:
        shaping, kinds = reward_shaping_detail(board_np, col, player)

    total_reward = terminal_reward + shaping

    # bentuk string jenis reward
    if req.use_shaping:
        if kinds:
            reward_type = "shaping: " + " + ".join(kinds)
        else:
            reward_type = "shaping: none"
    else:
        reward_type = "no_shaping"

    # terminal?
    if win != 0:
        return MoveResponse(
            column=col,
            winner=win,
            is_terminal=True,
            q_value=q_value,
            reward=total_reward,
            reward_type=reward_type if total_reward != 0 else "terminal_win",
        )

    if is_draw(board_after):
        return MoveResponse(
            column=col,
            winner=3,
            is_terminal=True,
            q_value=q_value,
            reward=total_reward,
            reward_type=reward_type if total_reward != 0 else "draw",
        )

    # non-terminal
    return MoveResponse(
        column=col,
        winner=0,
        is_terminal=False,
        q_value=q_value,
        reward=total_reward,
        reward_type=reward_type,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
