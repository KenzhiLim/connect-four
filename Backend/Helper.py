import random
import numpy as np
import math

# HYPERPARAMETER UTAMA
ROWS, COLS = 6, 7
P = 4
N_TUP = 8
M_TUP = 70
SEED = 42

# RNG
rng = random.Random(SEED)
np.random.seed(SEED)

# ENVIRONMENT


def empty_board():
    # Papan kosong
    return np.zeros((ROWS, COLS), dtype=np.int8)


def cek_legal(board):
    # Kolom yang masih bisa diisi
    return [c for c in range(COLS) if board[0, c] == 0]


def drop_koin(board, col, player):
    assert board[0, col] == 0
    newBoard = board.copy()
    for r in range(ROWS - 1, -1, -1):
        if newBoard[r, col] == 0:
            newBoard[r, col] = player
            return newBoard, r
    raise RuntimeError("Kolom penuh")


def cek_winner(board, r, c):
    # Periksa apakah ada pola garis terbentuk dari langkah terakhir
    target = board[r, c]
    if target == 0:
        return 0
    arah = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in arah:
        count = 1
        for delta in (+1, -1):
            rr, cc = r + delta * dr, c + delta * dc
            while 0 <= rr < ROWS and 0 <= cc < COLS and board[rr, cc] == target:
                count += 1
                rr += delta * dr
                cc += delta * dc
        if count >= 4:
            return target
    return 0


def is_draw(board):
    # Seri kalau baris paling atas penuh semua
    return np.all(board[0, :] != 0)


def mirror_col(c):
    return COLS - 1 - c


def mirror_board(board):
    return np.flip(board, axis=1)


def is_immediate_win(board, col, player):
    acts = cek_legal(board)
    if col not in acts:
        return False
    board_after, row = drop_koin(board, col, player)
    return cek_winner(board_after, row, col) == player


def count_immediate_wins(board, player):
    count = 0
    acts = cek_legal(board)
    for c in acts:
        if is_immediate_win(board, c, player):
            count += 1
    return count


# N-TUPLE
def random_tuples(m=M_TUP, n=N_TUP, _rng=rng):
    # Buat M buah tuple sepanjang N yang mencatat koordinat random pada papan
    coordinates = [(r, c) for r in range(ROWS) for c in range(COLS)]
    return [tuple(_rng.sample(coordinates, n)) for _ in range(m)]


# TUPLES sama persis seperti training (seed & rng sama)
TUPLES = random_tuples()

# Mirror tuples (gunakan mirror_col dari environment)
MIRROR_TUPLES = [tuple((r, mirror_col(c)) for (r, c) in tc) for tc in TUPLES]

# Pangkat P untuk encoding indeks LUT
POW_P = np.array([P ** i for i in range(N_TUP)], dtype=np.int64)


def hitung_index(board, tuple_coordinates):
    vals = [int(board[r, c]) for (r, c) in tuple_coordinates]
    return int(np.dot(vals, POW_P))


# LUT VALUE FUNCTION
def q_afterstate(board_after, luts):
    s = 0.0
    for i, tc in enumerate(TUPLES):
        k = hitung_index(board_after, tc)
        km = hitung_index(board_after, MIRROR_TUPLES[i])
        s += luts[i][k] + luts[i][km]
    return float(s)


def best_action_greedy(board, luts_active, player):
    acts = cek_legal(board)
    if not acts:
        return None

    best_col = None
    best_q = float("-inf")

    for col in acts:
        board_after, row = drop_koin(board, col, player)
        qSa = q_afterstate(board_after, luts_active)
        if qSa > best_q:
            best_q = qSa
            best_col = col

    return best_col


def best_action_greedy2(board, luts_active, player):
    acts = cek_legal(board)
    if not acts:
        return None

    opp = 2 if player == 1 else 1
    threat_cols = [c for c in acts if is_immediate_win(board, c, opp)]

    if threat_cols:
        best_col = None
        best_q = float("-inf")
        for col in threat_cols:
            board_after, row = drop_koin(board, col, player)
            qSa = q_afterstate(board_after, luts_active)
            if qSa > best_q:
                best_q = qSa
                best_col = col
        return best_col

    return best_action_greedy(board, luts_active, player)


def pilih_aksi_ai(board, player, LUTsP1, LUTsP2, use_threat_rule=False):
    luts_active = LUTsP1 if player == 1 else LUTsP2

    if use_threat_rule:
        return best_action_greedy2(board, luts_active, player)
    else:
        return best_action_greedy(board, luts_active, player)


# REWARD SHAPING
# Anneal & clip
SHAPING_T_ANNEAL = 3_000_000
SHAPING_CLIP = 0.30

# Bobot fitur
W_CENTER_START = 0.06
W_BLOCK_THREAT = 0.10
W_PERFECT_PLAY = 0.06
W_SECOND_EDGE = 0.04
W_PARITY = 0.04
W_FORK = 0.12

USE_SHAPING = True
episodesTrained = 0


def shaping_scale_cos(step):
    if step is None or step <= 0:
        return 1.0
    if step >= SHAPING_T_ANNEAL:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * step / SHAPING_T_ANNEAL))


def get_opponent(p):
    return 2 if p == 1 else 1


def reward_shaping_detail(board, action_col, player):
    if not globals().get("USE_SHAPING", True):
        return 0.0, []

    acts = cek_legal(board)
    if action_col not in acts:
        return 0.0, []

    after, rLanding = drop_koin(board, action_col, player)

    # TERMINAL? → jangan beri shaping
    if cek_winner(after, rLanding, action_col) != 0 or is_draw(after):
        return 0.0, []

    opp = get_opponent(player)
    reward = 0.0
    kinds = []

    # 1) Center start
    if np.count_nonzero(board) == 0 and action_col == (COLS // 2):
        reward += W_CENTER_START
        kinds.append("CENTER_START")

    # 2) Block 1-step threat lawan
    opp_before = count_immediate_wins(board, opp)
    if opp_before > 0 and count_immediate_wins(after, opp) == 0:
        reward += W_BLOCK_THREAT
        kinds.append("BLOCK_THREAT")

    # 3) Perfect-play heuristic
    my_before = count_immediate_wins(board, player)
    my_after = count_immediate_wins(after, player)
    if opp_before > 0 and count_immediate_wins(after, opp) == 0 and my_after > my_before:
        reward += W_PERFECT_PLAY
        kinds.append("PERFECT_PLAY")

    # 4) Koin kedua di ujung
    if np.count_nonzero(board == player) == 1 and (action_col in (0, COLS - 1)):
        reward += W_SECOND_EDGE
        kinds.append("SECOND_EDGE")

    # 5) Parity
    dist = (ROWS - 1) - rLanding
    preferred_parity = 0 if player == 1 else 1
    if (dist % 2) == preferred_parity:
        reward += W_PARITY
        kinds.append("PARITY")

    # 6) Fork
    winNext = sum(
        1 for c in cek_legal(after)
        if is_immediate_win(after, c, player)
    )
    if winNext >= 2:
        reward += W_FORK
        kinds.append("FORK")

    # Anneal + clip
    step = globals().get("episodesTrained", 0)
    scale = shaping_scale_cos(step)
    shaped = reward * scale
    if shaped > SHAPING_CLIP:
        shaped = SHAPING_CLIP
    if shaped < -SHAPING_CLIP:
        shaped = -SHAPING_CLIP

    return shaped, kinds


def reward_shaping(board, action_col, player):
    shaped, _ = reward_shaping_detail(board, action_col, player)
    return shaped
