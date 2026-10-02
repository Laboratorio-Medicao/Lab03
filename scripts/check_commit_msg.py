"""Rejeita mensagem de commit sem referência a Issue (#N).

Uso: python scripts/check_commit_msg.py <arquivo-com-a-mensagem>
Exit 0 = aceita; 1 = rejeitada (ou arquivo ilegível).
"""

import re
import sys

REFERENCIA = re.compile(r"#\d+")
EXEMPLO = "feat(pipeline): cria estrutura inicial (#3)"


def tem_referencia(mensagem: str) -> bool:
    # O git descarta linhas iniciadas por '#' (comentários do editor); ignorar igual.
    linhas = [l for l in mensagem.splitlines() if not l.startswith("#")]
    texto = "\n".join(linhas)
    if texto.startswith("Merge "):  # merges automáticos do git
        return True
    return REFERENCIA.search(texto) is not None


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        with open(argv[1], encoding="utf-8") as f:
            mensagem = f.read()
    except OSError as exc:
        print(f"erro ao ler a mensagem do commit: {exc}", file=sys.stderr)
        return 1
    if tem_referencia(mensagem):
        return 0
    print(
        "COMMIT REJEITADO: a mensagem precisa referenciar uma Issue (#N).\n"
        f"Exemplo: {EXEMPLO}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
