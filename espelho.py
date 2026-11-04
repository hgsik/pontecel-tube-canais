"""Espelho dos feeds do PonteCel-Tube (roda no GitHub Actions a cada hora).

Para cada canal do tube.json, baixa o feed que o app usa (UULF = vídeos normais, UUSH = Shorts, e o feed do canal
como reserva) e grava em espelho/<chave>.xml. Só grava quando o feed veio com vídeos: se o YouTube estiver fora do
ar, a última cópia boa continua. Os feeds que falharem ganham mais duas chances na mesma rodada, com uma pausa antes
(o YouTube costuma falhar por alguns minutos e voltar). Apaga as cópias de canais que saíram da lista.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "espelho")
BASE = "https://www.youtube.com/feeds/videos.xml?"
PASSADAS = 3          # 1ª passada + 2 repescagens só dos que falharam
PAUSA_REPESCAGEM = 90  # segundos antes de cada repescagem
PAUSA_ENTRE = 0.5      # segundos entre um feed e outro


def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PonteCel-Tube-espelho"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError:
            return None  # 404/500 do YouTube: fica para a repescagem
        except (urllib.error.URLError, OSError):
            time.sleep(2 * (i + 1))
    return None


def chaves(cat):
    for c in cat["categorias"]:
        for ch in c["canais"]:
            cid = ch["id"]
            yield ("UUSH" if c.get("shorts") else "UULF") + cid[2:], "playlist_id"
            yield cid, "channel_id"


def canais(cat):
    vistos = {}
    for c in cat["categorias"]:
        for ch in c["canais"]:
            vistos.setdefault(ch["id"], (ch["nome"], set()))[1].add(("UUSH" if c.get("shorts") else "UULF") + ch["id"][2:])
    return vistos


def gravar(chave, xml):
    with open(os.path.join(PASTA, chave + ".xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)


def main():
    cat = json.load(open(os.path.join(RAIZ, "tube.json"), encoding="utf-8"))
    os.makedirs(PASTA, exist_ok=True)
    queridas = dict(chaves(cat))
    pendentes = sorted(queridas)
    ok = 0
    for passada in range(PASSADAS):
        if not pendentes:
            break
        if passada:
            print("repescagem %d: %d feeds, depois de %ds" % (passada, len(pendentes), PAUSA_REPESCAGEM))
            time.sleep(PAUSA_REPESCAGEM)
        falharam = []
        for chave in pendentes:
            xml = baixar(BASE + queridas[chave] + "=" + chave)
            if xml and "<entry>" in xml:
                gravar(chave, xml)
                ok += 1
            else:
                falharam.append(chave)
            time.sleep(PAUSA_ENTRE)
        pendentes = falharam
    for nome in os.listdir(PASTA):
        if nome.endswith(".xml") and nome[:-4] not in queridas:
            os.remove(os.path.join(PASTA, nome))
    print("feeds atualizados: %d; sem resposta (cópia anterior mantida): %d" % (ok, len(pendentes)))
    # Canais sem nenhuma cópia (nem do feed principal, nem do feed do canal): o app não teria reserva para eles.
    tem = {n[:-4] for n in os.listdir(PASTA) if n.endswith(".xml")}
    sem = [nome for cid, (nome, principais) in canais(cat).items() if cid not in tem and not (principais & tem)]
    if sem:
        print("::warning::Canais sem cópia no espelho (%d): %s" % (len(sem), ", ".join(sorted(sem))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
