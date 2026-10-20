-- =============================================================================
-- Pró-Gestão RPPS — Migração: Manual > Dimensão > Requisito > Item
-- PostgreSQL
--
-- Relacionamentos:
--   manual    1 --- N requisito
--   dimensao  1 --- N requisito
--   requisito 1 --- N item
--
-- A tabela `requisitos` (legada) tem PK `cod` (texto). A nova tabela
-- `requisito` usa surrogate key `id_requisito` (integer). Como as tabelas
-- dependentes (acoes, requisito_unidade, evidencias) estão vazias, a migração
-- apenas recria a estrutura — não há dados a converter.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Dropa dependentes primeiro (FK para requisitos.cod)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS requisito_unidade CASCADE;
DROP TABLE IF EXISTS requisitos CASCADE;

-- ---------------------------------------------------------------------------
-- Tabela: manual
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manual (
    id_manual     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_manual   VARCHAR(200) NOT NULL,
    versao_manual VARCHAR(20) NOT NULL,
    CONSTRAINT uq_manual_versao UNIQUE (versao_manual)
);

COMMENT ON TABLE manual IS
    'Manual do Pró-Gestão RPPS, com um registro por versão publicada.';
COMMENT ON COLUMN manual.versao_manual IS
    'Versão publicada do manual. Exemplo: 4.1.';

-- ---------------------------------------------------------------------------
-- Tabela: dimensao
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dimensao (
    id_dimensao   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_dimensao VARCHAR(150) NOT NULL,
    CONSTRAINT uq_dimensao_nome UNIQUE (nome_dimensao)
);

COMMENT ON TABLE dimensao IS
    'Dimensões do Manual: Controles Internos, Governança Corporativa e Educação Previdenciária.';

-- ---------------------------------------------------------------------------
-- Tabela: requisito
-- Guarda IDs, sem duplicar nome_manual ou nome_dimensao.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requisito (
    id_requisito   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_manual      INTEGER NOT NULL,
    id_dimensao    INTEGER NOT NULL,
    cod_requisito  VARCHAR(10) NOT NULL,
    nome_requisito VARCHAR(200) NOT NULL,

    CONSTRAINT fk_requisito_manual
        FOREIGN KEY (id_manual)
        REFERENCES manual (id_manual)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_requisito_dimensao
        FOREIGN KEY (id_dimensao)
        REFERENCES dimensao (id_dimensao)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    -- O código é único dentro de cada versão do manual.
    CONSTRAINT uq_requisito_manual_cod
        UNIQUE (id_manual, cod_requisito),

    CONSTRAINT ck_requisito_cod_formato
        CHECK (cod_requisito ~ '^[0-9]+(\.[0-9]+)*$')
);

CREATE INDEX IF NOT EXISTS ix_requisito_dimensao
    ON requisito (id_dimensao);

CREATE INDEX IF NOT EXISTS ix_requisito_manual
    ON requisito (id_manual);

COMMENT ON TABLE requisito IS
    'Requisitos do manual, classificados por dimensão.';
COMMENT ON COLUMN requisito.id_manual IS
    'Manual/versão ao qual o requisito pertence.';
COMMENT ON COLUMN requisito.id_dimensao IS
    'Dimensão à qual o requisito pertence.';

-- ---------------------------------------------------------------------------
-- Tabela: item
-- Guarda id_requisito; o nome do requisito é obtido por JOIN.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item (
    id_item      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_requisito INTEGER NOT NULL,
    nome_item    VARCHAR(300) NOT NULL,
    nivel        VARCHAR(3) NOT NULL,
    descricao    TEXT,

    CONSTRAINT fk_item_requisito
        FOREIGN KEY (id_requisito)
        REFERENCES requisito (id_requisito)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_item_nivel
        CHECK (nivel IN ('I', 'II', 'III', 'IV')),

    CONSTRAINT uq_item_req_nivel_nome
        UNIQUE (id_requisito, nivel, nome_item)
);

CREATE INDEX IF NOT EXISTS ix_item_id_requisito
    ON item (id_requisito);

COMMENT ON TABLE item IS
    'Itens exigidos por requisito em cada nível de certificação (I a IV).';
COMMENT ON COLUMN item.nivel IS
    'Nível de certificação do Pró-Gestão: I, II, III ou IV.';

COMMIT;
