import random
import numpy as np

# ============================================================
# HYPERPARAMETER UTAMA (diambil dari notebook)
# ============================================================
ROWS, COLS = 6, 7
P = 4
N_TUP = 8
M_TUP = 70
SEED = 42

# RNG sama seperti di notebook
rng = random.Random(SEED)
np.random.seed(SEED)

# ============================================================
# ENVIRONMENT (diambil dari sel Environment di notebook + snippet kamu)
# ============================================================


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

# ============================================================
# N-TUPLE (diambil dari sel N-Tuple di notebook)
# ============================================================


def random_tuples(m=M_TUP, n=N_TUP, _rng=rng):
    # Buat M buah tuple sepanjang N yang mencatat koordinat random pada papan
    coordinates = [(r, c) for r in range(ROWS) for c in range(COLS)]
    return [tuple(rng.sample(coordinates, n)) for _ in range(m)]


# TUPLES sama persis seperti training (seed & rng sama)
TUPLES = random_tuples()

# Mirror tuples (gunakan mirror_col dari environment)
MIRROR_TUPLES = [tuple((r, mirror_col(c)) for (r, c) in tc) for tc in TUPLES]

# Pangkat P untuk encoding indeks LUT
POW_P = np.array([P ** i for i in range(N_TUP)], dtype=np.int64)


def hitung_index(board, tuple_coordinates):
    vals = [int(board[r, c]) for (r, c) in tuple_coordinates]
    return int(np.dot(vals, POW_P))

# ============================================================
# LUT VALUE FUNCTION (diambil dari sel LUT di notebook)
# ============================================================


def q_afterstate(board_after, luts):
    """
    Menghitung nilai afterstate menggunakan N-tuple LUT.
    - board_after : papan setelah aksi (numpy array 6x7)
    - luts        : list LUT untuk satu pemain (misal LUTsP1 atau LUTsP2)
                    bentuknya: list panjang M_TUP, tiap elemen array size P**N_TUP
    """
    s = 0.0
    for i, tc in enumerate(TUPLES):
        k = hitung_index(board_after, tc)
        km = hitung_index(board_after, MIRROR_TUPLES[i])
        s += luts[i][k] + luts[i][km]
    return float(s)

# ============================================================
# POLICY: PILIH AKSI TERBAIK DARI LUT
# ============================================================


def best_action_from_luts(board, luts_active, player):
    """
    Memilih kolom terbaik untuk 'player' menggunakan LUT aktif (luts_active).
    - board: papan saat ini (numpy array 6x7)
    - luts_active: LUTsP1 atau LUTsP2 (untuk satu pemain)
    - player: 1 atau 2
    """
    acts = cek_legal(board)
    if not acts:
        return None  # tidak ada aksi legal

    best_col = None
    best_q = float("-inf")

    for col in acts:
        board_after, row = drop_koin(board, col, player)
        qSa = q_afterstate(board_after, luts_active)
        if qSa > best_q:
            best_q = qSa
            best_col = col

    return best_col


def pilih_aksi_ai(board, player, LUTsP1, LUTsP2):
    """
    Wrapper praktis untuk dipanggil dari server.py

    Parameters
    ----------
    board : numpy array 6x7 (isi 0/1/2)
    player : int
        Pemain yang sedang bergerak (1 atau 2, biasanya 2 = AI)
    LUTsP1, LUTsP2 : list of np.ndarray
        Diambil dari checkpoint luts_dual.pkl:
          data["lutsP1"], data["lutsP2"]

    Returns
    -------
    col : int atau None
        Kolom yang dipilih AI (0..6), atau None kalau tidak ada aksi legal.
    """
    luts_active = LUTsP1 if player == 1 else LUTsP2
    return best_action_from_luts(board, luts_active, player)
