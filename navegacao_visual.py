"""
navegacao_visual.py
--------------------
Gera o GIF animado do Log Pose 3A: as 3 agulhas giram sem rumo, desaceleram e
travam apontando pras ilhas, já na cor do tipo de cada uma (verde = Estável,
amarelo = Moderada, vermelho = Instável). Quando Totto Land é apontada, as
3 agulhas se juntam numa só, rosa.

Usa Pillow. Chame via asyncio.to_thread (é CPU, leva ~1s). Devolve BytesIO
(GIF) ou None se algo falhar — o comando segue sem a animação.
"""

import io
import math
import random

TAM = 360          # tamanho final (px)
ESC = 2            # supersampling pra suavizar as bordas
FUNDO = (14, 24, 38)
ANEL = (205, 170, 90)
ANEL_ESCURO = (92, 74, 40)
CINZA = (120, 132, 148)
CORES = {"E": (72, 200, 120), "M": (240, 190, 60), "I": (230, 75, 70), "T": (235, 100, 160)}
# ângulos finais (graus, 0 = direita, sentido anti-horário na tela invertida) das 3 agulhas
ANGULOS = (-90.0, 30.0, 150.0)


def _fonte(tamanho: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Pillow antigo
        return ImageFont.load_default()


def _agulha(draw, cx, cy, ang, comp, cor, larg):
    a = math.radians(ang)
    ponta = (cx + comp * math.cos(a), cy + comp * math.sin(a))
    cauda = (cx - comp * 0.28 * math.cos(a), cy - comp * 0.28 * math.sin(a))
    px, py = -math.sin(a) * larg, math.cos(a) * larg
    draw.polygon([(cauda[0] + px * 0.6, cauda[1] + py * 0.6), (cx + px, cy + py), ponta,
                  (cx - px, cy - py), (cauda[0] - px * 0.6, cauda[1] - py * 0.6)], fill=cor)
    return ponta


def _frame(ang_atual, cores, numeros, pulso, brilho_ponta):
    from PIL import Image, ImageDraw
    t = TAM * ESC
    img = Image.new("RGB", (t, t), FUNDO)
    d = ImageDraw.Draw(img)
    c = t // 2
    raio = int(t * 0.44)

    # anel e marcações
    d.ellipse([c - raio, c - raio, c + raio, c + raio], outline=ANEL, width=6 * ESC // 2)
    d.ellipse([c - raio + 14 * ESC, c - raio + 14 * ESC, c + raio - 14 * ESC, c + raio - 14 * ESC],
              outline=ANEL_ESCURO, width=2 * ESC // 2 or 1)
    for k in range(36):
        a = math.radians(k * 10)
        r1 = raio - 14 * ESC
        r2 = r1 - (12 if k % 9 == 0 else 6) * ESC
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=ANEL if k % 9 == 0 else ANEL_ESCURO, width=2 * ESC // 2 or 1)

    # pulso ao travar
    if pulso > 0:
        r = int(raio * (0.55 + 0.45 * pulso))
        d.ellipse([c - r, c - r, c + r, c + r], outline=tuple(int(v * (1 - pulso) + f * pulso) for v, f in zip(ANEL, FUNDO)),
                  width=3 * ESC)

    # agulhas
    fonte = _fonte(15 * ESC)
    for ang, cor, num in zip(ang_atual, cores, numeros):
        ponta = _agulha(d, c, c, ang, raio - 26 * ESC, cor, 7 * ESC)
        if brilho_ponta and num is not None:
            r = 13 * ESC
            d.ellipse([ponta[0] - r, ponta[1] - r, ponta[0] + r, ponta[1] + r], fill=FUNDO, outline=cor, width=3 * ESC)
            d.text(ponta, str(num), fill=cor, font=fonte, anchor="mm")

    # pino central
    d.ellipse([c - 10 * ESC, c - 10 * ESC, c + 10 * ESC, c + 10 * ESC], fill=ANEL, outline=ANEL_ESCURO, width=2 * ESC)
    d.ellipse([c - 4 * ESC, c - 4 * ESC, c + 4 * ESC, c + 4 * ESC], fill=FUNDO)
    return img.resize((TAM, TAM), Image.LANCZOS)


def gerar_gif_logpose(tipos: list, totto: bool = False, seed=None):
    """tipos: lista de 'E'/'M'/'I' (uma por agulha, 1 a 3). Retorna BytesIO do GIF ou None."""
    try:
        rng = random.Random(seed)
        n = max(1, min(3, len(tipos)))
        finais = [ANGULOS[0]] * n if totto else list(ANGULOS[:n])
        cores_finais = [CORES["T"]] * n if totto else [CORES.get(t, CINZA) for t in tipos[:n]]
        numeros = [None if totto else i + 1 for i in range(n)]

        # cada agulha dá voltas diferentes antes de travar no ângulo final
        voltas = [rng.choice([2, 3, 4]) * 360 * rng.choice([1, -1]) for _ in range(n)]
        inicios = [rng.uniform(0, 360) for _ in range(n)]

        frames, duracoes = [], []
        giro = 30
        for f in range(giro):
            p = f / (giro - 1)
            suave = 1 - (1 - p) ** 3          # desacelera até parar
            angs = [fin + (1 - suave) * (v + ini - fin) for fin, v, ini in zip(finais, voltas, inicios)]
            frames.append(_frame(angs, [CINZA] * n, numeros, 0, False))
            duracoes.append(45)

        for f in range(10):                   # travou: ganha cor e um pulso
            p = f / 9
            cores = cores_finais if f >= 1 else [CINZA] * n
            frames.append(_frame(finais, cores, numeros, 1 - p if f else 0.0, True))
            duracoes.append(70)
        frames.append(_frame(finais, cores_finais, numeros, 0, True))
        duracoes.append(3500)                 # segura o resultado antes de repetir

        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                       duration=duracoes, loop=0, optimize=False, disposal=2)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"⚠️ Não consegui gerar o GIF do Log Pose: {e}")
        return None
