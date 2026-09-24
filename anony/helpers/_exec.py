import io
import sys
import traceback

async def execute_code(code: str, scope: dict) -> str:
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    stdout = sys.stdout
    stderr = sys.stderr

    try:
        sys.stdout = redirected_output
        sys.stderr = redirected_error
        exec(
            f"async def __aexec():\n" + "\n".join(f"    {line}" for line in code.split("\n")),
            scope
        )
        result = await scope["__aexec"]()
        output = redirected_output.getvalue()
        error = redirected_error.getvalue()
        if result is not None:
            return f"{result}\n{output}"
        return output or error or "Success (No Output)"
    except Exception:
        return traceback.format_exc()
    finally:
        sys.stdout = stdout
        sys.stderr = stderr
