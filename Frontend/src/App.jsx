import { useState, useEffect } from "react";
import "./App.css";

const ROWS = 6;
const COLS = 7;
const EMPTY_BOARD = Array.from({ length: ROWS }, () => Array(COLS).fill(0));

const API_URL = "https://connectfour-backend-production.up.railway.app";

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
  const [lastRewardType, setLastRewardType] = useState("");
  const [aiMoveHistory, setAiMoveHistory] = useState([]);

  const [useShaping, setUseShaping] = useState(true);

  useEffect(() => {
    if (!gameOver && currentPlayer === aiPlayer) {
      callAiMove();
    }
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
      setLastRewardType("");
      setAiMoveHistory([]);
      setCurrentPlayer(1);

      setStatus(
        aiAsP1 ? "AI mulai dulu (Player 1)..." : "Giliran kamu (Player 1)",
      );

      return aiAsP1;
    });
  };

  const handleColumnClick = (colIndex) => {
    if (gameOver || isAiThinking || currentPlayer !== humanPlayer) return;

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
      const res = await fetch(`${API_URL}/api/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          board,
          player: aiPlayer,
          use_shaping: useShaping,
        }),
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();

      const rewardType =
        typeof data.reward_type === "string" && data.reward_type.length > 0
          ? data.reward_type
          : useShaping
            ? "shaping"
            : "no_shaping";

      setLastQValue(typeof data.q_value === "number" ? data.q_value : null);
      setLastReward(typeof data.reward === "number" ? data.reward : null);
      setLastRewardType(rewardType);

      setAiMoveHistory((prev) =>
        [
          ...prev,
          {
            move: prev.length + 1,
            column: data.column,
            q: data.q_value,
            reward: data.reward,
            rewardType,
          },
        ].slice(-5),
      );

      const col = data.column;
      if (col < 0 || col >= COLS) {
        setStatus("AI tidak bisa bergerak.");
        setGameOver(true);
        return;
      }

      const rowIndex = findEmptyRow(board, col);
      if (rowIndex === -1) {
        setStatus("Langkah AI tidak valid.");
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
        } else {
          setStatus("Seri!");
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
                        <div className={`disc player-${cell}`} />
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
          </div>
        </div>
      </div>
    </div>
  );
}

function findEmptyRow(board, col) {
  for (let r = ROWS - 1; r >= 0; r--) {
    if (board[r][col] === 0) return r;
  }
  return -1;
}

function checkWinner(board, lastRow, lastCol) {
  const player = board[lastRow][lastCol];
  if (!player) return 0;

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
