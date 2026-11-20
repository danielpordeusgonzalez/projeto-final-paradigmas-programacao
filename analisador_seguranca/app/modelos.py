"""Objetos do domínio e contrato das regras de detecção."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence, Tuple


# Cada ocorrência do CSV tem identidade própria, mesmo com campos idênticos.
@dataclass(frozen=True, eq=False)
class Evento:
    instante: datetime
    usuario: str
    ip: str
    evento: str
    resultado: str


@dataclass(frozen=True)
class Alerta:
    regra: str
    usuario: str
    severidade: str
    descricao: str
    eventos_associados: Tuple[Evento, ...]

    @property
    def instante(self):
        return self.eventos_associados[-1].instante

    @property
    def evidencias(self):
        return tuple(
            f"{e.instante.isoformat()} | {e.usuario} | {e.ip} | {e.evento} | {e.resultado}"
            for e in self.eventos_associados
        )


class Regra(ABC):
    nome: str
    descricao: str
    severidade: str

    @abstractmethod
    def avaliar(self, eventos: Sequence[Evento]) -> List[Alerta]:
        """Recebe eventos em ordem cronológica e devolve os alertas inferidos."""

    def criar_alerta(self, associados, justificativa):
        return Alerta(self.nome, associados[-1].usuario, self.severidade,
                      justificativa, tuple(associados))
