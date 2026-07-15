from datetime import datetime, timedelta, timezone

from marketcore.action.authorization_v2 import AuthorizationGrantV2, AuthorizationVerdictV2, ScopeAuthorizationEngineV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.policy_v2 import (
    ActionPolicyContextV2,
    ActionPolicyRuleV2,
    ActionPolicyVerdictV2,
    AutonomyModeV2,
    StaticActionPolicyEngineV2,
)
from marketcore.presentation.render_tree.v2 import ActionKindV2


NOW = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)


def command(*, actor_id: str = "operator.test", approval: bool = False, policy_class: str = "RESEARCH_MAINTENANCE") -> ActionIntentV2:
    return ActionIntentV2(
        action_id="research.refresh",
        action_kind=ActionKindV2.COMMAND,
        interaction_kind=InteractionKindV2.DOUBLE_CLICK,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id=actor_id,
        command_code="RESEARCH.REFRESH",
        policy_class=policy_class,
        authorization_scope="research:write",
        requires_approval=approval,
        reversible=not approval,
        rollback_code=None if approval else "RESEARCH.RESTORE_PREVIOUS_SNAPSHOT",
        idempotency_key="refresh-1",
    )


def engine() -> StaticActionPolicyEngineV2:
    return StaticActionPolicyEngineV2(
        {
            "RESEARCH_MAINTENANCE": ActionPolicyRuleV2(
                policy_class="RESEARCH_MAINTENANCE",
                allowed_modes=frozenset({AutonomyModeV2.RECOMMEND, AutonomyModeV2.AUTONOMOUS}),
                allowed_actors=frozenset({ActionActorKindV2.OPERATOR}),
                risk_guard_code="RISK.RESEARCH_RESOURCE_GUARD",
                valid_until=NOW + timedelta(days=1),
            )
        }
    )


def test_authorization_allows_exact_actor_and_scope() -> None:
    decision = ScopeAuthorizationEngineV2().authorize(
        command(),
        AuthorizationGrantV2("operator.test", frozenset({"research:write"}), NOW + timedelta(hours=1)),
        now=NOW,
    )
    assert decision.verdict is AuthorizationVerdictV2.ALLOW


def test_authorization_denies_missing_scope_and_actor_mismatch() -> None:
    boundary = ScopeAuthorizationEngineV2()
    missing = boundary.authorize(command(), AuthorizationGrantV2("operator.test", frozenset({"research:read"})), now=NOW)
    mismatch = boundary.authorize(command(), AuthorizationGrantV2("operator.other", frozenset({"research:*"})), now=NOW)
    assert missing.reason_code == "AUTHORIZATION_SCOPE_MISSING"
    assert mismatch.reason_code == "AUTHORIZATION_ACTOR_MISMATCH"


def test_authorization_denies_expired_grant() -> None:
    decision = ScopeAuthorizationEngineV2().authorize(
        command(), AuthorizationGrantV2("operator.test", frozenset({"research:*"}), NOW), now=NOW
    )
    assert decision.reason_code == "AUTHORIZATION_GRANT_EXPIRED"


def test_policy_fails_closed_for_unknown_class_and_advisory_mode() -> None:
    unknown = engine().evaluate(command(policy_class="UNKNOWN"), ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, NOW))
    advisory = engine().evaluate(command(), ActionPolicyContextV2(AutonomyModeV2.ADVISORY, NOW))
    assert unknown.reason_code == "POLICY_CLASS_UNKNOWN"
    assert advisory.reason_code == "AUTONOMY_MODE_FORBIDDEN"


def test_policy_requires_separate_approval() -> None:
    pending = engine().evaluate(command(approval=True), ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, NOW))
    allowed = engine().evaluate(command(approval=True), ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, NOW, approval_granted=True))
    assert pending.verdict is ActionPolicyVerdictV2.REQUIRE_APPROVAL
    assert allowed.verdict is ActionPolicyVerdictV2.ALLOW
    assert allowed.risk_guard_code == "RISK.RESEARCH_RESOURCE_GUARD"


def test_policy_denies_stale_data() -> None:
    decision = engine().evaluate(command(), ActionPolicyContextV2(AutonomyModeV2.AUTONOMOUS, NOW, stale_data=True))
    assert decision.reason_code == "POLICY_STALE_DATA"


def test_boundaries_fail_closed_for_naive_clock() -> None:
    naive_now = NOW.replace(tzinfo=None)
    authorization = ScopeAuthorizationEngineV2().authorize(
        command(), AuthorizationGrantV2("operator.test", frozenset({"research:*"})), now=naive_now
    )
    policy = engine().evaluate(command(), ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, naive_now))
    assert authorization.reason_code == "AUTHORIZATION_CLOCK_INVALID"
    assert policy.reason_code == "POLICY_CLOCK_INVALID"
