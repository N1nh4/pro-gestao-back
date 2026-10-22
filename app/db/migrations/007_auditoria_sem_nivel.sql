-- =============================================================================
-- Pró-Gestão RPPS — Migração 007: auditoria vinculada apenas ao manual
-- PostgreSQL
--
-- A auditoria passa a selecionar somente o manual (o nível deixa de fazer
-- parte do seu escopo). As ações continuam dentro da auditoria e o nível é
-- propriedade do item escolhido no catálogo.
-- =============================================================================

BEGIN;

DO $$
BEGIN
    IF to_regclass('auditorias') IS NULL THEN
        RAISE EXCEPTION 'Tabela auditorias ausente; execute as migrações 005/006 antes.';
    END IF;
END $$;

ALTER TABLE auditorias DROP CONSTRAINT IF EXISTS fk_auditoria_nivel;
DROP INDEX IF EXISTS ix_auditorias_nivel;

ALTER TABLE auditorias DROP COLUMN IF EXISTS id_nivel;

COMMENT ON TABLE auditorias IS
    'Auditoria de uma certificação: manual, datas, auditor e parecer.';
COMMENT ON COLUMN auditorias.id_manual IS
    'Manual avaliado nesta auditoria (as ações do plano pertencem a ele).';

COMMENT ON COLUMN acao.id_auditoria IS
    'Auditoria (certificação + manual) à qual a ação pertence.';

COMMIT;
