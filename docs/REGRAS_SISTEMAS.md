# Regras dos sistemas

## Procurados (planilha Google)

- Planilha: **"Procurados Blues"**, aba **"Procurados"**. Colunas: A = nome, B = tipo (`Pirata` ou `Marinheiro`). Linha 1 é cabeçalho.
- Duplicatas são comparadas sem diferenciar maiúsculas.
- `database.py` autentica com `credenciais.json` (conta de serviço). Erros de conexão ficam em `obter_ultimo_erro_conexao()` e são mostrados ao usuário.

## /procurado (caça)

1. Escolhe o procurado (autocomplete mostra só os disponíveis) e o mar (só regiões ativas com `tem_procurado`).
2. Sorteia uma ilha/local daquele mar com chance igual.
3. Registra a caça em `cacadas.db` com **trava de 14 dias** (`DIAS_TRAVA`). Enquanto a trava dura, ninguém pode caçar o mesmo nome.
4. Bloqueia quem está na **edição atual do jornal** (`jornal_atual`).
5. Embed com caçador, local, e timestamp de liberação.

Comandos auxiliares:
- `/procurados_ativos`: lista caçadas ativas (efêmero).
- `/procurado_liberar`: libera a trava antes do prazo.

Travas expiradas são apagadas automaticamente nas consultas.

## /encontromaritimo (navegação)

Regiões e tabelas (`cogs/encontro.py`, `REGIOES`). Cada tabela soma 100%.

| Região | cacada | pirata | marinha | cacador | rei_do_mar | nada |
|---|---|---|---|---|---|---|
| Paradise | 60 (sem ND) | 14 (ND 9) | 14 (ND 10) | 6 (ND 11) | 6 (ND 11) | — |
| Novo Mundo | 60 (sem ND) | 14 (ND 14) | 14 (ND 15) | 6 (ND 16) | 6 (ND 16) | — |
| Calm Belt | — | 9 (ND 16) | 9 (ND 16) | 12 (ND 16) | 30 (ND 16) | 40 |

- `cacada` = caçada na ilha (procurado andando pela região), sem combate direto.
- Opção `debug` mostra o número sorteado.

**Totto Land** não usa essa tabela:
- `/encontromaritimo` → **Desastre** (1d6): 1–3 frotas tarte (5/10/15d10 de dano), 4 e 5 oficiais (perseguição ou cerco, perdem metade ou todo o deslocamento), 6 → Embate (Técnica Combinada, CD 25 para escapar, tentativa a cada semana).
- `/desafiodasilhas [nc]` → 1d12 na exploração: 1–4 nada, 5–9 patrulha, 10–11 combatente (ND 14), 12 oficial (ND 15).
- NC (Nível de Confusão 0–10): NC ≥ 10 força **General Doce**; NC 8–9 força **Exército da Fúria** (ambos têm prioridade sobre o d12).
- Faixas de estado de caçada: 0–1 desconhecidos; 2–7 monitorados (+1 CD nos testes); 8–9 inimigos públicos; 10 alvos marcados.

## /exploracao (mesa) e /ler_poneglyph

- Tiers em `exploracao_data.json` (`paradise`, `blues`). Se o arquivo não existir ou estiver corrompido, recria com `DADOS_PADRAO`.
- Itens por tier:
  - `normal`: rola `0–100`, sucesso se `roll < chance`.
  - `prof_amador` / `prof_profissional`: Professor (chance do tier) + Contratado (50%). Contratado sorteia rank: Infame 50%, Desconhecido 30%, Famoso 20% (amador) ou prefixo Profissional.
  - `poneglyph`: se achou, convida `/ler_poneglyph`.
- `/ler_poneglyph` faz uma sequência de mensagens com `sleep` e sorteia o fragmento: pesos 45 / 40 / 7 / 7 / 1 (o último é a arma ancestral).
- Botão "Encaminhar" envia o embed para outro canal (ID ou link).

## Permissões

Todos os comandos de administração usam `is_allowed_role()`. Painéis (`/regioes`) também validam o cargo em cada botão. Mensagem padrão de negação: "❌ Você não tem permissão para usar esse comando."
