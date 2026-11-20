import unittest
from datetime import datetime, time
from pathlib import Path
from tempfile import TemporaryDirectory

from app.analisador import Analisador
from app.banco import abrir_banco, salvar_analise
from app.leitor_logs import ler_csv
from app.modelos import Evento
from app.regras import ForaDoHorario, MultiplasFalhas, SucessoAposFalhas
from app.relatorios import consultar_relatorio


def registro(hora, resultado="falha", usuario="usuario01", evento="login"):
    instante = datetime.fromisoformat("2026-10-20T" + hora)
    return Evento(instante, usuario, "192.0.2.10", evento, resultado)


class TestesDeteccao(unittest.TestCase):
    def test_falhas_na_janela_inclusiva_sem_repetir_alerta(self):
        eventos = [registro(h) for h in ("09:00", "09:05", "09:10", "09:10")]
        _, alertas = Analisador([MultiplasFalhas(10, 3)]).analisar(reversed(eventos))
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].severidade, "MÉDIA")
        self.assertEqual([e.instante for e in alertas[0].eventos_associados],
                         [e.instante for e in eventos[:3]])

    def test_falhas_distantes_e_falhas_de_usuarios_distintos(self):
        eventos = [registro(h) for h in ("09:00", "09:20", "09:40")]
        eventos += [registro("09:40", usuario="usuario02"), registro("09:40", evento="consulta")]
        self.assertEqual(MultiplasFalhas(10, 3).avaliar(eventos), [])

    def test_sucesso_considera_apenas_falhas_anteriores_do_usuario(self):
        falha, sucesso = registro("09:03"), registro("09:06", "sucesso")
        eventos = [registro("09:07"), registro("09:06"), registro("08:00"),
                   registro("09:05", usuario="usuario02"), sucesso, falha]
        _, alertas = Analisador([SucessoAposFalhas(10)]).analisar(eventos)
        self.assertEqual(len(alertas), 1)
        alerta = alertas[0]
        self.assertEqual((alerta.severidade, alerta.eventos_associados), ("ALTA", (falha, sucesso)))
        self.assertIn("1 falha", alerta.descricao)
        self.assertIn(sucesso.instante.isoformat(), alerta.descricao)
        self.assertIn(falha.instante.isoformat(), alerta.evidencias[0])

    def test_faixa_inclui_inicio_e_exclui_fim(self):
        eventos = [registro(h, evento="consulta") for h in ("07:59:59", "08:00", "17:59:59", "18:00")]
        alertas = ForaDoHorario(time(8), time(18)).avaliar(eventos)
        self.assertEqual([a.eventos_associados for a in alertas], [(eventos[0],), (eventos[3],)])
        self.assertTrue(all(a.severidade == "BAIXA" for a in alertas))

    def test_parametros_alteram_as_deteccoes(self):
        eventos = [registro("09:00"), registro("09:11"), registro("09:22", "sucesso")]
        regras = [MultiplasFalhas(11, 2), SucessoAposFalhas(11), ForaDoHorario(time(9, 5), time(18))]
        _, alertas = Analisador(regras).analisar(eventos)
        self.assertEqual([a.severidade for a in alertas], ["BAIXA", "MÉDIA", "ALTA"])


class TestesInfraestrutura(unittest.TestCase):
    def test_linhas_malformadas_nao_interrompem_leitura(self):
        with TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "logs.csv"
            arquivo.write_bytes(
                b"\xef\xbb\xbfinstante,usuario,ip,evento,resultado\n"
                b'"aspas sem fechamento\n'
                b"2026-10-20T09:00:00, usuario01 ,192.0.2.10, LOGIN , Falha \n"
                b"2026-02-30T09:00:00,usuario01,192.0.2.10,login,falha\n"
                b"2026-10-20T09:01:00,usuario01,192.0.2.10,login\n"
                b"2026-10-20T09:02:00,,192.0.2.10,login,falha\n"
                b"2026-10-20T09:02:30,usuario\xff,192.0.2.10,login,falha\n"
                b"2026-10-20T09:03:00,usuario01,192.0.2.10,login,sucesso\n"
            )
            eventos, invalidos = ler_csv(arquivo)
            self.assertEqual((len(eventos), invalidos), (2, 5))
            self.assertEqual((eventos[0].usuario, eventos[0].evento, eventos[0].resultado),
                             ("usuario01", "login", "falha"))
            self.assertEqual(len(SucessoAposFalhas(10).avaliar(eventos)), 1)

    def test_evidencias_distintas_e_relatorios_por_periodo(self):
        eventos = [registro("09:00"), registro("09:00"), registro("09:01", "sucesso"),
                   registro("09:01", "sucesso", usuario="usuario02")]
        regras = [MultiplasFalhas(10, 2), SucessoAposFalhas(10)]
        ordenados, alertas = Analisador(regras).analisar(eventos)
        with TemporaryDirectory() as pasta:
            banco = Path(pasta) / "seguranca.db"
            salvar_analise(banco, ordenados, alertas)
            with abrir_banco(banco) as conexao:
                evidencias = conexao.execute("""
                    SELECT e.id, e.resultado FROM alerta_eventos ae
                    JOIN eventos e ON e.id = ae.evento_id
                    JOIN alertas a ON a.id = ae.alerta_id
                    WHERE a.severidade = 'ALTA' ORDER BY e.id
                """).fetchall()
            self.assertEqual(evidencias, [(1, "falha"), (2, "falha"), (3, "sucesso")])
            ponto = eventos[2].instante.isoformat()
            self.assertEqual(consultar_relatorio(banco, "usuario", ponto, ponto),
                             [("usuario01", 1, 1), ("usuario02", 1, 0)])
            self.assertEqual(consultar_relatorio(banco, "regra", ponto, ponto),
                             [("Sucesso após falhas", 1)])
            self.assertEqual(consultar_relatorio(banco, "severidade", ponto, ponto),
                             [("BAIXA", 0), ("MÉDIA", 0), ("ALTA", 1)])


if __name__ == "__main__":
    unittest.main()
