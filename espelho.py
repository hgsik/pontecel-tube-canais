"""Espelho dos feeds do PonteCel-Tube (roda no GitHub Actions a cada hora).

Para cada canal do tube.json, baixa o feed que o app usa (UULF = vídeos normais, UUSH = Shorts, e o feed do canal
como reserva) e grava em espelho/<chave>.xml. Só grava quando o feed veio com vídeos: se o YouTube estiver fora do
ar, a última cópia boa continua. Apaga as cópias de canais que saíram da lista.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "espelho")
BASE = "https://www.youtube.com/feeds/videos.xml?"


def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PonteCel-Tube-espelho"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError:
            return None  # 404/500 do YouTube: repetir na hora não adianta; a próxima rodada tenta de novo
        except (urllib.error.URLError, OSError):
            time.sleep(2 * (i + 1))
    return None


def chaves(cat):
    for c in cat["categorias"]:
        for ch in c["canais"]:
            cid = ch["id"]
            yield ("UUSH" if c.get("shorts") else "UULF") + cid[2:], "playlist_id"
            yield cid, "channel_id"


def main():
    cat = json.load(open(os.path.join(RAIZ, "tube.json"), encoding="utf-8"))
    os.makedirs(PASTA, exist_ok=True)
    queridas = dict(chaves(cat))
    ok = falhou = 0
    for chave, param in sorted(queridas.items()):
        xml = baixar(BASE + param + "=" + chave)
        if xml and "<entry>" in xml:
            with open(os.path.join(PASTA, chave + ".xml"), "w", encoding="utf-8", newline="\n") as f:
                f.write(xml)
            ok += 1
        else:
            falhou += 1
    for nome in os.listdir(PASTA):
        if nome.endswith(".xml") and nome[:-4] not in queridas:
            os.remove(os.path.join(PASTA, nome))
    print("feeds atualizados: %d; sem resposta (cópia anterior mantida): %d" % (ok, falhou))
    return 0


if __name__ == "__main__":
    sys.exit(main())
