"""Stop hook: the visible reply must start with a same-platform Rota line."""
import json
import os
import sys

LINE = (
    "Rota: <situação> · <modelo desta plataforma> · esforço <nível> · aplicado "
    "quando o seletor aberto já está nesse par, ou · pedido quando não está. "
    "Não nomeie outra família. Mantenha o restante da resposta e pare."
)


def main() -> int:
    if os.environ.get("ESCOLHA_DE_MODELO_INTERNO") == "1":
        return 0
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0
    reason = str(data.get("reason") or "")
    if reason and reason not in ("end_turn", "endTurn"):
        return 0
    if data.get("stopHookActive") or data.get("stop_hook_active"):
        return 0
    text = data.get("lastAssistantMessage") or data.get("last_assistant_message") or ""
    if not isinstance(text, str):
        text = str(text)
    first = text.lstrip("\ufeff \t\r\n").splitlines()
    if first and first[0].startswith("Rota:") and "melhor em" not in first[0].casefold():
        return 0
    json.dump(
        {
            "decision": "block",
            "reason": "A primeira linha visível da resposta tem de ser a escolha. " + LINE,
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
