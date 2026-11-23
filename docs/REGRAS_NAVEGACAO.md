# Navegação do Novo Mundo (Log Pose 3A)

Código: `cogs/navegacao.py` (comandos, painel e botões), `navegacao_visual.py` (GIF do Log Pose, Pillow), `navegacao_engine.py` (regras, constantes de balanceamento no topo), `navegacao_db.py` (Google Sheets), `navegacao_dados.py` (ilhas de seed).

## Armazenamento (persistente)

`navegacao_db.py` escolhe o backend pela variável de ambiente **`DATABASE_URL`**:

- **Com `DATABASE_URL`: PostgreSQL da Discloud** (produção). Tabelas `nm_ilhas`, `nm_bandos` (estado em JSONB) e `nm_log`, criadas sozinhas na primeira conexão; `nm_ilhas` é semeada de `navegacao_dados.py`. O banco só é acessível pela rede privada (VLAN), então não dá pra conectar do PC.
- **Sem `DATABASE_URL`: Google Sheets** (reserva/testes locais). Abas `NM_Ilhas`, `NM_Bandos`, `NM_Log` na planilha "Procurados Blues".

Os dois backends têm a mesma interface; os dados **não migram sozinhos** de um para o outro.

Ilhas: gerencie pelo painel `/navegacao` > 🏝️ Ilhas (➕ Adicionar / ➖ Remover). O rodapé do painel mostra o backend em uso. Tipos: `inicial`, `sincronizavel`, `secreta`, `principal`, `totto` (o arquipélago), `totto_ilha` (ilhas dentro de Totto), `calm` (nota = nível 1 ou 2). Área: 1, 2, 3, 4 ou `calm`.

**Ilhas de Totto Land ainda não estão cadastradas:** use o painel (Ilhas > Adicionar) com área `2` e tipo `totto_ilha`.

### Ligar o PostgreSQL na Discloud

1. Dashboard > Databases > Create database > PostgreSQL (mín. 512 MB de RAM, conta na RAM do plano).
2. Ativar **VLAN** na aplicação do bot (plano Diamond) e deixar bot e banco no mesmo cluster/Project.
3. Colocar `DATABASE_URL=postgresql://USUARIO:SENHA@HOST:PORTA/BANCO` no `.env` do bot na Discloud (URL do card "Private connection"). Nunca no Git.
4. Rebuild/deploy. Conferir abrindo `/navegacao` (o rodapé mostra o banco e a abertura já exige conexão).

## Regras implementadas

1. Bando parte de Raijin, Risky Red ou Mystoria (`/navegacao_iniciar`).
2. `/navegar` sincroniza 3 ilhas distintas, cada agulha com tipo sorteado:
   - 🟢 Estável: CD normal, +1 progressão.
   - 🟡 Moderada: CD +2, +1,5 progressão.
   - 🔴 Instável: CD +5, **falha leva ao Calm Belt**, +3 progressões.
3. Botões ✅/❌ da mensagem do `/navegar` (um por agulha): o mestre informa o resultado do Teste de Navegação.
   - Sucesso: chega à ilha, ganha a progressão da agulha (área atual).
   - Falha: ilha secreta aleatória da **área atual** (sem progressão); se a agulha era Instável, ilha aleatória do **Calm Belt**. Em Totto Land não há ilha secreta: rola-se Desastre (`/encontromaritimo`).
4. Pool de sincronização: ilhas não visitadas da área atual (peso 1) e de áreas anteriores (peso `PESO_AREA_ANTERIOR` = 0,1). Ilhas de áreas ainda não exploradas nunca aparecem. Ilha visitada nunca volta.
5. Ilha principal (Dressrosa 1→2, Wano 2→3, Elbaph 3→Laugh Tale) entra no pool com 20 progressões na área (peso `PESO_PRINCIPAL` = 5). Ao chegar nela a progressão zera e a próxima área é liberada. Na área 4, Laugh Tale sempre aparece numa agulha.
6. **Totto Land** (Área 2):
   - Se uma agulha a sorteia (e o bando nunca saiu de lá), as 3 apontam pra ela. O bando vai (botões da mensagem) ou espera 7 dias pra `/navegar` de novo (`forcar` ignora a espera).
   - Dentro: só ilhas `totto_ilha`, todas Estáveis, CD normal, +1 progressão cada, também contando pra área.
   - Sair: Sair (painel `/navegacao` > 🍬) exige 5 progressões lá dentro. Depois, Totto vira ilha comum (uma agulha só) e dá pra voltar com as mesmas regras.
7. Painel `/navegacao`: ver progresso e **ilhas visitadas** (por área, Totto, secretas e Calm Belt, na ordem da viagem), ✏️ Ajustar (área, progressão, local, flag de Totto; dessincroniza o Log Pose), 🍬 Sair de Totto, 🧭 Navegar, criar bando.

## Botões persistentes

Os botões da mensagem de sincronização usam `discord.ui.DynamicItem` com `timeout=None`; o `custom_id` é `nm:<agulha>:<s|f>:<hash do bando>:<sync_id>`. O estado vive no banco, então funcionam depois de reiniciar o bot. `sync_id` sobe a cada sincronização/ajuste: botão de uma sincronização antiga (ou já resolvida) avisa e some da mensagem. Só cargos permitidos podem apertar. Depois de apertado, a mensagem perde os botões e mostra quem resolveu.

## GIF

`navegacao_visual.gerar_gif_logpose`: usa a imagem `assets/logpose_base.png` (Log Pose do anime, **já sem as agulhas**) como fundo e desenha por cima só as 3 agulhas, o aro colorido de cada bolha (verde/âmbar/vermelho pelo tipo) e o número. As agulhas giram, balançam e assentam; em Totto Land as 3 apontam pro mesmo lado e o aro fica rosa. ~2,5 s pra gerar (roda em thread), ~1 MB. Se a imagem faltar ou der erro, a sincronização sai sem GIF.

A posição das bolhas (`BOLHAS` no topo do arquivo) é na imagem original de 700x667. Se trocar a imagem de base, ajuste esses valores e apague as agulhas dela antes.
