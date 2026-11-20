"""Inferências sobre eventos ordenados, sem acesso a arquivos ou ao banco."""

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import time

from .modelos import Regra


def janelas_de_login(eventos, minutos):
    """A cada login, apresenta as falhas do usuário na janela, incluindo a atual."""
    por_usuario = defaultdict(deque)
    for evento in eventos:
        if evento.evento != "login":
            continue
        falhas = por_usuario[evento.usuario]
        while falhas and (evento.instante - falhas[0].instante).total_seconds() > minutos * 60:
            falhas.popleft()
        if evento.resultado == "falha":
            falhas.append(evento)
        yield evento, falhas


@dataclass
class MultiplasFalhas(Regra):
    janela_minutos: int
    limite_falhas: int
    nome = "Múltiplas falhas"
    descricao = "Falhas de login de um usuário dentro da janela."
    severidade = "MÉDIA"

    def avaliar(self, eventos):
        alertas = []
        for evento, falhas in janelas_de_login(eventos, self.janela_minutos):
            if evento.resultado == "falha" and len(falhas) == self.limite_falhas:
                motivo = f"{len(falhas)} falhas de login em uma janela de {self.janela_minutos} min."
                alertas.append(self.criar_alerta(falhas, motivo))
        return alertas


@dataclass
class SucessoAposFalhas(Regra):
    janela_minutos: int
    nome = "Sucesso após falhas"
    descricao = "Login bem-sucedido após pelo menos uma falha recente."
    severidade = "ALTA"

    def avaliar(self, eventos):
        alertas = []
        for evento, falhas in janelas_de_login(eventos, self.janela_minutos):
            if evento.resultado == "sucesso":
                anteriores = [falha for falha in falhas if falha.instante < evento.instante]
                if anteriores:
                    motivo = (f"Login bem-sucedido em {evento.instante.isoformat()} após "
                              f"{len(anteriores)} falha(s) nos últimos {self.janela_minutos} min.")
                    alertas.append(self.criar_alerta([*anteriores, evento], motivo))
        return alertas


@dataclass
class ForaDoHorario(Regra):
    inicio: time
    fim: time
    nome = "Atividade fora do horário"
    descricao = "Evento anterior ao início ou a partir do fim do expediente."
    severidade = "BAIXA"

    def avaliar(self, eventos):
        motivo = f"Atividade fora do expediente das {self.inicio:%H:%M} às {self.fim:%H:%M}."
        return [self.criar_alerta([evento], motivo) for evento in eventos
                if not self.inicio <= evento.instante.time() < self.fim]
