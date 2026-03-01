"""Tests for the state machine module."""

import unittest
import threading
import time
from src.state_machine import ListeningStateMachine, ListeningState


class TestListeningStateMachine(unittest.TestCase):
    """Test cases for the ListeningStateMachine class."""

    def test_initial_state(self):
        """Test that state machine starts in LISTENING_ONLY_STATE."""
        sm = ListeningStateMachine()
        self.assertEqual(sm.current_state, ListeningState.LISTENING_ONLY_STATE)

    def test_valid_transition_listening_to_showing(self):
        """Test valid transition from LISTENING_ONLY_STATE to SHOWING_STATE."""
        sm = ListeningStateMachine()
        result = sm.transition_to(ListeningState.SHOWING_STATE)
        self.assertTrue(result)
        self.assertEqual(sm.current_state, ListeningState.SHOWING_STATE)

    def test_valid_transition_showing_to_listening(self):
        """Test valid transition from SHOWING_STATE to LISTENING_ONLY_STATE."""
        sm = ListeningStateMachine()
        sm.transition_to(ListeningState.SHOWING_STATE)
        result = sm.transition_to(ListeningState.LISTENING_ONLY_STATE)
        self.assertTrue(result)
        self.assertEqual(sm.current_state, ListeningState.LISTENING_ONLY_STATE)

    def test_invalid_transition_showing_to_showing(self):
        """Test that SHOWING_STATE -> SHOWING_STATE is invalid."""
        sm = ListeningStateMachine()
        sm.transition_to(ListeningState.SHOWING_STATE)
        result = sm.transition_to(ListeningState.SHOWING_STATE)
        self.assertFalse(result)
        self.assertEqual(sm.current_state, ListeningState.SHOWING_STATE)

    def test_invalid_transition_listening_to_listening(self):
        """Test that LISTENING_ONLY_STATE -> LISTENING_ONLY_STATE is invalid."""
        sm = ListeningStateMachine()
        result = sm.transition_to(ListeningState.LISTENING_ONLY_STATE)
        self.assertFalse(result)
        self.assertEqual(sm.current_state, ListeningState.LISTENING_ONLY_STATE)

    def test_error_state_transition(self):
        """Test transition to ERROR_STATE from any state."""
        sm = ListeningStateMachine()
        result = sm.transition_to(ListeningState.ERROR_STATE)
        self.assertTrue(result)
        self.assertEqual(sm.current_state, ListeningState.ERROR_STATE)

    def test_recovery_from_error_state(self):
        """Test recovery from ERROR_STATE to LISTENING_ONLY_STATE."""
        sm = ListeningStateMachine()
        sm.transition_to(ListeningState.ERROR_STATE)
        result = sm.transition_to(ListeningState.LISTENING_ONLY_STATE)
        self.assertTrue(result)
        self.assertEqual(sm.current_state, ListeningState.LISTENING_ONLY_STATE)

    def test_is_in_state(self):
        """Test the is_in_state method."""
        sm = ListeningStateMachine()
        self.assertTrue(sm.is_in_state(ListeningState.LISTENING_ONLY_STATE))
        self.assertFalse(sm.is_in_state(ListeningState.SHOWING_STATE))

    def test_can_transition_to(self):
        """Test the can_transition_to method."""
        sm = ListeningStateMachine()
        self.assertTrue(sm.can_transition_to(ListeningState.SHOWING_STATE))
        self.assertTrue(sm.can_transition_to(ListeningState.ERROR_STATE))
        self.assertFalse(sm.can_transition_to(ListeningState.LISTENING_ONLY_STATE))

    def test_callback_execution(self):
        """Test that callbacks are executed on state transitions."""
        sm = ListeningStateMachine()
        callback_called = []

        def test_callback(from_state, to_state, context):
            callback_called.append((from_state, to_state, context))

        sm.on_transition(
            ListeningState.LISTENING_ONLY_STATE,
            ListeningState.SHOWING_STATE,
            test_callback,
        )

        sm.transition_to(ListeningState.SHOWING_STATE, {"test": "data"})

        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0][0], ListeningState.LISTENING_ONLY_STATE)
        self.assertEqual(callback_called[0][1], ListeningState.SHOWING_STATE)
        self.assertEqual(callback_called[0][2], {"test": "data"})

    def test_state_entry_callback(self):
        """Test state entry callback execution."""
        sm = ListeningStateMachine()
        entry_called = []

        def entry_callback(from_state, to_state, context):
            entry_called.append(to_state)

        sm.on_state_entry(ListeningState.SHOWING_STATE, entry_callback)
        sm.transition_to(ListeningState.SHOWING_STATE)

        self.assertEqual(len(entry_called), 1)
        self.assertEqual(entry_called[0], ListeningState.SHOWING_STATE)

    def test_state_exit_callback(self):
        """Test state exit callback execution."""
        sm = ListeningStateMachine()
        exit_called = []

        def exit_callback(from_state, to_state, context):
            exit_called.append(from_state)

        sm.on_state_exit(ListeningState.LISTENING_ONLY_STATE, exit_callback)
        sm.transition_to(ListeningState.SHOWING_STATE)

        self.assertEqual(len(exit_called), 1)
        self.assertEqual(exit_called[0], ListeningState.LISTENING_ONLY_STATE)

    def test_thread_safety(self):
        """Test that state machine handles concurrent transitions safely."""
        sm = ListeningStateMachine()
        results = []

        def transition_worker(target_state):
            result = sm.transition_to(target_state)
            results.append(result)

        threads = [
            threading.Thread(target=transition_worker, args=(ListeningState.SHOWING_STATE,)),
            threading.Thread(target=transition_worker, args=(ListeningState.ERROR_STATE,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Both transitions may succeed if they happen sequentially:
        # LISTENING_ONLY_STATE → SHOWING_STATE → ERROR_STATE
        # This demonstrates thread-safe sequential execution
        self.assertGreaterEqual(sum(results), 1)
        # Final state should be one of the target states
        self.assertIn(
            sm.current_state,
            [ListeningState.SHOWING_STATE, ListeningState.ERROR_STATE]
        )

    def test_retry_mechanism(self):
        """Test retry delay and count mechanism."""
        sm = ListeningStateMachine()

        # Initial state
        self.assertEqual(sm.get_retry_delay(), 1.0)
        self.assertTrue(sm.should_retry())

        # After first retry
        sm.increment_retry()
        self.assertEqual(sm.get_retry_delay(), 2.0)
        self.assertTrue(sm.should_retry())

        # After second retry
        sm.increment_retry()
        self.assertEqual(sm.get_retry_delay(), 4.0)
        self.assertTrue(sm.should_retry())

        # After third retry (max exceeded)
        sm.increment_retry()
        self.assertEqual(sm.get_retry_delay(), 4.0)  # Max delay
        self.assertFalse(sm.should_retry())

    def test_retry_reset_on_transition(self):
        """Test that retry count resets on successful transition."""
        sm = ListeningStateMachine()

        sm.increment_retry()
        sm.increment_retry()
        self.assertEqual(sm._retry_count, 2)

        # Transition should reset retry count
        sm.transition_to(ListeningState.SHOWING_STATE)
        self.assertEqual(sm._retry_count, 0)

    def test_string_representation(self):
        """Test the string representation of state machine."""
        sm = ListeningStateMachine()
        self.assertIn("LISTENING_ONLY_STATE", str(sm))

        sm.transition_to(ListeningState.SHOWING_STATE)
        self.assertIn("SHOWING_STATE", str(sm))


class TestListeningState(unittest.TestCase):
    """Test cases for the ListeningState enum."""

    def test_states_exist(self):
        """Test that all required states exist."""
        self.assertIsNotNone(ListeningState.LISTENING_ONLY_STATE)
        self.assertIsNotNone(ListeningState.SHOWING_STATE)
        self.assertIsNotNone(ListeningState.ERROR_STATE)

    def test_states_are_unique(self):
        """Test that all states are unique."""
        states = [
            ListeningState.LISTENING_ONLY_STATE,
            ListeningState.SHOWING_STATE,
            ListeningState.ERROR_STATE,
        ]
        self.assertEqual(len(states), len(set(states)))


if __name__ == "__main__":
    unittest.main()
