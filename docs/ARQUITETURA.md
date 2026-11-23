# Arquitetura

## Arquivos

| Arquivo | Papel |
|---|---|
| `bot.py` | `BotBase`. `setup_hook` carrega cogs na ordem: jornal, exploracao, regioes_admin, procurado, encontro, navegacao. Depois `tree.sync()`. Prefixo `jornal!` (não há comandos de texto). |
| `cogs/jornal.py` | `/testar_noticia`, `/rerrolar_jornal`, `/rerrolar_variavel`, `/cadastrar`, `/remover`, `/editar`, `/lista_procurados`. Loop semanal `postar_noticias_semanais`. |
| `cogs/regioes_admin.py` | `/regioes`: painel com botões/selects/modais (locais, templates, clima, grupos, variações). |
| `cogs/procurado.py` | `/procurado`, `/procurados_ativos`, `/procurado_liberar`. |
| `cogs/encontro.py` | `/encontromaritimo`, `/desafiodasilhas` (Totto Land). |
| `cogs/exploracao.py` | `/exploracao`, `/ler_poneglyph`. Dados em `exploracao_data.json`. |
| `cogs/permissoes.py` | `is_allowed_role()` e IDs de cargos. |
| `regioes_db.py` | Schema e CRUD SQLite de regiões, locais, grupos, variações, categorias e opções de clima. Seed inicial (`_seed_defaults_if_empty`). `sortear_com_peso`, `calcular_porcentagens`. |
| `regioes_engine.py` | Gera o estado do boletim (`gerar_estado_regiao`), renderiza texto, rerrola uma variável, reconstrói estado de mensagem postada. |
| `cacadas_db.py` | Travas de caça (14 dias), `jornal_atual`, `edicao_atual` (estado JSON por região). |
| `database.py` | Lê/escreve a planilha Google via gspread (`credenciais.json`). `obter_planilha()` é compartilhada com a navegação. |
| `cogs/navegacao.py` | Comandos da navegação do Novo Mundo. Regras em `navegacao_engine.py`, PostgreSQL/Sheets em `navegacao_db.py`, ilhas de seed em `navegacao_dados.py`. Ver `REGRAS_NAVEGACAO.md`. |
| `image-1.png` | Imagem anexada a cada boletim enviado. |

## Bancos

- Navegação do Novo Mundo: PostgreSQL da Discloud (`DATABASE_URL`), com Google Sheets como reserva. Tabelas `nm_ilhas`, `nm_bandos`, `nm_log` (ver `REGRAS_NAVEGACAO.md`).
- `regioes.db` — configuração do jornal (criado automaticamente, semeado com East/South/North/West Blue e Paradise).
- `cacadas.db` — caçadas ativas, nomes da edição atual, estado para rerrolar.
- Ambos são SQLite, ignorados pelo git (`*.db`).

## Fluxo do jornal

1. `gerar_todos_boletins` embaralha o pool de procurados (planilha).
2. Para cada região ativa, `gerar_estado_regiao` sorteia: grupos de template (com local), procurado (consome o pool), categorias de clima.
3. `renderizar_estado` monta o texto. Cada boletim é enviado com `image-1.png`.
4. Se for oficial (não teste): `definir_jornal_atual` bloqueia os nomes no `/procurado`, e `salvar_edicao_atual` guarda o estado + ids das mensagens para `/rerrolar_variavel`.

## Agenda

Loop `postar_noticias_semanais`: domingo (`DIA_DA_SEMANA_UTC = 6`) às 15:00 UTC, no canal `ID_CANAL_JORNAL`.
