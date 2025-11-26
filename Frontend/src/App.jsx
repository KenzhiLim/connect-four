import { useState, useEffect } from "react";
import "./App.css";

const ROWS = 6;
const COLS = 7;
const EMPTY_BOARD = Array.from({ length: ROWS }, () => Array(COLS).fill(0));

function App() {
  const [board, setBoard] = useState(EMPTY_BOARD);
  const [currentPlayer, setCurrentPlayer] = useState(1);
  const [aiPlayer, setAiPlayer] = useState(2);
  const [humanPlayer, setHumanPlayer] = useState(1);
  const [status, setStatus] = useState("Giliran kamu (Player 1)");
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [aiStartsNext, setAiStartsNext] = useState(true);

  const [lastQValue, setLastQValue] = useState(null);
  const [lastReward, setLastReward] = useState(null);
  const [aiMoveHistory, setAiMoveHistory] = useState([]);
  const [lastRewardType, setLastRewardType] = useState("");

  const [useShaping, setUseShaping] = useState(true);

  useEffect(() => {
    if (!gameOver && currentPlayer === aiPlayer) {
      callAiMove();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPlayer, aiPlayer, gameOver]);

  const resetGame = () => {
    setAiStartsNext((prev) => {
      const aiAsP1 = !prev;
      const newAiPlayer = aiAsP1 ? 1 : 2;
      const newHumanPlayer = aiAsP1 ? 2 : 1;

      setAiPlayer(newAiPlayer);
      setHumanPlayer(newHumanPlayer);

      setBoard(EMPTY_BOARD);
      setGameOver(false);
      setIsAiThinking(false);
      setLastQValue(null);
      setLastReward(null);
      setAiMoveHistory([]);

      setCurrentPlayer(1);
      if (aiAsP1) {
        setStatus("AI mulai dulu (Player 1)...");
      } else {
        setStatus("Giliran kamu (Player 1)");
      }

      return aiAsP1;
    });
  };

  const handleColumnClick = (colIndex) => {
    if (gameOver || isAiThinking) return;
    if (currentPlayer !== humanPlayer) return;

    const rowIndex = findEmptyRow(board, colIndex);
    if (rowIndex === -1) return;

    const newBoard = board.map((row) => [...row]);
    newBoard[rowIndex][colIndex] = humanPlayer;
    setBoard(newBoard);

    const winner = checkWinner(newBoard, rowIndex, colIndex);
    if (winner === humanPlayer) {
      setStatus("Kamu menang!");
      setGameOver(true);
      return;
    }

    if (isDraw(newBoard)) {
      setStatus("Seri!");
      setGameOver(true);
      return;
    }

    setCurrentPlayer(aiPlayer);
    setStatus(`Giliran AI (Player ${aiPlayer})...`);
  };

  const callAiMove = async () => {
    setIsAiThinking(true);
    try {
      const res = await fetch("http://localhost:8000/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          board: board,
          player: aiPlayer,
          use_shaping: useShaping,
        }),
      });

      const data = await res.json();
      const rewardType =
        typeof data.reward_type === "string" && data.reward_type.length > 0
          ? data.reward_type
          : useShaping
          ? "shaping"
          : "no_shaping";

      // simpan q dan reward
      setLastQValue(typeof data.q_value === "number" ? data.q_value : null);
      setLastReward(typeof data.reward === "number" ? data.reward : null);
      setLastRewardType(rewardType);

      const col = data.column;

      // simpan q dan reward
      setLastQValue(typeof data.q_value === "number" ? data.q_value : null);
      setLastReward(typeof data.reward === "number" ? data.reward : null);

      setAiMoveHistory((prev) => {
        const next = [
          ...prev,
          {
            move: prev.length + 1,
            column: data.column,
            q: data.q_value,
            reward: data.reward,
            mode: useShaping ? "shaping" : "no-shaping",
            rewardType: rewardType,
          },
        ];
        return next.slice(-5);
      });

      if (col < 0 || col >= COLS) {
        setStatus("AI tidak bisa bergerak (game over).");
        setGameOver(true);
        return;
      }

      const rowIndex = findEmptyRow(board, col);
      if (rowIndex === -1) {
        setStatus("Langkah AI tidak valid (kolom penuh).");
        setGameOver(true);
        return;
      }

      const newBoard = board.map((row) => [...row]);
      newBoard[rowIndex][col] = aiPlayer;
      setBoard(newBoard);

      if (data.is_terminal) {
        if (data.winner === aiPlayer) {
          setStatus("AI menang.");
        } else if (data.winner === humanPlayer) {
          setStatus("Kamu menang!");
        } else if (data.winner === 3) {
          setStatus("Seri!");
        } else {
          setStatus("Game selesai.");
        }
        setGameOver(true);
      } else {
        setCurrentPlayer(humanPlayer);
        setStatus(`Giliran kamu (Player ${humanPlayer})`);
      }
    } catch (err) {
      console.error(err);
      setStatus("Gagal memanggil AI. Cek server backend.");
    } finally {
      setIsAiThinking(false);
    }
  };

  return (
    <div className="app">
      <div className="app-inner">
        <header className="header">
          <h1>Connect Four vs LUT Agent</h1>
          <p className="status">{status}</p>

          <div className="mode-switch">
            <span>Mode LUT:&nbsp;</span>
            <button
              className={useShaping ? "mode-btn active" : "mode-btn"}
              onClick={() => setUseShaping(true)}
              disabled={isAiThinking}
            >
              Dengan Reward Shaping
            </button>
            <button
              className={!useShaping ? "mode-btn active" : "mode-btn"}
              onClick={() => setUseShaping(false)}
              disabled={isAiThinking}
            >
              Tanpa Reward Shaping
            </button>
          </div>
        </header>

        {/* CONTENT: board + side panel */}
        <div className="content">
          <div className="board-area">
            <div className="board-wrapper">
              <div className="board">
                {board.map((row, rIdx) => (
                  <div className="board-row" key={rIdx}>
                    {row.map((cell, cIdx) => (
                      <div
                        key={cIdx}
                        className="cell"
                        onClick={() => handleColumnClick(cIdx)}
                      >
                        <div className={`disc player-${cell}`}></div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            <div className="controls">
              <button onClick={resetGame}>Reset</button>
              {isAiThinking && (
                <span className="thinking">AI sedang berpikir...</span>
              )}
            </div>

            <div className="legend">
              <div className="legend-item">
                <div className="legend-circle yellow"></div>
                {humanPlayer === 1 ? "Kamu (Player 1)" : "AI (Player 1)"}
              </div>
              <div className="legend-item">
                <div className="legend-circle red"></div>
                {aiPlayer === 2 ? "AI (Player 2)" : "Kamu (Player 2)"}
              </div>
            </div>
          </div>

          {/* PANEL DI SAMPING BOARD */}
          <aside className="side-panel">
            <div className="monitor">
              <h3>Monitoring Langkah AI</h3>
              <p>
                Mode aktif:&nbsp;
                <strong>
                  {useShaping
                    ? "Dengan reward shaping"
                    : "Tanpa reward shaping"}
                </strong>
              </p>

              {lastQValue !== null && (
                <p>Q-value langkah terakhir: {lastQValue.toFixed(3)}</p>
              )}
              {lastReward !== null && (
                <p>
                  Reward langkah terakhir: {lastReward.toFixed(3)}{" "}
                  {lastRewardType && <span>({lastRewardType})</span>}
                </p>
              )}

              {aiMoveHistory.length > 0 && (
                <table className="monitor-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Kolom</th>
                      <th>Q</th>
                      <th>R</th>
                      <th>Jenis Reward</th>
                    </tr>
                  </thead>
                  <tbody>
                    {aiMoveHistory.map((m) => (
                      <tr key={m.move}>
                        <td>{m.move}</td>
                        <td>{m.column}</td>
                        <td>
                          {typeof m.q === "number" ? m.q.toFixed(3) : "—"}
                        </td>
                        <td>
                          {typeof m.reward === "number"
                            ? m.reward.toFixed(3)
                            : "—"}
                        </td>
                        <td>{m.rewardType || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

// ===== Helper di frontend =====

function findEmptyRow(board, col) {
  for (let r = ROWS - 1; r >= 0; r--) {
    if (board[r][col] === 0) return r;
  }
  return -1;
}

function checkWinner(board, lastRow, lastCol) {
  const player = board[lastRow][lastCol];
  if (player === 0) return 0;

  const dirs = [
    [1, 0],
    [0, 1],
    [1, 1],
    [1, -1],
  ];

  for (const [dr, dc] of dirs) {
    let count = 1;

    let r = lastRow + dr;
    let c = lastCol + dc;
    while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
      count++;
      r += dr;
      c += dc;
    }

    r = lastRow - dr;
    c = lastCol - dc;
    while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
      count++;
      r -= dr;
      c -= dc;
    }

    if (count >= 4) return player;
  }

  return 0;
}

function isDraw(board) {
  return board[0].every((v) => v !== 0);
}

export default App;
