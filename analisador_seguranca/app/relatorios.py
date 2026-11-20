"""Consultas agregadas por período. O instante do alerta é o do evento disparador."""

from .banco import abrir_banco


PERIODO = """
    WHERE (:de IS NULL OR instante >= :de) AND (:ate IS NULL OR instante <= :ate)
"""

CONSULTAS = {
    "usuario": f"""
        WITH eventos_por_usuario AS (
            SELECT usuario, COUNT(*) AS total FROM eventos {PERIODO} GROUP BY usuario
        ), alertas_por_usuario AS (
            SELECT usuario, COUNT(*) AS total FROM alertas {PERIODO} GROUP BY usuario
        )
        SELECT e.usuario, e.total, COALESCE(a.total, 0)
        FROM eventos_por_usuario e LEFT JOIN alertas_por_usuario a USING (usuario)
        ORDER BY e.usuario
    """,
    "regra": f"""
        SELECT regra, COUNT(*) FROM alertas {PERIODO} GROUP BY regra ORDER BY regra
    """,
    "severidade": f"""
        WITH niveis(ordem, nome) AS (VALUES (1, 'BAIXA'), (2, 'MÉDIA'), (3, 'ALTA')),
        contagens AS (
            SELECT severidade, COUNT(*) AS total FROM alertas {PERIODO} GROUP BY severidade
        )
        SELECT n.nome, COALESCE(c.total, 0) FROM niveis n
        LEFT JOIN contagens c ON c.severidade = n.nome ORDER BY n.ordem
    """,
}


def consultar_relatorio(caminho, tipo, de=None, ate=None):
    with abrir_banco(caminho) as conexao:
        return conexao.execute(CONSULTAS[tipo], {"de": de, "ate": ate}).fetchall()
