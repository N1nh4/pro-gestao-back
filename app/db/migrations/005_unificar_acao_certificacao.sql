-- =============================================================================
-- Pró-Gestão RPPS — Migração 005: tabelas únicas `acao` e `certificacao`
-- PostgreSQL
--
-- Objetivo: uma tabela só para cada conceito.
--
--   acoes + plano_acao  ->  acao
--     (ação e seu plano passam a ser o mesmo registro, sempre por ID)
--
--   certificacao + certificacoes  ->  certificacao
--     (a certificação do ente passa a carregar também o manual e o nível)
--
-- Estrutura final:
--
--   certificacao 1 --- N acao
--   requisito    1 --- N acao
--   item         1 --- N acao   (o item precisa pertencer ao requisito)
--   unidades     1 --- N acao
--   tenants      1 --- N certificacao
--
-- Sem denormalização: nomes (manual, nível, requisito, item, unidade) são
-- obtidos por JOIN.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Pré-requisitos
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('acoes') IS NULL OR to_regclass('plano_acao') IS NULL THEN
        RAISE EXCEPTION 'Tabelas acoes/plano_acao ausentes; execute a migração 003 antes.';
    END IF;
    IF to_regclass('certificacao') IS NULL OR to_regclass('certificacoes') IS NULL THEN
        RAISE EXCEPTION 'Tabelas certificacao/certificacoes ausentes; execute a migração 003 antes.';
    END IF;
END $$;

-- =============================================================================
-- 1. CERTIFICACAO — acrescenta os dados da certificação do ente
-- =============================================================================
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS tenant_id            VARCHAR(36);
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS status               VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS numero_certificado   VARCHAR(50);
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS data_certificacao     DATE;
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS data_validade        DATE;
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS entidade_certificadora VARCHAR(200);
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS criado_em            TIMESTAMP NOT NULL DEFAULT now();
ALTER TABLE certificacao ADD COLUMN IF NOT EXISTS atualizado_em        TIMESTAMP NOT NULL DEFAULT now();

-- As linhas do catálogo (manual x nível) passam a pertencer a um ente.
UPDATE certificacao c
   SET tenant_id = (SELECT t.id FROM tenants t ORDER BY t.id LIMIT 1)
 WHERE c.tenant_id IS NULL;

-- Cópia das certificações para os demais entes.
INSERT INTO certificacao (
    id_manual, id_nivel, tenant_id, nome_certificacao, status,
    numero_certificado, data_certificacao, data_validade,
    entidade_certificadora, criado_em, atualizado_em
)
SELECT c.id_manual, c.id_nivel, t.id, c.nome_certificacao, c.status,
       c.numero_certificado, c.data_certificacao, c.data_validade,
       c.entidade_certificadora, c.criado_em, now()
  FROM certificacao c
 CROSS JOIN tenants t
 WHERE NOT EXISTS (
        SELECT 1 FROM certificacao x
         WHERE x.id_manual = c.id_manual
           AND x.id_nivel  = c.id_nivel
           AND x.tenant_id = t.id
       );

-- Certificações que ainda não existem (manual novo ou ente novo): um por nível.
INSERT INTO certificacao (
    id_manual, id_nivel, tenant_id, nome_certificacao, status,
    criado_em, atualizado_em
)
SELECT m.id_manual, n.id_nivel, t.id,
       'Certificação Pró-Gestão — Nível ' || n.nome_nivel, 'PENDENTE',
       now(), now()
  FROM manual m
 CROSS JOIN nivel n
 CROSS JOIN tenants t
 WHERE NOT EXISTS (
        SELECT 1 FROM certificacao x
         WHERE x.id_manual = m.id_manual
           AND x.id_nivel  = n.id_nivel
           AND x.tenant_id = t.id
       );

-- Unicidade agora por ente + manual + nível.
ALTER TABLE certificacao DROP CONSTRAINT IF EXISTS uq_certificacao_manual_nivel;
ALTER TABLE certificacao ADD CONSTRAINT uq_certificacao_tenant_manual_nivel
    UNIQUE (tenant_id, id_manual, id_nivel);

ALTER TABLE certificacao ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_certificacao_tenant'
    ) THEN
        ALTER TABLE certificacao
            ADD CONSTRAINT fk_certificacao_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
            ON UPDATE CASCADE ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_certificacao_tenant ON certificacao (tenant_id);

