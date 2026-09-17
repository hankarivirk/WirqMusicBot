"""Runtime compatibility aliases for legacy pytgcalls imports.

The pytgcalls release currently installed by the project imports several
Telegram exception names that are not exported by Pyrogram 2.x. Python loads
sitecustomize during interpreter startup, so these aliases are installed
before pytgcalls is imported.
"""

try:
    import pyrogram.errors as _errors

    _aliases = {
        "GroupcallForbidden": "Forbidden",
        "GroupcallInvalid": "BadRequest",
    }

    for _missing, _base_name in _aliases.items():
        if not hasattr(_errors, _missing) and hasattr(_errors, _base_name):
            setattr(_errors, _missing, type(_missing, (getattr(_errors, _base_name),), {}))
except Exception:
    # Do not prevent Python from starting if an optional dependency is absent.
    pass
