class BKTEngine:
    def __init__(self, p_init=0.2, p_transit=0.3, p_slip=0.1, p_guess=0.1, p_lapse=0.3):
        self.p_init = p_init
        self.p_transit = p_transit
        self.p_slip = p_slip
        self.p_guess = p_guess
        self.p_lapse = p_lapse

    def predict(self, current_knowledge: float) -> float:
        """
        Predict the probability of knowing the skill after a learning opportunity.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            
        Returns:
            float: Predicted probability of knowing the skill
        """
        return current_knowledge + (1 - current_knowledge) * self.p_transit

    def update(self, current_knowledge: float, is_correct: bool) -> float:
        """
        Update the knowledge state based on the user's performance.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            is_correct (bool): Whether the user's answer was correct
            
        Returns:
            float: Updated probability of knowing the skill
        """
        if is_correct:
            # Correct answer: Update based on slip probability
            numerator = current_knowledge * (1 - self.p_slip)
            denominator = current_knowledge * (1 - self.p_slip) + (1 - current_knowledge) * self.p_guess
        else:
            # Incorrect answer: Update based on guess probability
            numerator = current_knowledge * self.p_slip
            denominator = current_knowledge * self.p_slip + (1 - current_knowledge) * (1 - self.p_guess)
        
        return numerator / denominator if denominator != 0 else current_knowledge

    def is_mastered(self, current_knowledge: float, threshold: float = 0.95) -> bool:
        """
        Determine if the user has mastered the skill based on a threshold.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            threshold (float): Threshold for mastery (default: 0.95)
            
        Returns:
            bool: True if the skill is mastered, False otherwise
        """
        return current_knowledge >= threshold
