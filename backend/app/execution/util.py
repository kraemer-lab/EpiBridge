def parse_exit_code(wait_result: int | dict) -> int:
    if isinstance(wait_result, int):
        return wait_result
    if isinstance(wait_result, dict):
        status_code = wait_result.get("StatusCode")
        if isinstance(status_code, int):
            return status_code
        raise RuntimeError(
            f"Unexpected container wait result format: "
            f"dict without integer StatusCode: {wait_result}"
        )
    raise RuntimeError(
        f"Unexpected container wait result type: "
        f"{type(wait_result).__name__}: {wait_result}"
    )
