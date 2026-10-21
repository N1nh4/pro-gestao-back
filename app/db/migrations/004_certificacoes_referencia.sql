-- 004: certificações de referência do manual 4.1 (uma por nível I–IV).
-- Idempotente: pode ser reaplicado sem duplicar.

INSERT INTO certificacao (id_manual, id_nivel, nome_certificacao)
SELECT m.id_manual,
       n.id_nivel,
       'Certificação Pró-Gestão — Nível ' || n.nome_nivel
FROM manual m
CROSS JOIN nivel n
WHERE m.versao_manual = '4.1'
ON CONFLICT (id_manual, id_nivel) DO NOTHING;
