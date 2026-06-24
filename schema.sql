-- ============================================================
--  Barbearia Dom Carlo — Schema MySQL
--  Rode: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS barbearia
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE barbearia;

-- ------------------------------------------------------------
-- Usuarios do painel administrativo
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
  id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  username    VARCHAR(60)     NOT NULL UNIQUE,
  nome        VARCHAR(120)    NOT NULL,
  senha_hash  VARCHAR(255)    NOT NULL,
  criado_em   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Pedidos recebidos pelo site
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
  id                INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  nome              VARCHAR(120)    NOT NULL,
  whatsapp          VARCHAR(20)     NOT NULL,
  data_agendamento  DATE            NOT NULL,
  horario           VARCHAR(10)     NOT NULL,
  barbeiro          VARCHAR(80)     NOT NULL DEFAULT 'Qualquer disponivel',
  total             DECIMAL(8,2)    NOT NULL DEFAULT 0,
  status            ENUM(
                      'pendente',
                      'confirmado',
                      'concluido',
                      'cancelado'
                    )               NOT NULL DEFAULT 'pendente',
  criado_em         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_status          (status),
  INDEX idx_data_agendamento(data_agendamento),
  INDEX idx_criado_em       (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Servicos de cada pedido (relacao 1:N)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedido_servicos (
  id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  pedido_id   INT UNSIGNED    NOT NULL,
  nome        VARCHAR(100)    NOT NULL,
  preco       DECIMAL(8,2)    NOT NULL DEFAULT 0,
  duracao     VARCHAR(20)     NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  CONSTRAINT fk_ps_pedido
    FOREIGN KEY (pedido_id)
    REFERENCES pedidos(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Usuarios padrão
-- Senhas geradas com werkzeug.security.generate_password_hash()
--
--   domcarlo → barbearia2024
--   dev      → devadmin123
--
-- Para gerar outra senha rode no terminal Python:
--   from werkzeug.security import generate_password_hash
--   print(generate_password_hash("sua_senha"))
-- ------------------------------------------------------------
INSERT INTO usuarios (username, nome, senha_hash) VALUES
(
  'domcarlo',
  'Dom Carlo (Dono)',
  'pbkdf2:sha256:600000$barbearia$8a3f2c1d4e5b6a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c'
),
(
  'dev',
  'Desenvolvedor',
  'pbkdf2:sha256:600000$devadmin$1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b'
)
ON DUPLICATE KEY UPDATE username = username;

-- ------------------------------------------------------------
-- ATENÇÃO: os hashes acima são de exemplo e NÃO funcionam.
-- Gere os hashes reais rodando este script Python UMA VEZ:
--
--   python gerar_senhas.py
--
-- Ele vai imprimir os INSERT corretos para copiar aqui.
-- Ou use o comando abaixo diretamente no MySQL após rodar
-- o server.py pelo menos uma vez com debug=True e chamar:
--   POST /api/admin/setup  (apenas em modo debug)
-- ------------------------------------------------------------

-- View útil para relatórios rápidos
CREATE OR REPLACE VIEW vw_pedidos_resumo AS
SELECT
  p.id,
  p.nome,
  p.whatsapp,
  p.data_agendamento,
  p.horario,
  p.barbeiro,
  p.total,
  p.status,
  p.criado_em,
  GROUP_CONCAT(ps.nome ORDER BY ps.id SEPARATOR ', ') AS servicos_lista,
  COUNT(ps.id) AS qtd_servicos
FROM pedidos p
LEFT JOIN pedido_servicos ps ON ps.pedido_id = p.id
GROUP BY p.id;
