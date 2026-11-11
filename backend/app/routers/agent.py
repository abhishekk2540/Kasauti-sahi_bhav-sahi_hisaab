import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import PendingAction, User
from ..schemas import ChatIn
from ..services.agent.runner import run_agent
from ..services.agent.tools import execute_pending
from ..services.llm import get_llm_client

router = APIRouter(prefix="/agent", tags=["agent"])


def get_client():
    return get_llm_client()


@router.post("/chat")
def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db),
         client=Depends(get_client)):
    """Server-Sent Events stream. Each event: `data: {json}\\n\\n`. Ends with {"type":"done"}."""
    history = [m.model_dump() for m in body.messages]
    if history[-1]["role"] != "user":
        raise HTTPException(422, "Last message must be from the user")

    def gen():
        for ev in run_agent(db, user, history, client):
            yield f"data: {json.dumps(ev, default=str)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/pending")
def pending(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from sqlalchemy import select

    rows = db.scalars(select(PendingAction).where(PendingAction.user_id == user.id,
                                                  PendingAction.status == "pending")).all()
    return [{"id": r.id, "action": r.action, "summary": r.summary} for r in rows]


@router.post("/confirm/{action_id}")
def confirm(action_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return execute_pending(db, user, action_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/cancel/{action_id}")
def cancel(action_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pa = db.get(PendingAction, action_id)
    if not pa or pa.user_id != user.id:
        raise HTTPException(404, "Action not found")
    if pa.status != "pending":
        raise HTTPException(409, f"Action already {pa.status}")
    pa.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}
