class BootstrapError(Exception):
    """Raised when the skill-bundled runtime cannot be bootstrapped."""


class RequestValidationError(Exception):
    """Raised when a start request is structurally invalid."""


class ObservationValidationError(Exception):
    """Raised when an observation is structurally invalid."""


class ProtocolError(Exception):
    """Raised when the host violates the runtime protocol."""


class WorkflowExecutionError(Exception):
    """Raised when runtime execution cannot progress safely."""
