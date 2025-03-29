import math

class BKTEngine:
    def __init__(self, p_init=0.2, p_transit=0.3, p_slip=0.1, p_guess=0.1, p_lapse=0.3):
        self.p_init = p_init
        self.p_transit = p_transit
        self.p_slip = p_slip
        self.p_guess = p_guess
        self.p_lapse = p_lapse
        self.consecutive_correct = 0  # Track consecutive correct answers

    def predict(self, current_knowledge: float) -> float:
        """
        Predict the probability of knowing the skill after a learning opportunity.
        Modified to provide extremely slow progression at all levels.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            
        Returns:
            float: Predicted probability of knowing the skill
        """
        # Even stronger global learning rate reduction - apply a more aggressive slow-down factor
        global_slowdown = 0.1  # Reduce all learning by 90%
        
        # Add a damping factor for high knowledge states to slow down progression
        # As knowledge increases, learning becomes more incremental
        if current_knowledge < 0.3:
            # Less boost for beginners than before
            base_rate = self.p_transit * 1.1
        elif current_knowledge < 0.6:
            # Slower learning in the middle range
            base_rate = self.p_transit * 0.8
        else:
            # Extremely slow progression at higher levels (stronger logarithmic tail)
            # Use a logarithmically decreasing function for the transit rate
            knowledge_factor = 1.0 - current_knowledge
            log_factor = -0.25 * max(0.1, math.log10(knowledge_factor + 0.1))
            base_rate = self.p_transit * log_factor
            
            # Cap the minimum learning rate even lower to make high-end progression exceptionally slow
            base_rate = max(base_rate, self.p_transit * 0.05)
        
        # Apply global slowdown
        adjusted_rate = base_rate * global_slowdown
        
        # Apply consecutive correct answers bonus, but with a smaller impact
        if self.consecutive_correct > 2:
            # Much smaller bonus for consecutive correct answers
            bonus = min(0.3, (self.consecutive_correct - 2) * 0.05)
            adjusted_rate *= (1 + bonus)
        
        # Calculate knowledge update with the adjusted rate
        knowledge_gain = (1 - current_knowledge) * adjusted_rate
        
        # Return the updated knowledge state, ensuring it stays within bounds
        return min(1.0, current_knowledge + knowledge_gain)

    def update(self, current_knowledge: float, is_correct: bool) -> float:
        """
        Update knowledge state based on observed performance.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            is_correct (bool): Whether the answer was correct
            
        Returns:
            float: Updated probability of knowing the skill
        """
        # Track consecutive correct answers
        if is_correct:
            self.consecutive_correct += 1
        else:
            self.consecutive_correct = 0

        # Use the predict method to get the updated knowledge state
        updated_knowledge = self.predict(current_knowledge)
        
        # Apply Bayes' rule to update knowledge based on the answer
        if is_correct:
            # P(L | correct) = P(correct | L) * P(L) / P(correct)
            numerator = updated_knowledge * (1 - self.p_slip)
            denominator = updated_knowledge * (1 - self.p_slip) + (1 - updated_knowledge) * self.p_guess
        else:
            # P(L | incorrect) = P(incorrect | L) * P(L) / P(incorrect)
            numerator = updated_knowledge * self.p_slip
            denominator = updated_knowledge * self.p_slip + (1 - updated_knowledge) * (1 - self.p_guess)
        
        # Initialize slip_adjustment before using it
        slip_adjustment = 0
        
        # Determine slip adjustment based on knowledge level and consecutive correct answers
        if is_correct:
            # Require more consistency at all knowledge levels
            if current_knowledge < 0.5:
                # Early learning phase - increased penalty for knowledge growth
                if self.consecutive_correct > 2:
                    slip_adjustment = min(0.05 * (self.consecutive_correct - 2), 0.15)
                else:
                    # Minimal progress for first few correct answers
                    slip_adjustment = 0.15
            else:
                # Advanced learning phase - much stronger penalty
                if self.consecutive_correct > 3:
                    # Higher knowledge requires extensive consistent performance
                    slip_adjustment = min(0.10 * (self.consecutive_correct - 3), 0.25)
                else:
                    # Little progress without consistency
                    slip_adjustment = 0.20
        
        if is_correct:
            # Correct answer: Update based on slip probability (with adjustment)
            effective_slip = self.p_slip + slip_adjustment
            numerator = current_knowledge * (1 - effective_slip)
            denominator = current_knowledge * (1 - effective_slip) + (1 - current_knowledge) * self.p_guess
        else:
            # Incorrect answer: More impactful at all knowledge levels
            # Higher knowledge_penalty means more punishment for mistakes
            knowledge_penalty = 1.2  # Increased from 1.0
            numerator = current_knowledge * self.p_slip
            denominator = current_knowledge * self.p_slip + (1 - current_knowledge) * (1 - self.p_guess) * knowledge_penalty
        
        # Apply additional dampening to all knowledge updates
        update_value = numerator / denominator if denominator != 0 else current_knowledge
        dampened_update = current_knowledge + (update_value - current_knowledge) * 0.85
        
        # Ensure the result stays within bounds
        return max(0.0, min(1.0, dampened_update))

    def reset_counter(self):
        """Reset the consecutive correct counter."""
        self.consecutive_correct = 0

    def is_mastered(self, current_knowledge: float, threshold: float = 0.985) -> bool:
        """
        Determine if the user has mastered the skill based on a threshold.
        Significantly increased threshold makes mastery much harder to achieve.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            threshold (float): Threshold for mastery (default: 0.985)
            
        Returns:
            bool: True if the skill is mastered, False otherwise
        """
        return current_knowledge >= threshold
