import pytest

from marketcore.action.contract_v2 import (
    ActionActorKindV2,
    ActionContractErrorV2,
    ActionIntentV2,
    InteractionKindV2,
    action_intent_from_render_action_v2,
    validate_action_intent_v2,
)
from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderActionV2


@pytest.mark.parametrize("interaction", tuple(InteractionKindV2))
def test_navigation_is_explicit_for_click_and_double_click(interaction: InteractionKindV2) -> None:
    intent = action_intent_from_render_action_v2(
        RenderActionV2(
            action_id="navigation.open.research",
            action_kind=ActionKindV2.NAVIGATE,
            target_id="container.research",
        ),
        interaction_kind=interaction,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id="operator.test",
    )
    assert intent.interaction_kind is interaction
    assert intent.target_id == "container.research"
    assert intent.command_code is None


def test_reversible_command_requires_rollback() -> None:
    with pytest.raises(ActionContractErrorV2, match="ACTION_ROLLBACK_CODE_REQUIRED"):
        validate_action_intent_v2(
            ActionIntentV2(
                action_id="research.refresh",
                action_kind=ActionKindV2.COMMAND,
                interaction_kind=InteractionKindV2.DOUBLE_CLICK,
                actor_kind=ActionActorKindV2.OPERATOR,
                actor_id="operator.test",
                command_code="RESEARCH.REFRESH",
                policy_class="RESEARCH_MAINTENANCE",
                authorization_scope="research:write",
                reversible=True,
                idempotency_key="test-refresh-1",
            )
        )


def test_irreversible_command_requires_approval() -> None:
    with pytest.raises(ActionContractErrorV2, match="IRREVERSIBLE_ACTION_APPROVAL_REQUIRED"):
        validate_action_intent_v2(
            ActionIntentV2(
                action_id="research.stop",
                action_kind=ActionKindV2.COMMAND,
                interaction_kind=InteractionKindV2.DOUBLE_CLICK,
                actor_kind=ActionActorKindV2.OPERATOR,
                actor_id="operator.test",
                command_code="RESEARCH.STOP",
                policy_class="RESEARCH_MAINTENANCE",
                authorization_scope="research:write",
                idempotency_key="test-stop-1",
            )
        )


@pytest.mark.parametrize("actor", [ActionActorKindV2.OPERATOR, ActionActorKindV2.AI])
def test_ui_and_ai_cannot_submit_broker_orders(actor: ActionActorKindV2) -> None:
    with pytest.raises(ActionContractErrorV2, match="DIRECT_EXECUTION_FORBIDDEN"):
        validate_action_intent_v2(
            ActionIntentV2(
                action_id="execution.submit",
                action_kind=ActionKindV2.CONFIRM,
                interaction_kind=InteractionKindV2.DOUBLE_CLICK,
                actor_kind=actor,
                actor_id="actor.test",
                command_code="BROKER.SUBMIT_ORDER",
                policy_class="LIVE_EXECUTION",
                authorization_scope="execution:submit",
                requires_approval=True,
                idempotency_key="test-order-1",
            )
        )


def test_valid_reversible_command_is_accepted() -> None:
    intent = validate_action_intent_v2(
        ActionIntentV2(
            action_id="research.refresh",
            action_kind=ActionKindV2.COMMAND,
            interaction_kind=InteractionKindV2.DOUBLE_CLICK,
            actor_kind=ActionActorKindV2.OPERATOR,
            actor_id="operator.test",
            command_code="RESEARCH.REFRESH",
            policy_class="RESEARCH_MAINTENANCE",
            authorization_scope="research:write",
            reversible=True,
            rollback_code="RESEARCH.RESTORE_PREVIOUS_SNAPSHOT",
            idempotency_key="test-refresh-2",
        )
    )
    assert intent.rollback_code == "RESEARCH.RESTORE_PREVIOUS_SNAPSHOT"
