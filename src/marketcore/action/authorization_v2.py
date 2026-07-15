from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from marketcore.action.contract_v2 import ActionIntentV2, validate_action_intent_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2


class AuthorizationVerdictV2(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class AuthorizationGrantV2:
    actor_id: str
    scopes: frozenset[str]
    expires_at: datetime | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AuthorizationDecisionV2:
    verdict: AuthorizationVerdictV2
    reason_code: str
    actor_id: str
    required_scope: str | None

    @property
    def allowed(self) -> bool:
        return self.verdict is AuthorizationVerdictV2.ALLOW


def _scope_matches(granted_scope: str, required_scope: str) -> bool:
    if granted_scope == required_scope or granted_scope == "*":
        return True
    return granted_scope.endswith(":*") and required_scope.startswith(granted_scope[:-1])


class ScopeAuthorizationEngineV2:
    def authorize(
        self,
        intent: ActionIntentV2,
        grant: AuthorizationGrantV2 | None,
        *,
        now: datetime,
    ) -> AuthorizationDecisionV2:
        validate_action_intent_v2(intent)
        if now.tzinfo is None:
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_CLOCK_INVALID", intent.actor_id, intent.authorization_scope)
        if intent.action_kind is ActionKindV2.NAVIGATE:
            return AuthorizationDecisionV2(
                AuthorizationVerdictV2.ALLOW,
                "NAVIGATION_READ_ONLY",
                intent.actor_id,
                None,
            )
        required_scope = intent.authorization_scope
        if grant is None:
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_GRANT_MISSING", intent.actor_id, required_scope)
        if not grant.enabled:
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_GRANT_DISABLED", intent.actor_id, required_scope)
        if grant.actor_id != intent.actor_id:
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_ACTOR_MISMATCH", intent.actor_id, required_scope)
        if grant.expires_at is not None and (grant.expires_at.tzinfo is None or grant.expires_at <= now):
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_GRANT_EXPIRED", intent.actor_id, required_scope)
        if not any(_scope_matches(scope, str(required_scope)) for scope in grant.scopes):
            return AuthorizationDecisionV2(AuthorizationVerdictV2.DENY, "AUTHORIZATION_SCOPE_MISSING", intent.actor_id, required_scope)
        return AuthorizationDecisionV2(AuthorizationVerdictV2.ALLOW, "AUTHORIZATION_SCOPE_GRANTED", intent.actor_id, required_scope)
