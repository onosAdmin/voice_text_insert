"""State machine module for managing voice recognition application states."""

import threading
import time
from enum import Enum, auto
from typing import Callable, Optional, Any
from dataclasses import dataclass


class ListeningState(Enum):
    """Application states for the listening state machine."""

    LISTENING_ONLY_STATE = auto()
    SHOWING_STATE = auto()
    ERROR_STATE = auto()


@dataclass
class StateTransition:
    """Represents a state transition event."""

    from_state: ListeningState
    to_state: ListeningState
    event: str
    action: Optional[Callable] = None


class ListeningStateMachine:
    """Thread-safe state machine for managing voice recognition application states.

    Implements a two-state machine with the following valid transitions:
    - LISTENING_ONLY_STATE → SHOWING_STATE (on "alexa scrivi" keyword detected)
    - SHOWING_STATE → LISTENING_ONLY_STATE (on popup close or "inserisci" command)
    - * → LISTENING_ONLY_STATE (on error or cancel)
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        ListeningState.LISTENING_ONLY_STATE: {
            ListeningState.SHOWING_STATE,
            ListeningState.ERROR_STATE,
        },
        ListeningState.SHOWING_STATE: {
            ListeningState.LISTENING_ONLY_STATE,
            ListeningState.ERROR_STATE,
        },
        ListeningState.ERROR_STATE: {
            ListeningState.LISTENING_ONLY_STATE,
        },
    }

    def __init__(self):
        """Initialize the state machine in LISTENING_ONLY_STATE."""
        self._state = ListeningState.LISTENING_ONLY_STATE
        self._lock = threading.RLock()
        self._transition_callbacks: dict[tuple[ListeningState, ListeningState], list[Callable]] = {}
        self._state_entry_callbacks: dict[ListeningState, list[Callable]] = {}
        self._state_exit_callbacks: dict[ListeningState, list[Callable]] = {}
        self._retry_count = 0
        self._max_retries = 3
        self._retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff delays

    @property
    def current_state(self) -> ListeningState:
        """Get the current state in a thread-safe manner."""
        with self._lock:
            return self._state

    def is_in_state(self, state: ListeningState) -> bool:
        """Check if the current state matches the given state."""
        with self._lock:
            return self._state == state

    def can_transition_to(self, target_state: ListeningState) -> bool:
        """Check if a transition to the target state is valid."""
        with self._lock:
            return target_state in self.VALID_TRANSITIONS.get(self._state, set())

    def transition_to(
        self,
        target_state: ListeningState,
        context: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Attempt to transition to the target state.

        Args:
            target_state: The state to transition to
            context: Optional context data to pass to callbacks

        Returns:
            True if the transition was successful, False otherwise
        """
        with self._lock:
            current_state = self._state

            # Check if transition is valid
            if not self.can_transition_to(target_state):
                print(
                    f"Warning: Invalid state transition attempted: "
                    f"{current_state.name} → {target_state.name}"
                )
                return False

            # Execute exit callbacks for current state
            self._execute_callbacks(
                self._state_exit_callbacks.get(current_state, []),
                current_state,
                target_state,
                context,
            )

            # Perform the transition
            self._state = target_state
            print(f"State transition: {current_state.name} → {target_state.name}")

            # Reset retry count on successful transition
            if target_state != ListeningState.ERROR_STATE:
                self._retry_count = 0

            # Execute transition callbacks
            transition_key = (current_state, target_state)
            self._execute_callbacks(
                self._transition_callbacks.get(transition_key, []),
                current_state,
                target_state,
                context,
            )

            # Execute entry callbacks for new state
            self._execute_callbacks(
                self._state_entry_callbacks.get(target_state, []),
                current_state,
                target_state,
                context,
            )

            return True

    def _execute_callbacks(
        self,
        callbacks: list[Callable],
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict[str, Any]],
    ):
        """Execute a list of callbacks with the given parameters."""
        for callback in callbacks:
            try:
                callback(from_state, to_state, context)
            except Exception as e:
                print(f"Error executing state callback: {e}")

    def on_transition(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        callback: Callable[[ListeningState, ListeningState, Optional[dict]], None],
    ):
        """Register a callback for a specific state transition.

        Args:
            from_state: The source state
            to_state: The target state
            callback: Function to call when transition occurs
        """
        transition_key = (from_state, to_state)
        if transition_key not in self._transition_callbacks:
            self._transition_callbacks[transition_key] = []
        self._transition_callbacks[transition_key].append(callback)

    def on_state_entry(
        self,
        state: ListeningState,
        callback: Callable[[ListeningState, ListeningState, Optional[dict]], None],
    ):
        """Register a callback for when entering a specific state.

        Args:
            state: The state to watch
            callback: Function to call when entering the state
        """
        if state not in self._state_entry_callbacks:
            self._state_entry_callbacks[state] = []
        self._state_entry_callbacks[state].append(callback)

    def on_state_exit(
        self,
        state: ListeningState,
        callback: Callable[[ListeningState, ListeningState, Optional[dict]], None],
    ):
        """Register a callback for when exiting a specific state.

        Args:
            state: The state to watch
            callback: Function to call when exiting the state
        """
        if state not in self._state_exit_callbacks:
            self._state_exit_callbacks[state] = []
        self._state_exit_callbacks[state].append(callback)

    def get_retry_delay(self) -> float:
        """Get the current retry delay based on retry count.

        Returns:
            The delay in seconds for the current retry attempt
        """
        with self._lock:
            if self._retry_count < len(self._retry_delays):
                return self._retry_delays[self._retry_count]
            return self._retry_delays[-1]  # Return max delay

    def increment_retry(self) -> bool:
        """Increment the retry count and check if retries are exhausted.

        Returns:
            True if more retries are available, False otherwise
        """
        with self._lock:
            self._retry_count += 1
            return self._retry_count < self._max_retries

    def reset_retries(self):
        """Reset the retry count to zero."""
        with self._lock:
            self._retry_count = 0

    def should_retry(self) -> bool:
        """Check if retries are still available.

        Returns:
            True if more retries are available, False otherwise
        """
        with self._lock:
            return self._retry_count < self._max_retries

    def __str__(self) -> str:
        """Return string representation of current state."""
        return f"ListeningStateMachine(current={self.current_state.name})"
