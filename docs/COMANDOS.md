# Comandos (slash)

Todos exigem cargo permitido, exceto onde indicado.

## Jornal (`cogs/jornal.py`)

| Comando | O que faz |
|---|---|
| `/testar_noticia` | Gera edições de teste no canal atual. Não trava procurados. |
| `/rerrolar_jornal` | Gera e posta nova edição **oficial** no canal do jornal. |
| `/rerrolar_variavel mar variavel [mensagem_id]` | Rerrola uma variável de uma região. Sem `mensagem_id` usa a edição oficial salva. |
| `/cadastrar nome tipo` | Adiciona procurado na planilha (Pirata/Marinheiro). |
| `/remover nome` | Remove da planilha. |
| `/editar nome_antigo [nome_novo] [novo_tipo]` | Altera nome e/ou tipo. |
| `/lista_procurados` | Lista da planilha (efêmero). |

## Regiões (`cogs/regioes_admin.py`)

| Comando | O que faz |
|---|---|
| `/regioes` | Abre o painel (efêmero): criar/editar regiões, locais, templates, clima, variações. Botões validam cargo. |

## Procurados e caça (`cogs/procurado.py`)

| Comando | O que faz |
|---|---|
| `/procurado procurado mar` | Inicia caça: sorteia o local e trava por 14 dias. |
| `/procurados_ativos` | Lista caçadas em andamento (efêmero). |
| `/procurado_liberar nome` | Libera a trava antes do prazo. |

## Encontros (`cogs/encontro.py`)

| Comando | O que faz |
|---|---|
| `/encontromaritimo regiao [debug]` | Sorteia encontro em Paradise, Novo Mundo, Calm Belt ou Desastre (Totto Land). |
| `/desafiodasilhas [nc] [debug]` | Totto Land: sorteia encontro de exploração, com NC opcional. |

## Exploração (`cogs/exploracao.py`)

| Comando | O que faz |
|---|---|
| `/exploracao tier [debug]` | Mesa de exploração (`paradise` ou `blues`). |
| `/ler_poneglyph` | Leitura teatral de um Poneglyph encontrado. Sem restrição de cargo. |

## Navegação do Novo Mundo (`cogs/navegacao.py`)

| Comando | O que faz |
|---|---|
| `/navegacao_iniciar bando ilha` | Cria o bando (Raijin, Risky Red ou Mystoria). |
| `/navegar bando [forcar]` | Sincroniza o Log Pose 3A (3 ilhas + tipo de agulha). |
| `/viajar bando agulha resultado` | Aplica sucesso/falha do Teste de Navegação. |
| `/totto_sair bando` | Sai de Totto Land (5 progressões lá dentro). |
| `/navegacao_status bando` | Situação do bando (efêmero). |
| `/navegacao_ajustar bando ...` | Mestre: corrige área, progressão, local (efêmero). |

Regras: `REGRAS_NAVEGACAO.md`.

## Sem comando, mas relevante

- Loop semanal (domingo 15:00 UTC): posta a edição oficial automaticamente.
