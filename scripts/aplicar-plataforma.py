"""Before the answer, classify inside the open platform and write that model and effort."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

GROK_HOME = Path(os.environ.get("GROK_HOME") or Path.home() / ".grok")


def grok_bin() -> str:
    override = os.environ.get("GROK_BIN")
    if override:
        return override
    exe = Path.home() / ".grok" / "bin" / "grok.exe"
    if exe.is_file():
        return str(exe)
    return "grok"
ROUTE_DIR = Path(os.environ.get("ESCOLHA_DE_MODELO_DIR") or Path.home() / ".escolha-de-modelo")
GROK_ROUTE_DIR = GROK_HOME / "escolha-de-modelo"
ROUTE_PATH = ROUTE_DIR / "ultima-rota.json"
LOG_JSONL = ROUTE_DIR / "rotas.jsonl"
LOG_TABLE = ROUTE_DIR / "rotas.md"
GEMINI_SETTINGS = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
OBSIDIAN_TABLE = (
    Path.home()
    / ".antigravity"
    / "Obsidian"
    / "Projetos"
    / "Escolha de Modelo"
    / "Markdown"
    / "Logs de rota.md"
)
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
PEDIDO_MAX = 400
TABLE_ROWS = 80

GROK_ANSWER = {
    "low": "formato, lista ou renome",
    "medium": "explicação ou edição simples",
    "high": "código, bug, desenho ou regra",
    "xhigh": "o esforço high não fechou",
}


def prompt_text(data: dict) -> str:
    for key in ("prompt", "userPrompt", "user_prompt", "message", "lastUserInput"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


ROTA_RE = re.compile(
    r"Rota:\s*(?P<situacao>[^·<\n]+?)\s*·\s*(?P<model>[^·<\n]+?)\s*·\s*esfor[cç]o\s+(?P<effort>[A-Za-z0-9]+)\s*·\s*(?P<estado>aplicado|pedido)",
    re.IGNORECASE,
)


def argv_value(flag: str) -> str:
    if flag in sys.argv:
        index = sys.argv.index(flag)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return ""


def argv_platform() -> str:
    if "--plataforma" in sys.argv:
        index = sys.argv.index("--plataforma")
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1].casefold()
    forced = argv_value("--plataforma") or os.environ.get("ESCOLHA_DE_MODELO_PLATAFORMA", "")
    return forced.casefold()


def platform_of(data: dict) -> str:
    forced = argv_platform()
    if forced in {"grok", "codex", "antigravity", "claude"}:
        return forced
    if os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_THREAD_ID"):
        return "codex"
    session_id = str(data.get("sessionId") or data.get("session_id") or os.environ.get("GROK_SESSION_ID") or "")
    if session_id and (GROK_HOME / "sessions").is_dir() and not data.get("modelName"):
        return "grok"
    return ""


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[0-9a-záàâãéêíóôõúüç]+", text.casefold()))


def bypass_requested(text: str) -> bool:
    """An explicit standalone bypass keeps the configured pair for this turn."""
    return re.search(r"\bbypass\b", text, re.IGNORECASE) is not None


def keep_configured_pair(data: dict, platform: str, text: str) -> None:
    """Read selectors and log the override without classifying or applying a model."""
    used = None
    try:
        if platform == "codex" and CODEX_CONFIG.is_file():
            used = selector_codex(CODEX_CONFIG.read_text(encoding="utf-8"))
        elif platform == "antigravity":
            used = selector_antigravity(data)
        elif platform == "claude":
            used = selector_claude(data)
        elif platform == "grok":
            session_id = str(data.get("sessionId") or data.get("session_id") or os.environ.get("GROK_SESSION_ID") or "")
            used = selector_grok(session_id, str(data.get("cwd") or os.getcwd()))
        choice = {
            "situacao": "bypass solicitado; manter seletor configurado",
            "model": used[0] if used else "",
            "effort": used[1] if used else "",
            "fonte": "bypass",
        }
        log_pair(choice, "aplicado" if selector_known(used) else "pedido", platform, used, text)
    except (OSError, ValueError):
        # An unreadable selector or unwritable log must not defeat the override.
        pass


def rules_grok(text: str) -> dict:
    folded = text.casefold()
    words = tokens(text)
    if "não fechou" in folded or "nao fechou" in folded or "tenta de novo" in folded or "xhigh" in words:
        effort = "xhigh"
    elif words & {"urgente", "latência", "latencia"} or "mais rápido" in folded or "mais rapido" in folded:
        return {
            "situacao": "latência",
            "model": "grok-4.7-build-fast",
            "effort": "high",
            "fonte": "regras",
        }
    elif words & {"typo", "renome", "renomear", "lista", "tabela", "format", "formato", "formatação", "formatacao"}:
        effort = "low"
    elif words & {"explica", "explicar", "explicação", "explicacao", "resumo", "porque"} or "por que" in folded:
        effort = "medium"
    else:
        effort = "high"
    return {
        "situacao": GROK_ANSWER[effort],
        "model": "grok-4.7",
        "effort": effort,
        "fonte": "regras",
    }


def accept_grok(choice: dict) -> dict | None:
    model = str(choice.get("model") or "")
    effort = str(choice.get("effort") or "")
    allowed = {"low", "medium", "high", "xhigh"}
    if model == "grok-4.7-build-fast" and effort in allowed:
        return choice
    if model == "grok-4.7" and effort in allowed:
        return choice
    return None


def classify_grok(text: str) -> dict:
    if os.environ.get("ESCOLHA_DE_MODELO_LLM") != "1" or not text.strip():
        return rules_grok(text)
    schema = {
        "type": "object",
        "properties": {
            "situacao": {"type": "string"},
            "model": {"type": "string"},
            "effort": {"type": "string"},
        },
        "required": ["situacao", "model", "effort"],
        "additionalProperties": False,
    }
    ask = (
        "Classifique o pedido para o Grok Build. "
        "model só pode ser grok-4.7 ou grok-4.7-build-fast. "
        "effort só pode ser low, medium, high ou xhigh. "
        "grok-4.7-build-fast só se o pedido pede latência. "
        "low para formato, medium para explicação, high para código ou desenho, "
        "xhigh só se o texto diz que high não fechou.\n"
        f"Pedido:\n{text[:4000]}"
    )
    env = os.environ.copy()
    env["ESCOLHA_DE_MODELO_INTERNO"] = "1"
    for key in ("GROK_SESSION_ID", "GROK_AGENT", "ESCOLHA_DE_MODELO_REGRAS"):
        env.pop(key, None)
    try:
        completed = subprocess.run(
            [
                grok_bin(),
                "-p",
                ask,
                "--model",
                "grok-4.7",
                "--reasoning-effort",
                "low",
                "--max-turns",
                "1",
                "--disable-web-search",
                "--no-subagents",
                "--verbatim",
                "--permission-mode",
                "dontAsk",
                "--system-prompt-override",
                "Classifique o pedido. Responda só situacao, model e effort. Não use ferramentas.",
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(schema, ensure_ascii=False),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=35,
            env=env,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return rules_grok(text)
    choice = choice_from_stdout(completed.stdout or "")
    return choice or rules_grok(text)


def choice_from_stdout(raw: str) -> dict | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for _ in range(3):
        if not isinstance(parsed, dict):
            return None
        inner = parsed.get("structured_output", parsed.get("structuredOutput"))
        if isinstance(inner, dict):
            parsed = inner
            continue
        if isinstance(inner, str):
            try:
                parsed = json.loads(inner)
            except json.JSONDecodeError:
                return None
            continue
        text = parsed.get("text")
        if isinstance(text, str) and "model" not in parsed:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return None
            continue
        result = parsed.get("result")
        if isinstance(result, dict):
            parsed = result
            continue
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                return None
            continue
        break
    if not isinstance(parsed, dict):
        return None
    choice = {
        "situacao": str(parsed.get("situacao") or "classificado"),
        "model": str(parsed.get("model") or ""),
        "effort": str(parsed.get("effort") or ""),
        "fonte": "grok-4.7-low",
    }
    return accept_grok(choice)


def session_summary(session_id: str, cwd: str) -> Path | None:
    direct = GROK_HOME / "sessions" / quote(cwd, safe="") / session_id / "summary.json"
    if direct.is_file():
        return direct
    root = GROK_HOME / "sessions"
    if not root.is_dir():
        return None
    matches = list(root.glob(f"*/{session_id}/summary.json"))
    return matches[0] if matches else None


def selector_grok(session_id: str, cwd: str) -> tuple[str, str] | None:
    path = session_summary(session_id, cwd)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return str(data.get("current_model_id") or ""), str(data.get("reasoning_effort") or "")


def apply_grok(session_id: str, cwd: str, choice: dict) -> str:
    selector = selector_grok(session_id, cwd)
    if selector is None:
        return "pedido"
    current, effort = selector
    model = choice["model"]
    if current in {"grok-4.6", "grok-4.5"} and model == "grok-4.7":
        model = current
        choice["model"] = current
    if current == model and effort == choice["effort"]:
        return "aplicado"
    return "pedido"


def rules_antigravity(text: str) -> dict:
    folded = text.casefold()
    words = tokens(text)
    if "não fechou" in folded or "nao fechou" in folded or "hydrogen" in words:
        return {
            "situacao": "o Argon não fechou",
            "model": "Gemini 4 Hydrogen",
            "effort": "High",
            "fonte": "regras",
        }
    if words & {"typo", "renome", "renomear", "lista", "tabela", "format", "formato", "extração", "extracao"}:
        return {
            "situacao": "formato ou extração",
            "model": "Gemini 3.8 Flash",
            "effort": "Low",
            "fonte": "regras",
        }
    if words & {"explica", "explicar", "explicação", "explicacao", "resumo"} or "por que" in folded:
        return {
            "situacao": "explicação ou rascunho",
            "model": "Gemini 3.8 Flash",
            "effort": "Medium",
            "fonte": "regras",
        }
    return {
        "situacao": "código do dia",
        "model": "Gemini 4 Argon",
        "effort": "Low",
        "fonte": "regras",
    }


def rules_claude(text: str) -> dict:
    folded = text.casefold()
    words = tokens(text)
    if words & {"fable"} or "muitas horas" in folded:
        return {
            "situacao": "sessão longa",
            "model": "Claude Fable 5.1",
            "effort": "high",
            "fonte": "regras",
        }
    if "não fechou" in folded or "nao fechou" in folded or words & {"síntese", "sintese"}:
        return {
            "situacao": "o Sonnet não fechou",
            "model": "Claude Opus 5.5",
            "effort": "medium",
            "fonte": "regras",
        }
    if words & {"typo", "renome", "renomear", "lista", "tabela", "format", "formato", "extração", "extracao", "lote"}:
        return {
            "situacao": "lote ou extração",
            "model": "Claude Haiku 5.5",
            "effort": "low",
            "fonte": "regras",
        }
    return {
        "situacao": "código ou regra",
        "model": "Claude Sonnet 5.5",
        "effort": "high",
        "fonte": "regras",
    }


def split_selector(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    matched = re.fullmatch(r"(.+?)\s*\(([^)]+)\)", raw)
    if matched:
        return matched.group(1).strip(), matched.group(2).strip()
    parts = raw.split("-")
    efforts = {"low", "medium", "high", "xhigh"}
    if len(parts) > 1 and parts[-1].casefold() in efforts:
        return raw[: -(len(parts[-1]) + 1)], parts[-1]
    return raw, ""


def same_pair(suggested_model: str, suggested_effort: str, used_model: str, used_effort: str) -> bool:
    if not used_model or not used_effort:
        return False
    left = suggested_model.casefold()
    right = used_model.casefold()
    markers = ("flash", "argon", "hydrogen", "haiku", "sonnet", "opus", "fable", "luna", "terra", "astra", "sol")
    model_ok = left == right or left in right or right in left
    if not model_ok:
        model_ok = any(marker in left and marker in right for marker in markers)
    return model_ok and suggested_effort.casefold() == used_effort.casefold()


def selector_antigravity(data: dict) -> tuple[str, str]:
    raw = str(data.get("modelName") or "")
    if not raw and GEMINI_SETTINGS.is_file():
        try:
            settings = json.loads(GEMINI_SETTINGS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            settings = {}
        if isinstance(settings, dict):
            raw = str(settings.get("model") or "")
    return split_selector(raw)


def selector_claude(data: dict) -> tuple[str, str]:
    raw = str(data.get("model") or os.environ.get("CLAUDE_MODEL") or os.environ.get("ANTHROPIC_MODEL") or "")
    if not raw and CLAUDE_SETTINGS.is_file():
        try:
            settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            settings = {}
        if isinstance(settings, dict):
            raw = str(settings.get("model") or "")
    return split_selector(raw)


def rules_codex(text: str) -> dict:
    folded = text.casefold()
    words = tokens(text)
    if words & {"screenshot", "tela", "visão", "visao"}:
        return {"situacao": "tela", "model": "gpt-6.1-terra", "effort": "low", "fonte": "regras"}
    if "não fechou" in folded or "nao fechou" in folded or "astra" in words:
        return {"situacao": "o Sol não fechou", "model": "gpt-6-astra", "effort": "low", "fonte": "regras"}
    if words & {"typo", "renome", "renomear", "lista", "tabela", "format", "formato", "extração", "extracao"}:
        return {"situacao": "formato ou extração", "model": "gpt-6-luna", "effort": "low", "fonte": "regras"}
    if words & {"bug", "desenho", "arquitetura", "refactor"}:
        return {"situacao": "código difícil", "model": "gpt-6.1-sol", "effort": "high", "fonte": "regras"}
    return {"situacao": "código do dia", "model": "gpt-6.1-sol", "effort": "low", "fonte": "regras"}


def selector_codex(text: str) -> tuple[str, str]:
    model = ""
    effort = ""
    for line in text.splitlines():
        if line.startswith("model = ") and not model:
            model = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("model_reasoning_effort = ") and not effort:
            effort = line.split("=", 1)[1].strip().strip('"')
    return model, effort


def apply_codex(choice: dict) -> tuple[str, tuple[str, str] | None]:
    if not CODEX_CONFIG.is_file():
        return "pedido", None
    text = CODEX_CONFIG.read_text(encoding="utf-8")
    selector = selector_codex(text)
    lines = text.splitlines()
    found_model = False
    found_effort = False
    rebuilt = []
    for line in lines:
        if line.startswith("model = ") and not found_model:
            rebuilt.append(f'model = "{choice["model"]}"')
            found_model = True
        elif line.startswith("model_reasoning_effort = ") and not found_effort:
            rebuilt.append(f'model_reasoning_effort = "{choice["effort"]}"')
            found_effort = True
        else:
            rebuilt.append(line)
    if not found_model or not found_effort:
        return "pedido", selector
    updated = "\n".join(rebuilt) + ("\n" if text.endswith("\n") else "")
    if updated != text:
        CODEX_CONFIG.write_text(updated, encoding="utf-8")
        return "pedido", selector
    return "aplicado", selector


def clip(text: str, limit: int = PEDIDO_MAX) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def cell(text: str) -> str:
    return clip(text, 280).replace("|", "\\|")


def write_route(
    choice: dict,
    estado: str,
    platform: str,
    extra: dict | None = None,
    pedido: str = "",
) -> None:
    ROUTE_DIR.mkdir(parents=True, exist_ok=True)
    usado_modelo = ""
    usado_esforco = ""
    if extra:
        usado_modelo = str(extra.get("seletor_modelo") or "")
        usado_esforco = str(extra.get("seletor_esforco") or "")
    analisado = (
        f"plataforma {platform}; situação {choice['situacao']}; "
        f"fonte {choice.get('fonte', 'regras')}"
    )
    payload = {
        "quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plataforma": platform,
        "pedido": clip(pedido),
        "analisado": analisado,
        "sugerido_modelo": choice["model"],
        "sugerido_esforco": choice["effort"],
        "utilizado_modelo": usado_modelo,
        "utilizado_esforco": usado_esforco,
        "situacao": choice["situacao"],
        "model": choice["model"],
        "effort": choice["effort"],
        "fonte": choice.get("fonte", ""),
        "estado": estado,
    }
    if extra:
        payload.update(extra)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    ROUTE_PATH.write_text(text, encoding="utf-8")
    if not os.environ.get("ESCOLHA_DE_MODELO_DIR"):
        try:
            GROK_ROUTE_DIR.mkdir(parents=True, exist_ok=True)
            (GROK_ROUTE_DIR / "ultima-rota.json").write_text(text, encoding="utf-8")
        except OSError:
            pass
    append_log(payload)


def ensure_log_migrated() -> None:
    old = GROK_ROUTE_DIR / "rotas.jsonl"
    if LOG_JSONL.exists() or not old.is_file() or LOG_JSONL == old:
        return
    ROUTE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_JSONL.write_text(old.read_text(encoding="utf-8"), encoding="utf-8")


def append_log(row: dict) -> None:
    ensure_log_migrated()
    slim = {
        "quando": row.get("quando", ""),
        "plataforma": row.get("plataforma", ""),
        "pedido": row.get("pedido", ""),
        "analisado": row.get("analisado", ""),
        "sugerido_modelo": row.get("sugerido_modelo", row.get("model", "")),
        "sugerido_esforco": row.get("sugerido_esforco", row.get("effort", "")),
        "utilizado_modelo": row.get("utilizado_modelo", row.get("seletor_modelo", "")),
        "utilizado_esforco": row.get("utilizado_esforco", row.get("seletor_esforco", "")),
        "estado": row.get("estado", ""),
        "origem": row.get("origem", "pedido"),
    }
    with LOG_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(slim, ensure_ascii=False) + "\n")
    rewrite_table()


def load_log_rows() -> list[dict]:
    if not LOG_JSONL.is_file():
        return []
    rows = []
    for line in LOG_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows[-TABLE_ROWS:]


def rewrite_table() -> None:
    rows = load_log_rows()
    lines = [
        "# Logs de rota",
        "",
        "Cada linha é um pedido classificado pelo hook de uma das quatro IDEs. "
        "Pedido é o texto enviado. Análise é a situação e a fonte. "
        "Sugerido é o par escolhido. Utilizado é o seletor aberto na hora.",
        "",
        "| Quando (UTC) | Plataforma | Origem | Pedido | Análise | Sugerido | Utilizado | Estado |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in reversed(rows):
        sugerido = f"{row.get('sugerido_modelo', '')} / {row.get('sugerido_esforco', '')}"
        utilizado = f"{row.get('utilizado_modelo', '')} / {row.get('utilizado_esforco', '')}"
        if utilizado.strip() == "/":
            utilizado = "(seletor não lido)"
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(str(row.get("quando", ""))),
                    cell(str(row.get("plataforma", ""))),
                    cell(str(row.get("origem", "pedido"))),
                    cell(str(row.get("pedido", ""))),
                    cell(str(row.get("analisado", ""))),
                    cell(sugerido),
                    cell(utilizado),
                    cell(str(row.get("estado", ""))),
                ]
            )
            + " |"
        )
    lines.append("")
    text = "\n".join(lines)
    LOG_TABLE.write_text(text, encoding="utf-8")
    if not os.environ.get("ESCOLHA_DE_MODELO_DIR"):
        try:
            GROK_ROUTE_DIR.mkdir(parents=True, exist_ok=True)
            (GROK_ROUTE_DIR / "rotas.md").write_text(text, encoding="utf-8")
        except OSError:
            pass
    try:
        OBSIDIAN_TABLE.parent.mkdir(parents=True, exist_ok=True)
        OBSIDIAN_TABLE.write_text(text, encoding="utf-8")
    except OSError:
        pass


def rota_from_transcript(path: Path) -> dict | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    items = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    last_user = -1
    for index, item in enumerate(items):
        if item.get("type") == "USER_INPUT":
            last_user = index
    last = None
    for item in items[last_user + 1 :]:
        if item.get("type") != "PLANNER_RESPONSE":
            continue
        for match in ROTA_RE.finditer(str(item.get("content") or "")):
            last = {key: value.strip() for key, value in match.groupdict().items()}
    return last


def log_resposta(data: dict, platform: str) -> None:
    raw_path = str(data.get("transcriptPath") or "")
    path = Path(os.path.expanduser(raw_path)) if raw_path else None
    if path is None or not path.is_file():
        return
    declared = rota_from_transcript(path)
    if declared is None:
        return
    pedido = prompt_text(data)
    rules = {
        "antigravity": rules_antigravity,
        "claude": rules_claude,
        "codex": rules_codex,
        "grok": rules_grok,
    }.get(platform, rules_antigravity)
    choice = rules(pedido)
    estado = declared["estado"].casefold()
    for row in reversed(load_log_rows()[-6:]):
        if (
            row.get("origem") == "resposta"
            and row.get("pedido") == clip(pedido)
            and row.get("utilizado_modelo") == declared["model"]
            and row.get("utilizado_esforco") == declared["effort"]
            and row.get("estado") == estado
        ):
            return
    extra = {
        "seletor_modelo": declared["model"],
        "seletor_esforco": declared["effort"],
        "origem": "resposta",
        "analisado": (
            f"plataforma {platform}; situação {declared['situacao']}; fonte linha Rota"
        ),
    }
    write_route(choice, estado, platform, extra, pedido)


def selector_known(used: tuple[str, str] | None) -> bool:
    return used is not None and bool(used[0]) and bool(used[1])


def hold_reason(platform: str, choice: dict, used: tuple[str, str]) -> str:
    if platform == "grok":
        return (
            f"A sessão está em {used[0]} esforço {used[1]}. "
            f"Rode `/model {choice['model']}` e `/effort {choice['effort']}` "
            "e reenvie o pedido. O hook não alcança session/set_config_option."
        )
    if platform == "codex":
        return (
            f"A sessão está em {used[0]} esforço {used[1]}. "
            f"Rode `/model {choice['model']} --reasoning={choice['effort']}` "
            "e reenvie o pedido. A gravação em config.toml vale para a próxima sessão."
        )
    if platform == "antigravity":
        return (
            f"A sessão está em {used[0]} ({used[1]}). "
            f"Rode `/model {choice['model']} ({choice['effort']})` "
            "e reenvie o pedido. O hook não troca o modelo da chamada já aberta."
        )
    return (
        f"A sessão está em {used[0]} esforço {used[1]}. "
        f"Rode `/model` e escolha {choice['model']} com esforço {choice['effort']}, "
        "depois reenvie o pedido. O hook não troca o seletor do Claude Code."
    )


def emit_hold(platform: str, choice: dict, used: tuple[str, str]) -> None:
    reason = hold_reason(platform, choice, used)
    if platform == "antigravity":
        json.dump(
            {
                "terminationBehavior": "terminate",
                "injectSteps": [{"errorMessage": {"userMessage": reason}}],
            },
            sys.stdout,
            ensure_ascii=False,
        )
        return
    json.dump({"decision": "block", "reason": reason}, sys.stdout, ensure_ascii=False)


def log_pair(choice: dict, estado: str, platform: str, used: tuple[str, str] | None, pedido: str) -> None:
    extra = None
    if used is not None:
        extra = {"seletor_modelo": used[0], "seletor_esforco": used[1]}
    write_route(choice, estado, platform, extra, pedido)


def main() -> int:
    if os.environ.get("ESCOLHA_DE_MODELO_INTERNO") == "1":
        return 0
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0
    text = prompt_text(data)
    if bypass_requested(text):
        platform = platform_of(data) or "antigravity"
        if argv_value("--fase") != "resposta":
            keep_configured_pair(data, platform, text)
        if platform == "antigravity":
            json.dump({"decision": "allow"}, sys.stdout, ensure_ascii=False)
        return 0
    if argv_value("--fase") == "resposta":
        platform = platform_of(data) or "antigravity"
        log_resposta(data, platform)
        if platform == "antigravity":
            json.dump({"decision": "allow"}, sys.stdout, ensure_ascii=False)
        return 0
    if data.get("invocationNum") not in (None, 0, "0"):
        return 0
    text = prompt_text(data)
    session_id = str(data.get("sessionId") or data.get("session_id") or os.environ.get("GROK_SESSION_ID") or "")
    cwd = str(data.get("cwd") or data.get("workspacePaths") or os.getcwd())
    if isinstance(cwd, list):
        cwd = str(cwd[0]) if cwd else os.getcwd()
    platform = platform_of(data)
    if platform == "grok":
        choice = classify_grok(text)
        selector = selector_grok(session_id, cwd)
        estado = apply_grok(session_id, cwd, choice)
        extra = {
            "comandos": [f"/model {choice['model']}", f"/effort {choice['effort']}"],
        }
        if selector is not None:
            extra["seletor_modelo"] = selector[0]
            extra["seletor_esforco"] = selector[1]
        write_route(choice, estado, "grok", extra, text)
        if estado == "pedido" and selector_known(selector):
            emit_hold("grok", choice, selector)
        return 0
    elif platform == "codex":
        choice = rules_codex(text)
        estado, selector = apply_codex(choice)
        log_pair(choice, estado, "codex", selector, text)
        if estado == "pedido" and selector_known(selector):
            emit_hold("codex", choice, selector)
    elif platform == "antigravity":
        choice = rules_antigravity(text)
        used = selector_antigravity(data)
        estado = "aplicado" if same_pair(choice["model"], choice["effort"], used[0], used[1]) else "pedido"
        log_pair(choice, estado, "antigravity", used, text)
        if estado == "pedido" and selector_known(used):
            emit_hold("antigravity", choice, used)
    elif platform == "claude":
        choice = rules_claude(text)
        used = selector_claude(data)
        estado = "aplicado" if same_pair(choice["model"], choice["effort"], used[0], used[1]) else "pedido"
        log_pair(choice, estado, "claude", used, text)
        if estado == "pedido" and selector_known(used):
            emit_hold("claude", choice, used)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
