-- =============================================================================
-- Pró-Gestão RPPS — Migração 003: nível, certificação e plano de ação
-- PostgreSQL
--
-- Relacionamentos:
--   nivel      1 --- N certificacao
--   manual     1 --- N certificacao        (uma certificação por nível/manual)
--   acoes      1 --- N plano_acao
--   requisito  1 --- N plano_acao
--   item       1 --- N plano_acao          (opcional; precisa pertencer ao requisito)
--   unidades   1 --- N plano_acao
--
-- Sem denormalização: os nomes (manual, nível, requisito, item, unidade) são
-- obtidos por JOIN. Todas as relações usam o id (PK da tabela referenciada).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Pré-requisitos
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('manual') IS NULL OR to_regclass('item') IS NULL THEN
        RAISE EXCEPTION 'Execute antes 001_manual_requisito_item.sql (tabelas manual/item ausentes).';
    END IF;
    IF to_regclass('requisito') IS NULL OR to_regclass('acoes') IS NULL THEN
        RAISE EXCEPTION 'Tabelas requisito/acoes ausentes; execute as migrações anteriores.';
    END IF;
    IF to_regclass('unidades') IS NULL THEN
        RAISE EXCEPTION 'Tabela unidades não encontrada.';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Alvos de chave estrangeira composta (apenas acrescentam unicidade)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    -- o item, quando informado, precisa pertencer ao requisito da ação
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_item_id_req') THEN
        ALTER TABLE item ADD CONSTRAINT uq_item_id_req UNIQUE (id_item, id_requisito);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- NIVEL — domínio I–IV
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nivel (
    id_nivel   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_nivel VARCHAR(10) NOT NULL,

    CONSTRAINT uq_nivel_nome UNIQUE (nome_nivel),
    CONSTRAINT ck_nivel_nome CHECK (nome_nivel IN ('I', 'II', 'III', 'IV'))
);

COMMENT ON TABLE nivel IS
    'Níveis de certificação do Pró-Gestão: I, II, III e IV.';

INSERT INTO nivel (nome_nivel) VALUES ('I'), ('II'), ('III'), ('IV')
ON CONFLICT (nome_nivel) DO NOTHING;

-- ---------------------------------------------------------------------------
-- CERTIFICACAO — uma por nível em cada manual
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certificacao (
    id_certificacao INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_manual       INTEGER      NOT NULL,
    id_nivel        INTEGER      NOT NULL,
    nome_certificacao VARCHAR(200) NOT NULL,

    CONSTRAINT fk_certificacao_manual
        FOREIGN KEY (id_manual)
        REFERENCES manual (id_manual)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_certificacao_nivel
        FOREIGN KEY (id_nivel)
        REFERENCES nivel (id_nivel)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT uq_certificacao_manual_nivel UNIQUE (id_manual, id_nivel)
);

CREATE INDEX IF NOT EXISTS ix_certificacao_nivel ON certificacao (id_nivel);
CREATE INDEX IF NOT EXISTS ix_certificacao_manual ON certificacao (id_manual);

COMMENT ON TABLE certificacao IS
    'Certificações oferecidas por um manual, uma por nível (I a IV).';

-- ---------------------------------------------------------------------------
-- PLANO_ACAO — a ação do plano, por requisito, item (opcional) e unidade
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plano_acao (
    id_plano_acao  INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_acao        VARCHAR(10)  NOT NULL,
    id_requisito   INTEGER      NOT NULL,
    id_item        INTEGER,
    id_unidade     VARCHAR(36)  NOT NULL,
    nome_acao      VARCHAR(300) NOT NULL,
    descricao_acao TEXT         NOT NULL,
    prazo          DATE         NOT NULL,
    data_envio     DATE,
    status         VARCHAR(20)  NOT NULL DEFAULT 'PENDENTE',

    CONSTRAINT fk_plano_acao_acao
        FOREIGN KEY (id_acao)
        REFERENCES acoes (id_acao)
        ON UPDATE CASCADE ON DELETE CASCADE,

    CONSTRAINT fk_plano_acao_requisito
        FOREIGN KEY (id_requisito)
        REFERENCES requisito (id_requisito)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    -- o item, quando informado, precisa pertencer ao requisito desta ação
    CONSTRAINT fk_plano_acao_item
        FOREIGN KEY (id_item, id_requisito)
        REFERENCES item (id_item, id_requisito)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_plano_acao_unidade
        FOREIGN KEY (id_unidade)
        REFERENCES unidades (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_plano_acao_status
        CHECK (status IN ('PENDENTE', 'ENVIADO', 'APROVADO', 'DILIGÊNCIA'))
);

CREATE INDEX IF NOT EXISTS ix_plano_acao_acao      ON plano_acao (id_acao);
CREATE INDEX IF NOT EXISTS ix_plano_acao_requisito ON plano_acao (id_requisito);
CREATE INDEX IF NOT EXISTS ix_plano_acao_item      ON plano_acao (id_item);
CREATE INDEX IF NOT EXISTS ix_plano_acao_unidade   ON plano_acao (id_unidade);
CREATE INDEX IF NOT EXISTS ix_plano_acao_status    ON plano_acao (status, prazo);

COMMENT ON TABLE  plano_acao IS
    'Ações do plano: por ação (acoes), requisito, item opcional e unidade responsável.';
COMMENT ON COLUMN plano_acao.id_acao IS
    'Ação da tabela acoes à qual o item do plano pertence.';
COMMENT ON COLUMN plano_acao.prazo IS
    'Data limite da ação.';
COMMENT ON COLUMN plano_acao.data_envio IS
    'Data em que a ação foi enviada (status ENVIADO).';
COMMENT ON COLUMN plano_acao.status IS
    'PENDENTE | ENVIADO | APROVADO | DILIGÊNCIA';

COMMIT;
