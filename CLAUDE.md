# CLAUDE.md — Bot do Jornal (Rainbow News / One Piece RPG)

Bot de Discord em discord.py (slash commands). Idioma do código, comandos e
mensagens: **português**. Mantenha esse padrão.

Detalhes ficam em `docs/` — leia só o que for relevante à tarefa:
- `docs/ARQUITETURA.md` — mapa de arquivos, banco de dados, fluxo do jornal.
- `docs/REGRAS_JORNAL.md` — como o boletim é sorteado, /rerrolar_variavel, travas.
- `docs/REGRAS_SISTEMAS.md` — /procurado, /encontromaritimo, /desafiodasilhas, /exploracao, /ler_poneglyph.
- `docs/REGRAS_NAVEGACAO.md` — navegação do Novo Mundo (Log Pose 3A, Totto Land, Sheets como banco).
- `docs/COMANDOS.md` — lista de todos os slash commands e permissões.

## Regras de trabalho

- Não rode o bot nem toque em `.env`, `credenciais.json`, `*.db` ou `exploracao_data.json` sem pedido explícito.
- Não commite segredos. `.env` e `credenciais.json` estão no `.gitignore`; confirme antes de `git add`.
- Ignore `_backup_local/`: é um bot antigo e diferente ("Buggy"), não é o código ativo.
- Para adicionar região, mar, locais, rumores ou clima: **não** editar código — isso é feito no `/regioes` do Discord. Mexer no código só se a mudança for de comportamento.
- Ao mudar regras de sorteio, atualize o `docs/` correspondente junto.
- Commits em PT-BR, curtos, no estilo do histórico (`Adiciona ...`, `Remove ...`).

## Estrutura resumida

- `bot.py` — entrada; carrega os cogs e sincroniza os comandos.
- `cogs/` — um arquivo por sistema (jornal, regioes_admin, procurado, encontro, exploracao, permissoes).
- `regioes_db.py` / `regioes_engine.py` — dados e sorteio do jornal (SQLite `regioes.db`).
- `cacadas_db.py` — travas de caça e estado da edição oficial (SQLite `cacadas.db`).
- `navegacao_engine.py` / `navegacao_db.py` / `navegacao_dados.py` — navegação do Novo Mundo (regras puras, Sheets, ilhas de seed).
- `database.py` — integração com a planilha Google "Procurados Blues" (aba "Procurados").

## Permissões

Todo comando admin usa `@is_allowed_role()` (`cogs/permissoes.py`), com 4 cargos por ID.
Não duplicar a lista de IDs em outro lugar.

## Gotchas

- Mensagem do jornal é reconstruída por regex contra os templates atuais (`reconstruir_estado`); mudar um template quebra o `/rerrolar_variavel` em mensagens antigas.
- Edição de teste (`[TESTE]`) não grava estado oficial.
- Ao postar uma edição oficial, `jornal_atual` é substituído inteiro — nomes da edição ficam fora do `/procurado`.
