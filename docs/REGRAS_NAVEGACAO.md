# Navegação do Novo Mundo (Log Pose 3A)

Código: `cogs/navegacao.py` (comandos), `navegacao_engine.py` (regras, constantes de balanceamento no topo), `navegacao_db.py` (Google Sheets), `navegacao_dados.py` (ilhas de seed).

## Armazenamento (persistente)

`navegacao_db.py` escolhe o backend pela variável de ambiente **`DATABASE_URL`**:

- **Com `DATABASE_URL`: PostgreSQL da Discloud** (produção). Tabelas `nm_ilhas`, `nm_bandos` (estado em JSONB) e `nm_log`, criadas sozinhas na primeira conexão; `nm_ilhas` é semeada de `navegacao_dados.py`. O banco só é acessível pela rede privada (VLAN), então não dá pra conectar do PC.
- **Sem `DATABASE_URL`: Google Sheets** (reserva/testes locais). Abas `NM_Ilhas`, `NM_Bandos`, `NM_Log` na planilha "Procurados Blues".

Os dois backends têm a mesma interface; os dados **não migram sozinhos** de um para o outro.

Ilhas: gerencie por `/navegacao_ilha_adicionar` e `/navegacao_ilha_remover`. `/navegacao_banco` mostra o backend em uso e testa a conexão. Tipos: `inicial`, `sincronizavel`, `secreta`, `principal`, `totto` (o arquipélago), `totto_ilha` (ilhas dentro de Totto), `calm` (nota = nível 1 ou 2). Área: 1, 2, 3, 4 ou `calm`.

**Ilhas de Totto Land ainda não estão cadastradas:** use `/navegacao_ilha_adicionar` com área `2` e tipo `totto_ilha`.

### Ligar o PostgreSQL na Discloud

1. Dashboard > Databases > Create database > PostgreSQL (mín. 512 MB de RAM, conta na RAM do plano).
2. Ativar **VLAN** na aplicação do bot (plano Diamond) e deixar bot e banco no mesmo cluster/Project.
3. Colocar `DATABASE_URL=postgresql://USUARIO:SENHA@HOST:PORTA/BANCO` no `.env` do bot na Discloud (URL do card "Private connection"). Nunca no Git.
4. Rebuild/deploy. Conferir com `/navegacao_banco`.

## Regras implementadas

1. Bando parte de Raijin, Risky Red ou Mystoria (`/navegacao_iniciar`).
2. `/navegar` sincroniza 3 ilhas distintas, cada agulha com tipo sorteado:
   - 🟢 Estável: CD normal, +1 progressão.
   - 🟡 Moderada: CD +2, +1,5 progressão.
   - 🔴 Instável: CD +5, **falha leva ao Calm Belt**, +3 progressões.
3. `/viajar bando agulha resultado`: o mestre informa o resultado do Teste de Navegação.
   - Sucesso: chega à ilha, ganha a progressão da agulha (área atual).
   - Falha: ilha secreta aleatória da **área atual** (sem progressão); se a agulha era Instável, ilha aleatória do **Calm Belt**. Em Totto Land não há ilha secreta: rola-se Desastre (`/encontromaritimo`).
4. Pool de sincronização: ilhas não visitadas da área atual (peso 1) e de áreas anteriores (peso `PESO_AREA_ANTERIOR` = 0,1). Ilhas de áreas ainda não exploradas nunca aparecem. Ilha visitada nunca volta.
5. Ilha principal (Dressrosa 1→2, Wano 2→3, Elbaph 3→Laugh Tale) entra no pool com 20 progressões na área (peso `PESO_PRINCIPAL` = 5). Ao chegar nela a progressão zera e a próxima área é liberada. Na área 4, Laugh Tale sempre aparece numa agulha.
6. **Totto Land** (Área 2):
   - Se uma agulha a sorteia (e o bando nunca saiu de lá), as 3 apontam pra ela. O bando vai (`/viajar`) ou espera 7 dias pra `/navegar` de novo (`forcar` ignora a espera).
   - Dentro: só ilhas `totto_ilha`, todas Estáveis, CD normal, +1 progressão cada, também contando pra área.
   - Sair: `/totto_sair` exige 5 progressões lá dentro. Depois, Totto vira ilha comum (uma agulha só) e dá pra voltar com as mesmas regras.
7. `/navegacao_ajustar` corrige área, progressão, local e flag de Totto (dessincroniza o Log Pose).

## Decisões assumidas (não vieram das regras; mude as constantes se não servir)

- Tipo da agulha: chance igual (1/3 cada), `PESOS_TIPO_AGULHA`.
- Progressão é ganha ao **chegar** na ilha. Ilhas secretas e do Calm Belt não dão progressão.
- Chegar na ilha principal e entrar em Totto Land não dão progressão.
- Calm Belt níveis 1 e 2 entram no mesmo sorteio (sem regra de nível por área).
- Hollow Horn é tratada como ilha comum da Área 2.
- "Reino Majiatsuka (área 2)" foi removido da lista da Área 1 (aparece só na Área 2).
- Nomes das ilhas principais (Dressrosa, Wano, Elbaph, Laugh Tale) foram adicionados por conta própria; não estavam nas listas.