-- Dados legados de `certificacoes` (certificação do ente) para a linha
-- equivalente da tabela única (nível no manual mais recente).
UPDATE certificacao x
   SET status                = upper(c.status),
       numero_certificado    = c.numero_certificado,
       data_certificacao     = c.data_certificacao,
       data_validade         = c.data_validade,
       entidade_certificadora = c.entidade_certificadora
  FROM certificacoes c
  JOIN nivel n ON n.nome_nivel = c.nivel
 WHERE c.tenant_id = x.tenant_id
   AND x.id_nivel  = n.id_nivel
   AND x.id_manual = (SELECT max(id_manual) FROM manual);

COMMENT ON TABLE certificacao IS
    'Certificação do ente: um registro por (ente, manual, nível), com status, número, datas e entidade certificadora.';
COMMENT ON COLUMN certificacao.status IS
    'PENDENTE | VIGENTE | VENCIDA | REVOGADA';

DROP TABLE IF EXISTS certificacoes;

-- =============================================================================
-- 2. ACAO — tabela única (ação + plano)
-- =============================================================================
CREATE TABLE IF NOT EXISTS acao (
    id_acao         INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       VARCHAR(36)  NOT NULL,
    id_certificacao INTEGER      NOT NULL,
    id_requisito    INTEGER      NOT NULL,
    id_item         INTEGER,
    id_unidade      VARCHAR(36)  NOT NULL,
    nome            VARCHAR(300) NOT NULL,
    descricao       TEXT         NOT NULL,
    prazo           DATE         NOT NULL,
    data_envio      DATE,
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDENTE',
    data_aprovacao  DATE,
    criado_por      VARCHAR(36),
    criado_em       TIMESTAMP    NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMP    NOT NULL DEFAULT now(),

    CONSTRAINT fk_acao_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenants (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_acao_certificacao
        FOREIGN KEY (id_certificacao)
        REFERENCES certificacao (id_certificacao)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_acao_requisito
        FOREIGN KEY (id_requisito)
        REFERENCES requisito (id_requisito)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    -- o item, quando informado, precisa pertencer ao requisito da ação
    CONSTRAINT fk_acao_item
        FOREIGN KEY (id_item, id_requisito)
        REFERENCES item (id_item, id_requisito)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_acao_unidade
        FOREIGN KEY (id_unidade)
        REFERENCES unidades (id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT fk_acao_criado_por
        FOREIGN KEY (criado_por)
        REFERENCES usuarios (id)
        ON UPDATE CASCADE ON DELETE SET NULL,

    CONSTRAINT ck_acao_status
        CHECK (status IN ('PENDENTE', 'ENVIADO', 'APROVADO', 'DILIGÊNCIA'))
);

CREATE INDEX IF NOT EXISTS ix_acao_tenant       ON acao (tenant_id);
CREATE INDEX IF NOT EXISTS ix_acao_certificacao ON acao (id_certificacao);
CREATE INDEX IF NOT EXISTS ix_acao_requisito    ON acao (id_requisito);
CREATE INDEX IF NOT EXISTS ix_acao_item         ON acao (id_item);
CREATE INDEX IF NOT EXISTS ix_acao_unidade      ON acao (id_unidade);
CREATE INDEX IF NOT EXISTS ix_acao_status       ON acao (status, prazo);

COMMENT ON TABLE acao IS
    'Ação do plano: requisito, item, unidade, prazo e status — tudo por ID.';
COMMENT ON COLUMN acao.id_certificacao IS
    'Certificação (ente, manual, nível) à qual a ação pertence.';
COMMENT ON COLUMN acao.nome IS
    'Título da ação.';
COMMENT ON COLUMN acao.descricao IS
    'Descrição do que deve ser comprovado ou executado.';
COMMENT ON COLUMN acao.data_envio IS
    'Data em que a ação foi enviada (status ENVIADO).';
COMMENT ON COLUMN acao.data_aprovacao IS
    'Data em que a ação foi aprovada (status APROVADO).';

-- ---------------------------------------------------------------------------
-- 2.1 Certificação destino da ação: ente + manual do requisito + nível do item
--     (fallback: nível mais baixo do manual; depois: qualquer certificação do ente)
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 2.2 Migração dos dados: acoes + plano_acao -> acao
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE tmp_acao_map (
    old_id VARCHAR(10) PRIMARY KEY,
    new_id INTEGER NOT NULL
) ON COMMIT DROP;

-- Ações que já tinham plano: os dados do plano prevalecem.
WITH src AS (
    SELECT
        a.id_acao                              AS old_id,
        a.tenant_id,
        COALESCE(
            (SELECT c.id_certificacao
               FROM certificacao c
               JOIN nivel n ON n.id_nivel = c.id_nivel
              WHERE c.tenant_id = a.tenant_id
                AND c.id_manual = (SELECT r.id_manual FROM requisito r
                                    WHERE r.id_requisito = p.id_requisito)
                AND n.nome_nivel = (SELECT i.nivel FROM item i
                                     WHERE i.id_item = p.id_item)
              LIMIT 1),
            (SELECT c.id_certificacao
               FROM certificacao c
               JOIN nivel n ON n.id_nivel = c.id_nivel
              WHERE c.tenant_id = a.tenant_id
                AND c.id_manual = (SELECT r.id_manual FROM requisito r
                                    WHERE r.id_requisito = p.id_requisito)
              ORDER BY n.nome_nivel
              LIMIT 1),
            (SELECT c.id_certificacao
               FROM certificacao c
              WHERE c.tenant_id = a.tenant_id
              ORDER BY c.id_certificacao
              LIMIT 1)
        )                                    AS id_certificacao,
        p.id_requisito,
        p.id_item,
        p.id_unidade,
        p.nome_acao                            AS nome,
        p.descricao_acao                       AS descricao,
        p.prazo,
        COALESCE(p.data_envio, a.dt_envio)     AS data_envio,
        p.status,
        a.dt_aprovacao                         AS data_aprovacao,
        a.criado_por,
        COALESCE(a.criado_em, now())           AS criado_em,
        ROW_NUMBER() OVER (ORDER BY a.id_acao) AS new_id
      FROM acoes a
      JOIN plano_acao p ON p.id_acao = a.id_acao
),
ins AS (
    INSERT INTO acao (
        id_acao, tenant_id, id_certificacao, id_requisito, id_item, id_unidade,
        nome, descricao, prazo, data_envio, status, data_aprovacao,
        criado_por, criado_em, atualizado_em
    )
    OVERRIDING SYSTEM VALUE
    SELECT new_id, tenant_id, id_certificacao, id_requisito, id_item, id_unidade,
           nome, descricao, prazo, data_envio, status, data_aprovacao,
           criado_por, criado_em, now()
      FROM src
    RETURNING id_acao
)
INSERT INTO tmp_acao_map (old_id, new_id)
SELECT old_id, new_id FROM src;

-- Ações legadas sem plano.
WITH src AS (
    SELECT
        a.id_acao                              AS old_id,
        a.tenant_id,
        COALESCE(
            (SELECT c.id_certificacao
               FROM certificacao c
               JOIN nivel n ON n.id_nivel = c.id_nivel
              WHERE c.tenant_id = a.tenant_id
                AND c.id_manual = (SELECT r.id_manual FROM requisito r
                                    WHERE r.id_requisito = a.requisito_id)
                AND n.nome_nivel = (SELECT i.nivel FROM item i
                                     WHERE i.id_item = (
                                           SELECT p.id_item FROM plano_acao p
                                            WHERE p.id_acao = a.id_acao))
              LIMIT 1),
            (SELECT c.id_certificacao
               FROM certificacao c
               JOIN nivel n ON n.id_nivel = c.id_nivel
              WHERE c.tenant_id = a.tenant_id
                AND c.id_manual = (SELECT r.id_manual FROM requisito r
                                    WHERE r.id_requisito = a.requisito_id)
              ORDER BY n.nome_nivel
              LIMIT 1),
            (SELECT c.id_certificacao
               FROM certificacao c
              WHERE c.tenant_id = a.tenant_id
              ORDER BY c.id_certificacao
              LIMIT 1)
        )                                    AS id_certificacao,
        a.requisito_id                        AS id_requisito,
        NULL::INTEGER                         AS id_item,
        a.unidade_id                          AS id_unidade,
        a.descricao_acao                      AS nome,
        a.descricao_acao                      AS descricao,
        a.prazo,
        a.dt_envio                            AS data_envio,
        a.status,
        a.dt_aprovacao                        AS data_aprovacao,
        a.criado_por,
        COALESCE(a.criado_em, now())           AS criado_em,
        ROW_NUMBER() OVER (ORDER BY a.id_acao)
            + (SELECT COALESCE(max(new_id), 0) FROM tmp_acao_map) AS new_id
      FROM acoes a
      LEFT JOIN plano_acao p ON p.id_acao = a.id_acao
     WHERE p.id_acao IS NULL
),
ins AS (
    INSERT INTO acao (
        id_acao, tenant_id, id_certificacao, id_requisito, id_item, id_unidade,
        nome, descricao, prazo, data_envio, status, data_aprovacao,
        criado_por, criado_em, atualizado_em
    )
    OVERRIDING SYSTEM VALUE
    SELECT new_id, tenant_id, id_certificacao, id_requisito, id_item, id_unidade,
           nome, descricao, prazo, data_envio, status, data_aprovacao,
           criado_por, criado_em, now()
      FROM src
    RETURNING id_acao
)
INSERT INTO tmp_acao_map (old_id, new_id)
SELECT old_id, new_id FROM src;

-- Ajusta a sequência de identidade para os próximos inserts.
SELECT setval(
    pg_get_serial_sequence('acao', 'id_acao'),
    COALESCE((SELECT max(id_acao) FROM acao), 0) + 1,
    false
);

-- =============================================================================
-- 3. Tabelas filhas: historico_acoes, diligencias, documentos e GED
-- =============================================================================
ALTER TABLE historico_acoes DROP CONSTRAINT IF EXISTS historico_acoes_acao_id_fkey;
ALTER TABLE diligencias     DROP CONSTRAINT IF EXISTS diligencias_acao_id_fkey;
ALTER TABLE documentos      DROP CONSTRAINT IF EXISTS documentos_acao_id_fkey;

-- Linhas órfãs (sem ação correspondente) não sobrevivem à conversão.
DELETE FROM historico_acoes h
 WHERE h.acao_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM tmp_acao_map m WHERE m.old_id = h.acao_id);
DELETE FROM diligencias d
 WHERE d.acao_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM tmp_acao_map m WHERE m.old_id = d.acao_id);
