from uuid import uuid4

import psycopg2

from marketcore.action.command_worker_v2 import GovernedCommandWorkerV2, PostgresPendingRequestRollbackHandlerV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.presentation.render_tree.v2 import ActionKindV2


class Executor:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def execute(self, command):
        self.calls.append(command.request_kind)
        if self.fail: raise RuntimeError("expected failure")
        return "VERDICT=TEST_SAFE_COMPLETE"


def insert_request(kind="RESEARCH_REFRESH", action="research.request.refresh"):
    request_id=str(uuid4()); command="RESEARCH.REQUEST_REFRESH" if kind=="RESEARCH_REFRESH" else "PAPER.REQUEST_OBSERVATION"
    with psycopg2.connect("postgresql:///finam_core") as c:
        with c.cursor() as x:x.execute("INSERT INTO marketcore_action.command_request_v2(request_id,action_id,request_kind,command_code,actor_id,status,requested_at) VALUES(%s,%s,%s,%s,'test.worker','PENDING',clock_timestamp())",(request_id,action,kind,command))
    return request_id


def status(request_id):
    with psycopg2.connect("postgresql:///finam_core") as c:
        with c.cursor() as x:x.execute("SELECT status FROM marketcore_action.command_request_v2 WHERE request_id=%s",(request_id,));return x.fetchone()[0]


def test_worker_completes_claimed_request() -> None:
    request_id=insert_request(); executor=Executor()
    assert GovernedCommandWorkerV2(executor).run_once(request_id=request_id)=="COMPLETED"
    assert status(request_id)=="COMPLETED" and executor.calls==["RESEARCH_REFRESH"]


def test_worker_records_failure() -> None:
    request_id=insert_request("PAPER_OBSERVATION","paper.request.observation")
    assert GovernedCommandWorkerV2(Executor(True)).run_once(request_id=request_id)=="FAILED"
    assert status(request_id)=="FAILED"


def test_pending_request_can_be_rolled_back_but_completed_cannot() -> None:
    request_id=insert_request(); intent=ActionIntentV2("research.request.refresh",ActionKindV2.COMMAND,InteractionKindV2.DOUBLE_CLICK,ActionActorKindV2.OPERATOR,"test.worker",command_code="RESEARCH.REQUEST_REFRESH",policy_class="RESEARCH_MAINTENANCE",authorization_scope="research:write",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key=request_id)
    result=PostgresPendingRequestRollbackHandlerV2().rollback(intent,intent.rollback_code,request_id)
    assert result==f"cancelled:{request_id}" and status(request_id)=="CANCELLED"
    try: PostgresPendingRequestRollbackHandlerV2().rollback(intent,intent.rollback_code,request_id)
    except ValueError as exc: assert str(exc)=="PENDING_REQUEST_NOT_ROLLBACKABLE"
    else: raise AssertionError("second rollback must fail")
