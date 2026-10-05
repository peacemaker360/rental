"""Safe failures shared by storage and the API boundary."""


class DataIntegrityError(Exception):
    """Stored JSON does not have the required shape; never repair implicitly."""
