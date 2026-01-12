import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import os
import logging

logger = logging.getLogger(__name__)

class DQN(nn.Module):
    def __init__(self, input_dim=5, output_dim=3):
        super(DQN, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim) 
        )
        
    def forward(self, x):
        return self.fc(x)

class RLExecutionAgent:
    """
    Reinforcement Learning Agent for Optimal Execution.
    Action Space:
    0: WAIT (Do nothing)
    1: MARKET (Execute Immediately)
    2: LIMIT (Place Passive Order) - Simplified in V4 as 'Wait for better price'
    
    State Space (Input):
    [Z-Score, Quantformer Prob, OFI, Volatility Ratio, Time Held]
    """
    def __init__(self, state_dim=5, action_dim=3, lr=0.001, epsilon=0.1):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
        
        self.policy_net = DQN(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.epsilon = epsilon
        
        self.model_path = "AI/v4_rl_agent.pth"

    def get_action(self, state):
        """
        Epsilon-Greedy Policy.
        state: np.array of shape (5,)
        """
        if random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        self.policy_net.eval()
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()

    def update(self, state, action, reward, next_state, done):
        """
        Single step Q-Learning update (Simplified for Online Learning).
        """
        self.policy_net.train()
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0).to(self.device)
        action_tensor = torch.LongTensor([action]).to(self.device)
        reward_tensor = torch.FloatTensor([reward]).to(self.device)
        
        # Current Q
        q_value = self.policy_net(state_tensor).gather(1, action_tensor.unsqueeze(1))
        
        # Next Q
        next_q_value = self.policy_net(next_state_tensor).max(1)[0].detach()
        expected_q_value = reward_tensor + (0.99 * next_q_value * (1 - int(done)))
        
        loss = nn.MSELoss()(q_value, expected_q_value.unsqueeze(1))
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()

    def save(self):
        torch.save(self.policy_net.state_dict(), self.model_path)
        
    def load(self):
        if os.path.exists(self.model_path):
            self.policy_net.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.policy_net.eval()
            logger.info("RL Agent Loaded.")
        else:
            logger.warning("RL Agent model not found. Starting fresh.")