DELETE FROM documentos doc
 WHERE doc.acao_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM tmp_acao_map m WHERE m.old_id = doc.acao_id);

-- Converte o código da ação (AC-001) no id numérico da tabela única.
UPDATE historico_acoes h
   SET acao_id = (SELECT m.new_id FROM tmp_acao_map m WHERE m.old_id = h.acao_id)
 WHERE h.acao_id IS NOT NULL;
UPDATE diligencias d
   SET acao_id = (SELECT m.new_id FROM tmp_acao_map m WHERE m.old_id = d.acao_id)
 WHERE d.acao_id IS NOT NULL;
UPDATE documentos doc
   SET acao_id = (SELECT m.new_id FROM tmp_acao_map m WHERE m.old_id = doc.acao_id)
 WHERE doc.acao_id IS NOT NULL;
UPDATE tarefas t
   SET acao_id = (SELECT m.new_id FROM tmp_acao_map m WHERE m.old_id = t.acao_id)
 WHERE t.acao_id IS NOT NULL;
UPDATE evidencias e
   SET acao_id = (SELECT m.new_id FROM tmp_acao_map m WHERE m.old_id = e.acao_id)
 WHERE e.acao_id IS NOT NULL;

ALTER TABLE historico_acoes ALTER COLUMN acao_id TYPE INTEGER USING acao_id::integer;
ALTER TABLE diligencias     ALTER COLUMN acao_id TYPE INTEGER USING acao_id::integer;
ALTER TABLE documentos      ALTER COLUMN acao_id TYPE INTEGER USING acao_id::integer;
ALTER TABLE tarefas         ALTER COLUMN acao_id TYPE INTEGER USING acao_id::integer;
ALTER TABLE evidencias      ALTER COLUMN acao_id TYPE INTEGER USING acao_id::integer;

ALTER TABLE historico_acoes
    ADD CONSTRAINT historico_acoes_acao_id_fkey
    FOREIGN KEY (acao_id) REFERENCES acao (id_acao)
    ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE diligencias
    ADD CONSTRAINT diligencias_acao_id_fkey
    FOREIGN KEY (acao_id) REFERENCES acao (id_acao)
    ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE documentos
    ADD CONSTRAINT documentos_acao_id_fkey
    FOREIGN KEY (acao_id) REFERENCES acao (id_acao)
    ON UPDATE CASCADE ON DELETE CASCADE;

-- =============================================================================
-- 4. Limpeza das tabelas substituídas
-- =============================================================================
DROP TABLE IF EXISTS plano_acao;
DROP TABLE IF EXISTS acoes;

COMMIT;
