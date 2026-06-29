#!/bin/bash

SESSION_NAME="trading"

# Kill session if it already exists
tmux kill-session -t "$SESSION_NAME" 2>/dev/null

echo "Starting tmux session: $SESSION_NAME"

# Create the session and the first window (SUNPHARMA)
tmux new-session -d -s "$SESSION_NAME" -n "SUNPHARMA"

# Create windows for the remaining symbols
tmux new-window -t "$SESSION_NAME" -n "TRENT"
tmux new-window -t "$SESSION_NAME" -n "INFY"
tmux new-window -t "$SESSION_NAME" -n "ASIANPAINT"
tmux new-window -t "$SESSION_NAME" -n "HDFCBANK"

# Launch the live runners in each window
symbols=("SUNPHARMA" "TRENT" "INFY" "ASIANPAINT" "HDFCBANK")

for symbol in "${symbols[@]}"; do
    echo "Launching runner for $symbol in tmux window $symbol..."
    tmux send-keys -t "${SESSION_NAME}:${symbol}" "source venv/bin/activate" C-m
    tmux send-keys -t "${SESSION_NAME}:${symbol}" "python Src/liveTrading_runner.py --symbol $symbol" C-m
done

echo "Tmux session '$SESSION_NAME' initialized successfully."
echo "Use 'tmux attach -t $SESSION_NAME' to view the running sessions."
