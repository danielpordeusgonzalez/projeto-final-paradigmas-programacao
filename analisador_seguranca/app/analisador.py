"""Coordenação da leitura, da detecção e da persistência."""

from .banco import salvar_analise
from .leitor_logs import ler_csv


class Analisador:
    def __init__(self, regras):
        self.regras = tuple(regras)

    def analisar(self, eventos):
        ordenados = sorted(eventos, key=lambda evento: evento.instante)
        alertas = [alerta for regra in self.regras for alerta in regra.avaliar(ordenados)]
        return ordenados, sorted(alertas, key=lambda alerta: alerta.instante)

    def analisar_arquivo(self, arquivo, caminho_banco):
        eventos, invalidos = ler_csv(arquivo)
        ordenados, alertas = self.analisar(eventos)
        salvar_analise(caminho_banco, ordenados, alertas)
        return len(ordenados), invalidos, alertas
