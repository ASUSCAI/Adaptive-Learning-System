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
        Modified to provide extremely slow progression.
        
        Args:
            current_knowledge (float): Current probability of knowing the skill
            
        Returns:
            float: Predicted probability of knowing the skill
        """
        # Apply a very strong global learning rate reduction
        global_slowdown = 0.05  # Reduce learning by 95%
        
        # Add a damping factor for high knowledge states to slow down progression
        # As knowledge increases, learning becomes extremely incremental
        if current_knowledge < 0.3:
            # Minimal boost for beginners
            base_rate = self.p_transit * 0.9
        elif current_knowledge < 0.6:
            # Very slow learning in the middle range
            base_rate = self.p_transit * 0.6
        else:
            # Extremely slow progression at higher levels (stronger logarithmic tail)
            knowledge_factor = 1.0 - current_knowledge
            log_factor = -0.15 * max(0.1, math.log10(knowledge_factor + 0.1))
            base_rate = self.p_transit * log_factor
            
            # Cap the minimum learning rate at an extremely low level
            base_rate = max(base_rate, self.p_transit * 0.03)
        
        # Apply global slowdown
        adjusted_rate = base_rate * global_slowdown
        
        # Apply conservative consecutive correct answers bonus
        if self.consecutive_correct > 3:  # Require more consecutive correct answers
            # Small bonus for consecutive correct answers
            bonus = min(0.2, (self.consecutive_correct - 3) * 0.04)
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
                if self.consecutive_correct > 3:  # Need more consecutive correct answers
                    slip_adjustment = min(0.02 * (self.consecutive_correct - 3), 0.18)
                else:
                    # Minimal progress for first few correct answers
                    slip_adjustment = 0.20
            else:
                # Advanced learning phase - much stronger penalty
                if self.consecutive_correct > 5:  # Need many more consecutive correct answers
                    # Higher knowledge requires extensive consistent performance
                    slip_adjustment = min(0.02 * (self.consecutive_correct - 5), 0.25)
                else:
                    # Little progress without consistency
                    slip_adjustment = 0.25
        
        if is_correct:
            # Correct answer: Update based on slip probability (with adjustment)
            effective_slip = self.p_slip + slip_adjustment
            numerator = current_knowledge * (1 - effective_slip)
            denominator = current_knowledge * (1 - effective_slip) + (1 - current_knowledge) * self.p_guess
        else:
            # Incorrect answer: More impactful at all knowledge levels
            # Higher knowledge_penalty means more punishment for mistakes
            knowledge_penalty = 1.6  # Very strong penalty for mistakes
            numerator = current_knowledge * self.p_slip
            denominator = current_knowledge * self.p_slip + (1 - current_knowledge) * (1 - self.p_guess) * knowledge_penalty
        
        # Apply strong dampening to all knowledge updates
        update_value = numerator / denominator if denominator != 0 else current_knowledge
        dampened_update = current_knowledge + (update_value - current_knowledge) * 0.6  # Heavy dampening
        
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


class IBKTEngine(BKTEngine):
    """
    Individualized Bayesian Knowledge Tracing (IBKT) engine.
    
    This version of BKT adapts the model parameters to individual learner characteristics.
    It does this by maintaining a history of performance and using this to adjust parameters
    dynamically over time.
    """
    
    def __init__(self, p_init=0.15, p_transit=0.12, p_slip=0.20, p_guess=0.08, p_lapse=0.30, 
                 learning_rate=0.03, adaptivity_threshold=12, 
                 performance_history=None, adaptation_rate=0.03):
        """
        Initialize the IBKT engine with default parameters and adaptation settings.
        
        Args:
            p_init: Initial probability of knowing the skill
            p_transit: Probability of transitioning from not knowing to knowing
            p_slip: Probability of making a mistake despite knowing
            p_guess: Probability of guessing correctly despite not knowing
            p_lapse: Probability of forgetting a skill
            learning_rate: Base learning rate for parameter adaptation
            adaptivity_threshold: Minimum number of attempts before adapting parameters
            performance_history: List of past performance (True for correct, False for incorrect)
            adaptation_rate: How quickly parameters adapt (higher = faster adaptation)
        """
        # Decreased default p_transit from 0.20 to 0.12
        # Increased p_slip from 0.15 to 0.20
        # Decreased learning_rate from 0.08 to 0.03
        # Decreased adaptation_rate from 0.08 to 0.03
        # Increased adaptivity_threshold from 8 to 12
        super().__init__(p_init, p_transit, p_slip, p_guess, p_lapse)
        
        # Parameters for the adaptive model
        self.learning_rate = learning_rate
        self.adaptivity_threshold = adaptivity_threshold
        self.adaptation_rate = adaptation_rate
        
        # Initialize performance history if not provided
        self.performance_history = performance_history or []
        
        # Learner-specific parameter adjustments
        self.transit_adjustment = 0.0  # Adjustment to transit probability
        self.slip_adjustment = 0.0     # Adjustment to slip probability
        self.guess_adjustment = 0.0    # Adjustment to guess probability
        
        # Learning style metrics
        self.consistency_score = 0.0   # Measure of answer consistency
        self.improvement_rate = 0.0    # Rate of improvement over time
        self.error_recovery = 0.0      # Ability to recover from errors
        
        # Counters for adaptation
        self.total_attempts = 0
        self.correct_attempts = 0
        
    def update_performance_history(self, is_correct):
        """Add the latest performance to history and update counters."""
        self.performance_history.append(is_correct)
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1
            
        # Keep history at a manageable size by removing oldest entries
        if len(self.performance_history) > 100:
            self.performance_history.pop(0)
            
    def update_learning_metrics(self):
        """Update the learning style metrics based on performance history."""
        if len(self.performance_history) < self.adaptivity_threshold:
            return
            
        # Calculate consistency score (how consistent the answers are)
        if len(self.performance_history) > 8:  # Need longer history
            recent = self.performance_history[-8:]  # Longer window
            self.consistency_score = sum(1 for i in range(1, len(recent)) 
                                         if recent[i] == recent[i-1]) / (len(recent) - 1)
                                         
        # Calculate improvement rate (trend of correctness)
        if len(self.performance_history) >= 12:  # Longer window for trend
            first_half = self.performance_history[-12:-6]  # Longer ranges
            second_half = self.performance_history[-6:]
            first_correct_rate = sum(first_half) / len(first_half)
            second_correct_rate = sum(second_half) / len(second_half)
            self.improvement_rate = second_correct_rate - first_correct_rate
            
        # Calculate error recovery (ability to get correct after an error)
        if len(self.performance_history) >= 6:  # Increased from 3
            recovery_opportunities = 0
            recoveries = 0
            for i in range(1, len(self.performance_history)):
                if not self.performance_history[i-1]:  # Previous answer was wrong
                    recovery_opportunities += 1
                    if self.performance_history[i]:  # Current answer is correct
                        recoveries += 1
                        
            self.error_recovery = recoveries / recovery_opportunities if recovery_opportunities > 0 else 0.5
    
    def adapt_parameters(self):
        """Adapt parameters based on learning metrics."""
        if self.total_attempts < self.adaptivity_threshold:
            return
            
        # Update learning metrics first
        self.update_learning_metrics()
        
        # Calculate overall correctness rate
        correctness_rate = self.correct_attempts / self.total_attempts if self.total_attempts > 0 else 0.5
        
        # Adapt transit parameter based on improvement rate and consistency
        # A high improvement rate with good consistency should increase transit
        transit_factor = (self.improvement_rate * 1.5 + self.consistency_score) / 3  # Decreased weight
        self.transit_adjustment = self.adaptation_rate * transit_factor * 0.8  # Reduced adjustment
        
        # Adapt slip parameter based on consistency and correctness
        # Higher consistency should decrease slip probability
        slip_factor = 1.0 - (self.consistency_score * 0.7 + correctness_rate * 0.3)
        self.slip_adjustment = -self.adaptation_rate * slip_factor * 0.7  # Reduced adjustment
        
        # Adapt guess parameter based on error recovery
        # High error recovery might indicate educated guessing rather than knowledge
        guess_factor = self.error_recovery - 0.5  # Center around zero
        self.guess_adjustment = self.adaptation_rate * guess_factor
    
    def get_individualized_parameters(self):
        """Get the individualized parameters adjusted for this learner."""
        # More restricted adjustment range
        bounded_transit_adj = max(-0.05, min(0.05, self.transit_adjustment))  # Decreased from ±0.15
        bounded_slip_adj = max(-0.05, min(0.05, self.slip_adjustment))  # Decreased from ±0.15
        bounded_guess_adj = max(-0.03, min(0.03, self.guess_adjustment))  # Decreased from ±0.08
        
        # Apply adjustments to base parameters
        individualized_transit = max(0.05, min(0.3, self.p_transit + bounded_transit_adj))  # Lower upper limit
        individualized_slip = max(0.10, min(0.3, self.p_slip + bounded_slip_adj))  # Higher lower limit
        individualized_guess = max(0.03, min(0.15, self.p_guess + bounded_guess_adj))  # Lower upper limit
        
        return {
            'p_transit': individualized_transit,
            'p_slip': individualized_slip,
            'p_guess': individualized_guess
        }
    
    def predict(self, current_knowledge: float) -> float:
        """
        Override predict method to use individualized parameters.
        """
        # Apply individualized parameters
        params = self.get_individualized_parameters()
        original_transit = self.p_transit
        self.p_transit = params['p_transit']
        
        # Call the parent class predict method
        result = super().predict(current_knowledge)
        
        # Add minimal bonus for consistent performance only after many correct answers
        if self.consecutive_correct >= 5:  # Increased from 3
            consistency_bonus = min(0.01 * (self.consecutive_correct - 5), 0.05)  # Reduced bonus
            result = min(1.0, result + consistency_bonus)
        
        # Restore original parameters
        self.p_transit = original_transit
        
        return result
    
    def update(self, current_knowledge: float, is_correct: bool) -> float:
        """
        Override update method to use individualized parameters and update history.
        """
        # Update performance history first
        self.update_performance_history(is_correct)
        
        # Try to adapt parameters based on the new history
        self.adapt_parameters()
        
        # Apply individualized parameters temporarily
        params = self.get_individualized_parameters()
        original_transit = self.p_transit
        original_slip = self.p_slip
        original_guess = self.p_guess
        
        self.p_transit = params['p_transit']
        self.p_slip = params['p_slip']
        self.p_guess = params['p_guess']
        
        # Call the parent class update method
        result = super().update(current_knowledge, is_correct)
        
        # Apply additional adjustment to make progress more conservative
        if is_correct:
            # Small boost for correct answers only after many consecutive
            if self.consecutive_correct >= 5:
                progress_boost = 1.0 + min(0.15, (self.consecutive_correct - 5) * 0.03)  # Reduced boost
                result = min(1.0, current_knowledge + (result - current_knowledge) * progress_boost)
            else:
                # Dampen progress for initial correct answers
                result = current_knowledge + (result - current_knowledge) * 0.7
        else:
            # Substantial reduction for incorrect answers
            result = current_knowledge + (result - current_knowledge) * 1.3
        
        # Restore original parameters
        self.p_transit = original_transit
        self.p_slip = original_slip
        self.p_guess = original_guess
        
        return result

class QuestionManager:
    """
    Manages question selection based on user performance, implementing spaced repetition
    and error-based repetition strategies.
    """
    
    def __init__(self, spacing_factor=2.0, error_priority=0.8, knowledge_penalty=0.3):
        """
        Initialize the QuestionManager.
        
        Args:
            spacing_factor: Controls how quickly spacing increases for correct answers
            error_priority: Priority multiplier for questions answered incorrectly
            knowledge_penalty: How much knowledge drops when a previously correct answer becomes wrong
        """
        self.question_history = {}  # Maps question_id -> list of {timestamp, correct, knowledge} 
        self.last_seen = {}         # Maps question_id -> attempt number when last seen
        self.correct_streak = {}    # Maps question_id -> number of times correctly answered in a row
        self.attempt_counter = 0    # Global counter of question attempts
        self.spacing_factor = spacing_factor
        self.error_priority = error_priority
        self.knowledge_penalty = knowledge_penalty
        
    def register_attempt(self, question_id, is_correct, knowledge_level, timestamp=None):
        """
        Register an attempt at answering a question.
        
        Args:
            question_id: Unique identifier for the question
            is_correct: Whether the answer was correct
            knowledge_level: Current knowledge level for this skill/concept
            timestamp: Optional timestamp (defaults to attempt counter)
        """
        if timestamp is None:
            timestamp = self.attempt_counter
            
        self.attempt_counter += 1
        
        # Initialize history if this is a new question
        if question_id not in self.question_history:
            self.question_history[question_id] = []
            self.correct_streak[question_id] = 0
            
        # Update correct streak counter
        if is_correct:
            self.correct_streak[question_id] += 1
        else:
            self.correct_streak[question_id] = 0
            
        # Check if this was previously correct but is now wrong
        prev_knowledge = None
        if len(self.question_history[question_id]) > 0:
            last_entry = self.question_history[question_id][-1]
            prev_knowledge = last_entry["knowledge"]
            
            # Apply knowledge penalty if previously answered correctly but now wrong
            if not is_correct and last_entry["correct"]:
                # Apply penalty proportional to previous knowledge level
                knowledge_level = max(0.1, knowledge_level - self.knowledge_penalty * prev_knowledge)
        
        # Record this attempt
        self.question_history[question_id].append({
            "timestamp": timestamp,
            "correct": is_correct,
            "knowledge": knowledge_level
        })
        
        # Update last seen
        self.last_seen[question_id] = self.attempt_counter
            
        return knowledge_level  # Return possibly adjusted knowledge level
    
    def get_question_selection_probabilities(self, available_question_ids, current_attempt=None):
        """
        Calculate selection probabilities for available questions.
        
        Args:
            available_question_ids: List of question IDs available for selection
            current_attempt: Current attempt number (defaults to attempt counter)
            
        Returns:
            dict: Mapping of question_id -> selection probability
        """
        if current_attempt is None:
            current_attempt = self.attempt_counter
            
        probabilities = {}
        total_weight = 0
        
        for q_id in available_question_ids:
            # New questions have high priority
            if q_id not in self.question_history:
                probabilities[q_id] = 1.0
                total_weight += 1.0
                continue
                
            history = self.question_history[q_id]
            last_entry = history[-1]
            
            # Base priority starts low for known items, higher for unknown
            priority = 1.0 - last_entry["knowledge"]
            
            # Time factor - questions not seen recently get higher priority
            time_since_last = current_attempt - self.last_seen.get(q_id, 0)
            
            # Spacing based on correctness streak
            correct_count = self.correct_streak.get(q_id, 0)
            
            if correct_count > 0:
                # Increase spacing exponentially with correct answers
                ideal_spacing = self.spacing_factor ** min(correct_count, 5)
                time_factor = time_since_last / ideal_spacing
                # Sigmoid-like function: low probability until approaching ideal spacing
                time_priority = 1 / (1 + math.exp(-5 * (time_factor - 0.8)))
            else:
                # For incorrect answers, use a shorter delay
                ideal_spacing = max(2, 5 - correct_count)  # Shorter delay for wrong answers
                time_factor = time_since_last / ideal_spacing
                # Linear increase up to the ideal spacing
                time_priority = min(1.0, time_factor * self.error_priority)
            
            # Final priority combines knowledge state and time factors
            priority = 0.3 * priority + 0.7 * time_priority
            
            # Extra boost for items with errors
            if not last_entry["correct"]:
                priority *= self.error_priority
                
            probabilities[q_id] = max(0.05, priority)  # Ensure minimum probability
            total_weight += probabilities[q_id]
        
        # Normalize to create probability distribution
        if total_weight > 0:
            for q_id in probabilities:
                probabilities[q_id] /= total_weight
                
        return probabilities
    
    def select_next_question(self, available_question_ids, current_attempt=None):
        """
        Select the next question based on performance history and spacing.
        
        Args:
            available_question_ids: List of question IDs available for selection
            current_attempt: Current attempt number (defaults to attempt counter)
            
        Returns:
            question_id: The selected question ID
        """
        import random
        
        if not available_question_ids:
            return None
            
        # If we have just one question, return it
        if len(available_question_ids) == 1:
            return available_question_ids[0]
            
        # Get selection probabilities
        probs = self.get_question_selection_probabilities(
            available_question_ids, current_attempt
        )
        
        # Convert to list for random.choices
        items = list(probs.keys())
        weights = [probs[item] for item in items]
        
        # Select question using weighted random
        selected = random.choices(items, weights=weights, k=1)[0]
        return selected
    
    def get_question_stats(self, question_id):
        """
        Get performance statistics for a specific question.
        
        Args:
            question_id: The question identifier
            
        Returns:
            dict: Performance statistics
        """
        if question_id not in self.question_history:
            return {"attempts": 0, "correct": 0, "knowledge": 0, "streak": 0}
            
        history = self.question_history[question_id]
        attempts = len(history)
        correct = sum(1 for entry in history if entry["correct"])
        last_knowledge = history[-1]["knowledge"] if history else 0
        streak = self.correct_streak.get(question_id, 0)
        
        return {
            "attempts": attempts,
            "correct": correct,
            "correct_rate": correct / attempts if attempts > 0 else 0,
            "knowledge": last_knowledge,
            "streak": streak,
            "last_seen": self.last_seen.get(question_id)
        }
