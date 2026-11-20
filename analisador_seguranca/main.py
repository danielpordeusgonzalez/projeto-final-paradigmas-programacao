"""Entrada do analisador de segurança pelo terminal."""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from app.analisador import Analisador
from app.leitor_logs import converter_instante
from app.regras import ForaDoHorario, MultiplasFalhas, SucessoAposFalhas
from app.relatorios import consultar_relatorio


BANCO_PADRAO = Path(__file__).resolve().parent / "seguranca.db"


class ArgumentosTerminal(argparse.ArgumentParser):
    """Fornece ajuda em português também nas instalações de Python em inglês."""

    def __init__(self, *args, **opcoes):
        super().__init__(*args, add_help=False, **opcoes)
        self.add_argument("-h", "--help", action="help", help="mostra esta ajuda")

    def format_help(self):
        return (super().format_help().replace("usage:", "Uso:")
                .replace("positional arguments:", "Argumentos:")
                .replace("optional arguments:", "Opções:").replace("options:", "Opções:"))

    def error(self, message):
        self.exit(2, f"Argumentos inválidos ou incompletos.\n{self.format_help()}")


def criar_argumentos():
    programa = ArgumentosTerminal(description="Analisador de registros de segurança simulados.")
    comandos = programa.add_subparsers(dest="comando", title="Comandos")
    analise = comandos.add_parser("analisar", help="analisa e armazena um CSV")
    analise.add_argument("arquivo", type=Path, help="caminho do arquivo CSV")
    analise.add_argument("--janela-minutos", default="10", help="janela de detecção (padrão 10)")
    analise.add_argument("--limite-falhas", default="3", help="mínimo de falhas (padrão 3)")
    analise.add_argument("--inicio-expediente", default="08:00", help="início incluído (padrão 08:00)")
    analise.add_argument("--fim-expediente", default="18:00", help="fim excluído (padrão 18:00)")
    relatorio = comandos.add_parser("relatorio", help="consulta os dados armazenados")
    relatorio.add_argument("tipo", choices=("usuario", "regra", "severidade"))
    relatorio.add_argument("--de", metavar="INSTANTE", help="início inclusivo do período")
    relatorio.add_argument("--ate", metavar="INSTANTE", help="fim inclusivo do período")
    for comando in (analise, relatorio):
        comando.add_argument("--banco", type=Path, default=BANCO_PADRAO,
                             help="arquivo SQLite (padrão seguranca.db na raiz do projeto)")
    return programa


def inteiro_positivo(texto, opcao):
    try:
        numero = int(texto)
        if numero > 0:
            return numero
    except ValueError:
        pass
    raise ValueError(f"{opcao} exige um número inteiro maior que zero.")


def horario(texto):
    try:
        valor = datetime.strptime(texto, "%H:%M").time()
        if valor.strftime("%H:%M") == texto:
            return valor
    except ValueError:
        pass
    raise ValueError("Informe os horários do expediente no formato HH:MM, de 00:00 a 23:59.")


def executar_analise(args):
    janela = inteiro_positivo(args.janela_minutos, "--janela-minutos")
    limite = inteiro_positivo(args.limite_falhas, "--limite-falhas")
    inicio, fim = horario(args.inicio_expediente), horario(args.fim_expediente)
    if inicio >= fim:
        raise ValueError("O fim do expediente deve ser posterior ao início no mesmo dia.")
    regras = [MultiplasFalhas(janela, limite), SucessoAposFalhas(janela), ForaDoHorario(inicio, fim)]
    validos, invalidos, alertas = Analisador(regras).analisar_arquivo(args.arquivo, args.banco)
    print(f"Registros válidos: {validos}\nRegistros inválidos: {invalidos}\nAlertas gerados: {len(alertas)}")
    for alerta in alertas:
        print(f"\n[{alerta.severidade}] {alerta.regra} | {alerta.usuario}\n{alerta.descricao}")
        print("Evidências (instante | usuário | IP | evento | resultado):")
        for evidencia in alerta.evidencias:
            print(f"  {evidencia}")


def exibir_relatorio(args):
    de = converter_instante(args.de).isoformat() if args.de is not None else None
    ate = converter_instante(args.ate).isoformat() if args.ate is not None else None
    if de and ate and de > ate:
        raise ValueError("O fim do período precisa ser igual ou posterior ao início.")
    titulos = {"usuario": "Usuário | Eventos | Alertas", "regra": "Regra | Alertas",
               "severidade": "Severidade | Alertas"}
    linhas = consultar_relatorio(args.banco, args.tipo, de, ate)
    print(titulos[args.tipo])
    for linha in linhas:
        print(" | ".join(map(str, linha)))
    if not linhas:
        print("Nenhum registro no período.")


def main():
    programa = criar_argumentos()
    args = programa.parse_args()
    try:
        if args.comando == "analisar":
            executar_analise(args)
        elif args.comando == "relatorio":
            exibir_relatorio(args)
        else:
            programa.print_help()
    except FileNotFoundError as erro:
        print(f"Arquivo não encontrado: {erro.filename}", file=sys.stderr)
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
    except OSError as erro:
        print(f"Não foi possível ler o arquivo: {erro.filename}", file=sys.stderr)
    except sqlite3.Error:
        print(f"Não foi possível acessar ou atualizar o banco SQLite: {args.banco}", file=sys.stderr)
    else:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
