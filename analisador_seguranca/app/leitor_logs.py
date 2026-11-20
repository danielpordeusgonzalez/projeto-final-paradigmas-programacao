"""Leitura de CSV com um registro por linha e normalização dos campos."""

import csv
from datetime import datetime

from .modelos import Evento


CAMPOS = ("instante", "usuario", "ip", "evento", "resultado")


def converter_instante(texto):
    try:
        instante = datetime.strptime(texto, "%Y-%m-%dT%H:%M:%S")
        if instante.isoformat() == texto:
            return instante
    except ValueError:
        pass
    raise ValueError("Use data e hora válidas no formato AAAA-MM-DDTHH:MM:SS.")


def normalizar_registro(registro):
    instante, usuario, ip, evento, resultado = (registro[c].strip() for c in CAMPOS)
    if not all((instante, usuario, ip, evento, resultado)):
        raise ValueError("Campo obrigatório vazio.")
    return Evento(converter_instante(instante), usuario, ip, evento.lower(), resultado.lower())


def ler_campos(linha):
    # O leitor preserva bytes inválidos até aqui para que o descarte afete só esta linha.
    try:
        linha.encode("utf-8")
    except UnicodeEncodeError as erro:
        raise ValueError("O CSV precisa estar codificado em UTF-8.") from erro
    return next(csv.reader([linha], strict=True))


def ler_csv(caminho):
    eventos = []
    invalidos = 0
    with open(caminho, encoding="utf-8-sig", errors="surrogateescape", newline="") as arquivo:
        try:
            cabecalho = [c.strip() for c in ler_campos(arquivo.readline())]
        except csv.Error as erro:
            raise ValueError("Cabeçalho CSV malformado.") from erro
        if not set(CAMPOS).issubset(cabecalho) or len(set(cabecalho)) != len(cabecalho):
            raise ValueError("O CSV precisa de um cabeçalho sem nomes repetidos e com os "
                             "campos instante, usuario, ip, evento e resultado.")

        for linha in arquivo:
            try:
                valores = ler_campos(linha)
                if len(valores) != len(cabecalho):
                    raise ValueError("Número incorreto de campos.")
                eventos.append(normalizar_registro(dict(zip(cabecalho, valores))))
            except (csv.Error, ValueError):
                invalidos += 1
    return eventos, invalidos
