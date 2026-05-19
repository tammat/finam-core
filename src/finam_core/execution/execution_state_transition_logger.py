from __future__ import annotations


class ExecutionStateTransitionLogger:
    """Русский комментарий: единая запись переходов execution_intents."""

    def ensure_table(self, cur) -> None:
        cur.execute("""
            create table if not exists execution_state_transitions (
                id bigserial primary key,
                created_at timestamptz not null default now(),
                intent_id bigint not null,
                previous_state text not null,
                next_state text not null,
                reason text,
                raw_json jsonb not null default '{}'::jsonb
            )
        """)

    def log(
        self,
        cur,
        *,
        intent_id: int,
        previous_state: str,
        next_state: str,
        reason: str = "",
    ) -> None:
        self.ensure_table(cur)

        cur.execute("""
            insert into execution_state_transitions (
                intent_id,
                previous_state,
                next_state,
                reason,
                raw_json
            )
            values (
                %s,
                %s,
                %s,
                %s,
                jsonb_build_object(
                    'source',
                    'execution_state_transition_logger'
                )
            )
        """, (
            intent_id,
            previous_state,
            next_state,
            reason,
        ))
