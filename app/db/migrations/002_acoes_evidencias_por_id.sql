-- =============================================================================
-- Pró-Gestão RPPS — Migração 002: acoes.evidencias passam a referenciar por ID
-- PostgreSQL
--
-- Troca a referência textual `requisito_cod` por `id_requisito` (FK para
-- requisito.id_requisito). As tabelas estão vazias, então não há dados a
-- converter — apenas a estrutura muda.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- acoes
-- ---------------------------------------------------------------------------
ALTER TABLE acoes DROP CONSTRAINT IF EXISTS acoes_requisito_cod_fkey;
ALTER TABLE acoes DROP COLUMN IF EXISTS requisito_cod;

ALTER TABLE acoes
    ADD COLUMN IF NOT EXISTS requisito_id INTEGER
        REFERENCES requisito (id_requisito)
        ON UPDATE CASCADE
        ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_acoes_requisito_id ON acoes (requisito_id);

COMMENT ON COLUMN acoes.requisito_id IS
    'Requisito do manual ao qual a ação pertence.';

-- ---------------------------------------------------------------------------
-- evidencias  (coluna era texto simples, sem FK)
-- ---------------------------------------------------------------------------
ALTER TABLE evidencias DROP COLUMN IF EXISTS requisito_cod;

ALTER TABLE evidencias
    ADD COLUMN IF NOT EXISTS requisito_id INTEGER
        REFERENCES requisito (id_requisito)
        ON UPDATE CASCADE
        ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_evidencias_requisito_id ON evidencias (requisito_id);

COMMENT ON COLUMN evidencias.requisito_id IS
    'Requisito do manual ao qual a evidência pertence.';

COMMIT;
