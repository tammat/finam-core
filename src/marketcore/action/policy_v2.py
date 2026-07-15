from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping

from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, validate_action_intent_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2


class AutonomyModeV2(str, Enum):
    ADVISORY = "ADVISORY"
    RECOMMEND = "RECOMMEND"
    AUTONOMOUS = "AUTONOMOUS"


class ActionPolicyVerdictV2(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True, slots=True)
class ActionPolicyRuleV2:
    policy_class: str
    allowed_modes: frozenset[AutonomyModeV2]
    allowed_actors: frozenset[ActionActorKindV2]
    risk_guard_code: str | None = None
    deny_on_stale_data: bool = True
    valid_until: datetime | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ActionPolicyContextV2:
    autonomy_mode: AutonomyModeV2
    now: datetime
    approval_granted: bool = False
    stale_data: bool = False


@dataclass(frozen=True, slots=True)
class ActionPolicyDecisionV2:
    verdict: ActionPolicyVerdictV2
    reason_code: str
    policy_class: str | None
    risk_guard_code: str | None = None

    @property
    def allowed(self) -> bool:
        return self.verdict is ActionPolicyVerdictV2.ALLOW


class StaticActionPolicyEngineV2:
    def __init__(self, rules: Mapping[str, ActionPolicyRuleV2]) -> None:
        self._rules = dict(rules)

    def evaluate(self, intent: ActionIntentV2, context: ActionPolicyContextV2) -> ActionPolicyDecisionV2:
        validate_action_intent_v2(intent)
        if context.now.tzinfo is None:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_CLOCK_INVALID", intent.policy_class)
        if intent.action_kind is ActionKindV2.NAVIGATE:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.ALLOW, "NAVIGATION_READ_ONLY", None)
        policy_class = str(intent.policy_class)
        rule = self._rules.get(policy_class)
        if rule is None:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_CLASS_UNKNOWN", policy_class)
        if not rule.enabled:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_RULE_DISABLED", policy_class)
        if rule.valid_until is not None and (rule.valid_until.tzinfo is None or rule.valid_until <= context.now):
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_RULE_EXPIRED", policy_class)
        if context.autonomy_mode not in rule.allowed_modes:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "AUTONOMY_MODE_FORBIDDEN", policy_class)
        if intent.actor_kind not in rule.allowed_actors:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_ACTOR_FORBIDDEN", policy_class)
        if context.stale_data and rule.deny_on_stale_data:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.DENY, "POLICY_STALE_DATA", policy_class)
        if intent.requires_approval and not context.approval_granted:
            return ActionPolicyDecisionV2(ActionPolicyVerdictV2.REQUIRE_APPROVAL, "OPERATOR_APPROVAL_REQUIRED", policy_class, rule.risk_guard_code)
        return ActionPolicyDecisionV2(ActionPolicyVerdictV2.ALLOW, "POLICY_ALLOWED", policy_class, rule.risk_guard_code)
