# Grupo 4 — Analisador de Segurança de Sistemas

Projeto de Paradigmas de Programação para analisar logs fictícios de acesso. Cada alerta descreve um comportamento suspeito e mostra os registros que justificaram a detecção. A confirmação de um incidente exige análise humana.

## Executar pelo terminal

Instale o Python 3.7 ou superior com SQLite, incluído na distribuição oficial para Windows. O projeto usa apenas a biblioteca padrão. A partir da pasta que contém `analisador_seguranca`, execute:

```powershell
cd analisador_seguranca
python main.py
python main.py analisar dados/logs_exemplo.csv
```

O primeiro comando Python mostra a ajuda. O comando `analisar` lê o CSV, exibe as evidências e cria `seguranca.db` ao lado de `main.py`. O exemplo produz **9 registros válidos, 1 inválido e 3 alertas**, um de cada regra.

Para alterar os quatro parâmetros e gravar o resultado em outro banco:

```powershell
python main.py analisar dados/logs_exemplo.csv --janela-minutos 15 --limite-falhas 4 --inicio-expediente 07:30 --fim-expediente 19:00 --banco outro.db
```

Cada análise acrescenta os eventos e alertas ao banco escolhido. Reprocessar o mesmo CSV no mesmo banco soma os registros novamente. As regras avaliam apenas o arquivo da execução atual.

## Entrada e regras

O CSV usa UTF-8, vírgula, um registro por linha e as colunas `instante,usuario,ip,evento,resultado`. Use data e hora local no formato `AAAA-MM-DDTHH:MM:SS`. O leitor remove espaços nas bordas e converte evento e resultado para minúsculas. Linhas inválidas entram na contagem de descartes. O analisador ordena os eventos válidos pelo instante.

| Regra | Condição com os parâmetros padrão | Severidade adotada |
|---|---|---|
| Múltiplas falhas | Falhas de `login` do mesmo usuário atingem 3 em uma janela de 10 minutos, incluindo o limite de 10 minutos. Falhas adicionais só geram outro alerta se a contagem voltar a atingir o limite após a expiração de falhas antigas. | MÉDIA |
| Sucesso após falhas | Um `login` com sucesso tem pelo menos uma falha de login do mesmo usuário nos 10 minutos anteriores. Falhas no mesmo segundo do sucesso são excluídas. As evidências incluem as falhas e o sucesso. | ALTA |
| Atividade fora do horário | Qualquer evento antes das 08:00 ou a partir das 18:00. O expediente configurado começa e termina no mesmo dia. | BAIXA |

## Consultar relatórios

```powershell
python main.py relatorio usuario
python main.py relatorio regra
python main.py relatorio severidade
python main.py relatorio usuario --de 2026-10-20T09:06:00 --ate 2026-10-20T09:06:00
```

Os três relatórios aceitam `--banco`, `--de` e `--ate`. Cada limite do período é opcional e inclusivo. Eventos contam pelo próprio horário, e alertas contam pelo horário do evento que os disparou. No último exemplo, após uma análise do CSV padrão, aparece `usuario01 | 1 | 1`. As três falhas anteriores continuam vinculadas ao alerta como evidências.

## Arquitetura em camadas

```text
analisador_seguranca/
├── main.py                  Apresentação dos comandos, erros e resultados
├── app/
│   ├── __init__.py          Pacote da aplicação
│   ├── analisador.py        Aplicação: coordena leitura, ordenação, regras e gravação
│   ├── modelos.py           Domínio: Evento, Regra e Alerta
│   ├── regras.py            Domínio: três regras independentes
│   ├── leitor_logs.py       Infraestrutura: leitura e normalização do CSV
│   ├── banco.py             Infraestrutura: tabelas e gravação em transação
│   └── relatorios.py        Infraestrutura: consultas agregadas por período
├── dados/logs_exemplo.csv   Registros fictícios para demonstração
├── tests/test_analisador.py Testes com unittest
├── README.md
└── seguranca.db             Gerado no primeiro acesso ao banco
```

O domínio recebe objetos em memória e devolve alertas. Na gravação, a tabela `alerta_eventos` liga cada alerta às linhas de `eventos` que o justificam. Assim, duas linhas idênticas do CSV continuam identificáveis como ocorrências distintas.

## Cinco paradigmas no código

| Paradigma | Arquivo, classe ou função | Aplicação e justificativa |
|---|---|---|
| Imperativo/estruturado | `app/leitor_logs.py`, `ler_csv` | O laço lê cada linha, valida os campos e conta os descartes antes de continuar. |
| Orientado a objetos | `app/modelos.py`, `Evento`, `Regra`, `Alerta`; `app/analisador.py`, `Analisador` | Cada classe tem uma responsabilidade. O analisador chama o mesmo método `avaliar` nas três regras. |
| Funcional | `normalizar_registro` e `ForaDoHorario.avaliar` | Uma função transforma dados em um novo evento. A outra filtra eventos e devolve alertas. Ambas operam sem entrada e saída. |
| Declarativo | `app/relatorios.py`, `CONSULTAS` | O SQL usa `WHERE`, `GROUP BY` e `COUNT` para declarar quais totais o SQLite deve calcular. |
| Lógico | `app/regras.py`, `MultiplasFalhas`, `SucessoAposFalhas` e `ForaDoHorario` | Cada regra expressa uma inferência: se os eventos satisfazem a condição, então se produz um alerta associado às evidências. |

## Executar os testes

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem as três regras, a configuração, o descarte de linhas inválidas, a persistência das evidências e as contagens por período. Os bancos usados nos testes ficam em diretórios temporários.
