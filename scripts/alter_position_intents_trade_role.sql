ALTER TABLE position_intents
ADD COLUMN IF NOT EXISTS trade_role TEXT NOT NULL DEFAULT 'core'
CHECK (trade_role IN ('core', 'hedge', 'speculative', 'watch_only', 'reduce_only'));

ALTER TABLE position_intents
ADD COLUMN IF NOT EXISTS allow_reduce BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE position_intents
ADD COLUMN IF NOT EXISTS allow_increase BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE position_intents
ADD COLUMN IF NOT EXISTS max_position_qty NUMERIC;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS old_trade_role TEXT;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS new_trade_role TEXT;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS old_allow_reduce BOOLEAN;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS new_allow_reduce BOOLEAN;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS old_allow_increase BOOLEAN;

ALTER TABLE position_intent_history
ADD COLUMN IF NOT EXISTS new_allow_increase BOOLEAN;
