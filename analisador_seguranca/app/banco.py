"""Criação do esquema SQLite e gravação atômica de cada análise."""

import sqlite3
from contextlib import closing, contextmanager


ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY, instante TEXT NOT NULL, usuario TEXT NOT NULL,
    ip TEXT NOT NULL, evento TEXT NOT NULL, resultado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY, instante TEXT NOT NULL, regra TEXT NOT NULL,
    usuario TEXT NOT NULL, severidade TEXT NOT NULL, descricao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerta_eventos (
    alerta_id INTEGER NOT NULL REFERENCES alertas(id),
    evento_id INTEGER NOT NULL REFERENCES eventos(id),
    PRIMARY KEY (alerta_id, evento_id)
);
"""


@contextmanager
def abrir_banco(caminho):
    with closing(sqlite3.connect(caminho)) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.executescript(ESQUEMA)
        with conexao:
            yield conexao


def salvar_analise(caminho, eventos, alertas):
    with abrir_banco(caminho) as conexao:
        ids_eventos = {}
        for evento in eventos:
            cursor = conexao.execute(
                "INSERT INTO eventos (instante, usuario, ip, evento, resultado) VALUES (?, ?, ?, ?, ?)",
                (evento.instante.isoformat(), evento.usuario, evento.ip, evento.evento, evento.resultado),
            )
            ids_eventos[evento] = cursor.lastrowid
        for alerta in alertas:
            cursor = conexao.execute(
                "INSERT INTO alertas (instante, regra, usuario, severidade, descricao) VALUES (?, ?, ?, ?, ?)",
                (alerta.instante.isoformat(), alerta.regra, alerta.usuario, alerta.severidade, alerta.descricao),
            )
            conexao.executemany(
                "INSERT INTO alerta_eventos (alerta_id, evento_id) VALUES (?, ?)",
                [(cursor.lastrowid, ids_eventos[evento]) for evento in alerta.eventos_associados],
            )
