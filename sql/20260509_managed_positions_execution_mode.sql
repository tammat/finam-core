ALTER TABLE managed_positions
ADD COLUMN IF NOT EXISTS execution_mode TEXT NOT NULL DEFAULT 'manual';

UPDATE managed_positions
SET execution_mode = 'manual'
WHERE execution_mode IS NULL OR execution_mode = '';

CREATE INDEX IF NOT EXISTS idx_managed_positions_execution_mode
ON managed_positions (execution_mode);
