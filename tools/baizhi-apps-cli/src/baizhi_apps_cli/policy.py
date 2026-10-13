class ConfirmationRequired(RuntimeError):
    def __init__(self, operation: str, target: str) -> None:
        self.code = "CONFIRMATION_REQUIRED"
        self.message = f"{operation} on {target} requires --confirm."
        super().__init__(self.message)


_ALWAYS_CONFIRM = {"schema.apply", "data.delete", "h5.publish", "h5.rollback"}


def require_confirmation(environment: str, operation: str, target: str, *, confirmed: bool) -> None:
    required = environment == "production" or operation in _ALWAYS_CONFIRM
    if required and not confirmed:
        raise ConfirmationRequired(operation, target)
