class BootstrapError(Exception):
    """Raised when the skill-bundled runtime cannot be bootstrapped."""


class RequestValidationError(Exception):
    """Raised when a start request is structurally invalid."""

    code = "invalid_request"


class ObservationValidationError(Exception):
    """Raised when an observation is structurally invalid."""

    code = "invalid_observation"


class ProtocolError(Exception):
    """Raised when the host violates the runtime protocol."""

    code = "protocol_error"


class WorkflowExecutionError(Exception):
    """Raised when runtime execution cannot progress safely."""

    code = "workflow_execution_error"


class StateConflictError(WorkflowExecutionError):
    """Raised when a persisted run changed while a stale snapshot was saving."""

    code = "state_conflict"


class VerifierExecutionError(WorkflowExecutionError):
    """Raised when a verifier cannot run within the trusted execution boundary."""

    code = "verifier_execution_error"


class ArtifactStoreError(WorkflowExecutionError):
    """Raised when a runtime-owned artifact cannot be stored or verified."""

    code = "artifact_store_error"


class TransportValidationError(WorkflowExecutionError):
    """Raised when an adapter receipt violates the canonical transport contract."""

    code = "invalid_transport"


class SchemaValidationError(WorkflowExecutionError):
    """Raised when a workflow contract uses or receives an invalid schema value."""

    code = "schema_validation_error"

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        expected: str | None = None,
        actual: str | None = None,
        source: str = "runtime",
        repairable: bool = False,
    ) -> None:
        self.path = path
        self.expected = expected
        self.actual = actual
        self.source = source
        self.repairable = repairable
        super().__init__(message)
