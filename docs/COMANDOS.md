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
| `/navegar bando [forcar]` | Sincroniza o Log Pose 3A. A mensagem sai com GIF animado e botões ✅/❌ por agulha. |
| `/navegacao` | Painel (efêmero) dos staffs: bandos, ilhas visitadas, ajustes, Totto Land, cadastro de ilhas. |

Os botões de sucesso/falha são persistentes (sem timeout, sobrevivem a reinício do bot). Tudo que antes eram comandos separados (`/viajar`, `/totto_sair`, `/navegacao_iniciar`, `/navegacao_status`, `/navegacao_ajustar`, `/navegacao_ilha_*`, `/navegacao_banco`) agora está no painel.

Regras: `REGRAS_NAVEGACAO.md`.

## Sem comando, mas relevante

- Loop semanal (domingo 15:00 UTC): posta a edição oficial automaticamente.
