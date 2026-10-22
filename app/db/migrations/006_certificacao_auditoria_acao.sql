-- =============================================================================
-- Pró-Gestão RPPS — Migração 006: certificação → auditorias → ações
-- PostgreSQL
--
-- Nova hierarquia:
--
--   certificacao 1 --- N auditoria 1 --- N acao
--
-- - `certificacao` passa a ser o certificado do ente (status, número, datas e
--   entidade certificadora); o manual e o nível saem daqui.
-- - `auditoria` passa a pertencer a uma certificação e seleciona um manual e
--   um nível. É nela que o plano de ação (as ações) é montado.
-- - `acao` deixa de apontar para a certificação e passa a apontar para a
--   auditoria (o manual e o nível são herdados dela).
--
-- Dados de negócio existentes são limpos para re-seed no novo formato
-- (decisão do projeto: limpar e re-semear os dados demo).
-- =============================================================================

BEGIN;

DO $$
BEGIN
    IF to_regclass('certificacao') IS NULL OR to_regclass('auditorias') IS NULL THEN
        RAISE EXCEPTION 'Tabelas certificacao/auditorias ausentes; execute a migração 005 antes.';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 0. Limpeza dos dados de negócio (re-seed no novo formato)
-- ---------------------------------------------------------------------------
DELETE FROM documentos;
DELETE FROM diligencias;
DELETE FROM historico_acoes;
DELETE FROM tarefas;
DELETE FROM evidencias;
DELETE FROM acao;
DELETE FROM auditorias;
DELETE FROM certificacao;

-- =============================================================================
-- 1. CERTIFICACAO — apenas o certificado do ente
-- =============================================================================
ALTER TABLE certificacao DROP CONSTRAINT IF EXISTS uq_certificacao_tenant_manual_nivel;
ALTER TABLE certificacao DROP CONSTRAINT IF EXISTS uq_certificacao_tenant_nome;

DROP INDEX IF EXISTS ix_certificacao_manual;
DROP INDEX IF EXISTS ix_certificacao_nivel;

ALTER TABLE certificacao DROP COLUMN IF EXISTS id_manual;
ALTER TABLE certificacao DROP COLUMN IF EXISTS id_nivel;

ALTER TABLE certificacao
    ADD CONSTRAINT uq_certificacao_tenant_nome UNIQUE (tenant_id, nome_certificacao);

COMMENT ON TABLE certificacao IS
    'Certificado do ente: status, número, datas e entidade certificadora.';
COMMENT ON COLUMN certificacao.status IS
    'PENDENTE | VIGENTE | VENCIDA | REVOGADA';

-- =============================================================================
-- 2. AUDITORIA — pertence à certificação e seleciona manual + nível
-- =============================================================================
ALTER TABLE auditorias ADD COLUMN IF NOT EXISTS id_certificacao INTEGER;
ALTER TABLE auditorias ADD COLUMN IF NOT EXISTS id_manual       INTEGER;
ALTER TABLE auditorias ADD COLUMN IF NOT EXISTS id_nivel        INTEGER;

ALTER TABLE auditorias DROP COLUMN IF EXISTS nivel_auditado;

ALTER TABLE auditorias
    ALTER COLUMN id_certificacao SET NOT NULL,
    ALTER COLUMN id_manual       SET NOT NULL,
    ALTER COLUMN id_nivel        SET NOT NULL;

ALTER TABLE auditorias
    ADD CONSTRAINT fk_auditoria_certificacao
        FOREIGN KEY (id_certificacao)
        REFERENCES certificacao (id_certificacao)
        ON UPDATE CASCADE ON DELETE CASCADE,
    ADD CONSTRAINT fk_auditoria_manual
        FOREIGN KEY (id_manual)
        REFERENCES manual (id_manual)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    ADD CONSTRAINT fk_auditoria_nivel
        FOREIGN KEY (id_nivel)
        REFERENCES nivel (id_nivel)
        ON UPDATE CASCADE ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_auditorias_certificacao ON auditorias (id_certificacao);
CREATE INDEX IF NOT EXISTS ix_auditorias_manual       ON auditorias (id_manual);
CREATE INDEX IF NOT EXISTS ix_auditorias_nivel        ON auditorias (id_nivel);

COMMENT ON TABLE auditorias IS
    'Auditoria de uma certificação: manual, nível, datas, auditor e parecer.';
COMMENT ON COLUMN auditorias.id_certificacao IS
    'Certificação do ente à qual a auditoria pertence.';
COMMENT ON COLUMN auditorias.id_manual IS
    'Manual avaliado nesta auditoria.';
COMMENT ON COLUMN auditorias.id_nivel IS
    'Nível avaliado nesta auditoria (as ações do plano ficam neste nível).';

-- =============================================================================
-- 3. ACAO — pertence a uma auditoria
-- =============================================================================
ALTER TABLE acao DROP CONSTRAINT IF EXISTS fk_acao_certificacao;
DROP INDEX IF EXISTS ix_acao_certificacao;

ALTER TABLE acao DROP COLUMN IF EXISTS id_certificacao;
ALTER TABLE acao ADD COLUMN IF NOT EXISTS id_auditoria VARCHAR(36);

ALTER TABLE acao ALTER COLUMN id_auditoria SET NOT NULL;

ALTER TABLE acao
    ADD CONSTRAINT fk_acao_auditoria
        FOREIGN KEY (id_auditoria)
        REFERENCES auditorias (id)
        ON UPDATE CASCADE ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_acao_auditoria ON acao (id_auditoria);

COMMENT ON COLUMN acao.id_auditoria IS
    'Auditoria (certificação + manual + nível) à qual a ação pertence.';

COMMIT;
