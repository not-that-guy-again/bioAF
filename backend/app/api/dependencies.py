from fastapi import Depends, HTTPException, Request


def require_role(*allowed_roles: str):
    def checker(request: Request):
        user = request.state.current_user
        if user["role"] not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return Depends(checker)
