-- Tabelas da semana 3: a nota (pai) e os seus itens (filhos).
-- Os testes criam as tabelas sozinhos. O docker-compose também, na criação do banco.

CREATE TABLE IF NOT EXISTS notas (
    id            SERIAL PRIMARY KEY,
    numero        INTEGER       NOT NULL,
    cnpj_emitente CHAR(14)      NOT NULL,
    uf_origem     CHAR(2)       NOT NULL,
    uf_destino    CHAR(2)       NOT NULL,
    valor_total   NUMERIC(12,2) NOT NULL,
    emitida_em    DATE          NOT NULL,
    UNIQUE (cnpj_emitente, numero)
);

CREATE TABLE IF NOT EXISTS itens (
    id             SERIAL PRIMARY KEY,
    nota_id        INTEGER       NOT NULL REFERENCES notas (id) ON DELETE CASCADE,
    descricao      VARCHAR(120)  NOT NULL,
    cfop           CHAR(4)       NOT NULL CHECK (cfop ~ '^[0-9]{4}$'),
    quantidade     NUMERIC(12,3) NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(12,2) NOT NULL CHECK (valor_unitario >= 0)
);
