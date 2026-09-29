"""Verificador de entrega · Proyecto de la Unidad 1 · ACD-2504

Uso, en la raíz de su repositorio:   python verificar_entrega.py

Revisa la FORMA de la entrega (estructura, secretos, datos intactos, pruebas, bitácora,
evaluación y orden de los commits). No revisa la calidad: eso lo hace el docente con la rúbrica.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
HASHES = {
    "data/denue_tampico_madero.csv": "381803ded8cecf649b0d529de133d334a3dafcd2bb9490c26f1a0d23fb981e94",
    "data/sectores_scian.csv": "712c8fb4d60ab59bac00534373c4d61704c546a444e1807057d197ad0118cca9",
    "data/mini_denue.csv": "2c77b5aa3829c0ffc5d0c58afeb7f6f512910537b7b7c43f58c473e5074064e4",
    "data/preguntas_prueba.json": "1707a93ea28de2215f035660da59bfa8a24e79a5fd0c87118b24420dd99307b0",
}
IDS = ["P%02d" % i for i in range(1, 11)]
ARCHIVOS = [
    "README.md", "requirements.txt", ".env.example", ".gitignore", "traza_manual.md",
    "app/__init__.py", "app/herramientas.py", "app/modelo.py", "app/modelo_simulado.py", "app/agente.py",
    "app/guardia.py", "app/cli.py", "app/lote.py", "app/evaluar.py", "app/bot.py", "prompts/sistema.md",
    "pruebas/__init__.py", "pruebas/prueba_herramientas.py",
    "evaluacion/__init__.py", "evaluacion/calcular_esperadas.py", "evaluacion/esperadas.json",
    "evaluacion/resultados.json", "evaluacion/analisis.md",
    *HASHES,
]

resultados = []


def informe(estado, texto):
    resultados.append(estado)
    print("[%s] %s" % (estado.ljust(5), texto))


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def primer_commit(ruta):
    """Hash del primer commit que agregó la ruta, o None."""
    salida = git("log", "--diff-filter=A", "--follow", "--format=%H", "--", ruta)
    return salida.splitlines()[-1] if salida else None


def antes(commit_a, commit_b):
    """True si commit_a es un ancestro estricto de commit_b en el historial."""
    return commit_a != commit_b and git("merge-base", "--is-ancestor", commit_a, commit_b) is not None


def sha256(ruta):
    return hashlib.sha256((RAIZ / ruta).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def leer(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8", errors="ignore") if (RAIZ / ruta).exists() else ""


# 1. Estructura
faltan = [a for a in ARCHIVOS if not (RAIZ / a).exists()]
informe("OK" if not faltan else "FALTA", "Estructura de archivos" + ("" if not faltan else ": " + ", ".join(faltan)))

# 2. Secretos
es_repo = git("rev-parse", "--is-inside-work-tree") == "true"
if not es_repo:
    informe("FALTA", "La carpeta no es un repositorio de Git")
else:
    rastreados = git("ls-files").splitlines()
    informe("OK" if ".env" not in rastreados else "FALTA", ".env no está en el repositorio")
    con_clave = [a for a in rastreados if (RAIZ / a).is_file() and (RAIZ / a).stat().st_size < 1_000_000
                 and re.search(r"AIza[0-9A-Za-z_\-]{30,}", leer(a))]
    informe("OK" if not con_clave else "FALTA",
            "Sin claves de API en archivos rastreados" + ("" if not con_clave else ": " + ", ".join(con_clave)))
informe("OK" if re.search(r"^\.env\s*$", leer(".gitignore"), re.M) else "FALTA", ".gitignore contiene .env")

# Bot de Telegram: token, variables y reglas de diseño
if es_repo:
    con_token = [a for a in rastreados if (RAIZ / a).is_file() and (RAIZ / a).stat().st_size < 1_000_000
                 and re.search(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b", (RAIZ / a).read_text(encoding="utf-8", errors="ignore"))]
    informe("OK" if not con_token else "FALTA",
            "Sin tokens de Telegram en archivos rastreados" + ("" if not con_token else ": " + ", ".join(con_token)))
ejemplo = (RAIZ / ".env.example").read_text(encoding="utf-8", errors="ignore") if (RAIZ / ".env.example").exists() else ""
informe("OK" if "TELEGRAM_BOT_TOKEN" in ejemplo and "TELEGRAM_USUARIOS_PERMITIDOS" in ejemplo else "FALTA",
        ".env.example declara TELEGRAM_BOT_TOKEN y TELEGRAM_USUARIOS_PERMITIDOS")
bot = (RAIZ / "app/bot.py").read_text(encoding="utf-8", errors="ignore") if (RAIZ / "app/bot.py").exists() else ""
if bot:
    informe("OK" if "TELEGRAM_USUARIOS_PERMITIDOS" in bot else "FALTA", "app/bot.py usa la lista de usuarios permitidos")
    informe("OK" if re.search(r"to_thread|run_in_executor", bot) else "FALTA",
            "app/bot.py corre el agente en otro hilo (asyncio.to_thread)")
    informe("OK" if not re.search(r"google\.genai|from google import genai", bot) else "FALTA",
            "app/bot.py no llama a Gemini directamente")
imagenes = [p for p in (RAIZ / "evidencia").glob("telegram*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")] \
    if (RAIZ / "evidencia").exists() else []
informe("OK" if imagenes else "FALTA", "Captura de Telegram en evidencia/")


# 3. Datos intactos
for ruta, esperado in HASHES.items():
    if (RAIZ / ruta).exists():
        informe("OK" if sha256(ruta) == esperado else "FALTA", "%s sin modificar" % ruta)

# 4. Contratos revisables sin el modelo
modelo = leer("app/modelo.py")
informe("OK" if re.search(r"AutomaticFunctionCallingConfig\(\s*disable\s*=\s*True", modelo) else "FALTA",
        "app/modelo.py desactiva la ejecución automática de funciones")
peligrosos = [p.name for p in (RAIZ / "app").glob("*.py")
              if re.search(r"(?<![\w.])(eval|exec)\s*\(", p.read_text(encoding="utf-8", errors="ignore"))]
informe("OK" if not peligrosos else "FALTA",
        "app/ no usa eval() ni exec()" + ("" if not peligrosos else ": " + ", ".join(peligrosos)))
calc = leer("evaluacion/calcular_esperadas.py")
informe("OK" if calc and not re.search(r"^\s*(from|import)\s+app\b", calc, re.M) else "FALTA",
        "calcular_esperadas.py no importa nada de app/")

# 5. Pruebas
if (RAIZ / "pruebas/prueba_herramientas.py").exists():
    n = len(re.findall(r"^\s*assert\b", leer("pruebas/prueba_herramientas.py"), re.M))
    informe("OK" if n >= 23 else "FALTA", "pruebas/prueba_herramientas.py tiene %d comprobaciones (mínimo 23)" % n)
    r = subprocess.run([sys.executable, "-m", "pruebas.prueba_herramientas"], cwd=RAIZ, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    informe("OK" if r.returncode == 0 else "FALTA",
            "Las pruebas pasan" + ("" if r.returncode == 0 else ": " + (r.stderr.strip().splitlines() or ["?"])[-1]))

# 6. Esperadas
try:
    esperadas = {e["id"]: e for e in json.loads(leer("evaluacion/esperadas.json"))["esperadas"]}
    sin = [i for i in IDS if i not in esperadas]
    manuales_ok = all(esperadas[i].get("revision") == "manual" and esperadas[i].get("criterio") for i in ("P09", "P10") if i in esperadas)
    auto_ok = all(esperadas[i].get("revision") == "automatica" and esperadas[i].get("cifras_clave") for i in IDS[:8] if i in esperadas)
    informe("OK" if not sin and manuales_ok and auto_ok else "FALTA",
            "esperadas.json: 10 preguntas, P01-P08 con cifras_clave y P09-P10 manuales con criterio")
except (json.JSONDecodeError, KeyError, TypeError):
    informe("FALTA", "evaluacion/esperadas.json no es válido")

# 7. Bitácora real
finales, archivos_reales, inicios_tg, fines = {}, [], set(), set()
for ruta in sorted((RAIZ / "logs").glob("corrida-*.jsonl")):
    real = False
    for linea in leer(str(ruta.relative_to(RAIZ))).splitlines():
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if ev.get("modelo") not in (None, "simulado"):
            real = True
            if ev.get("evento") == "fin":
                finales[ev.get("id")] = ev
                fines.add((ev.get("corrida"), ev.get("id")))
            if ev.get("evento") == "inicio" and ev.get("canal") == "telegram" and not str(ev.get("usuario", "")).isdigit():
                inicios_tg.add((ev.get("corrida"), ev.get("id")))
    if real:
        archivos_reales.append(ruta)
tg = len(inicios_tg & fines)
informe("OK" if tg >= 3 else "FALTA", "Preguntas reales respondidas desde Telegram con usuario anónimo: %d (mínimo 3)" % tg)
sin = [i for i in IDS if i not in finales]
informe("OK" if not sin else "FALTA", "Eventos «fin» reales para las 10 preguntas" + ("" if not sin else "; faltan: " + ", ".join(sin)))
herr = sum(1 for p in archivos_reales for l in leer(str(p.relative_to(RAIZ))).splitlines() if '"evento": "herramienta"' in l)
informe("OK" if herr >= 10 else "FALTA", "La bitácora real registra %d eventos «herramienta»" % herr)

if es_repo and (RAIZ / "evaluacion/esperadas.json").exists() and archivos_reales:
    t_esp = primer_commit("evaluacion/esperadas.json")
    t_logs = [primer_commit(str(p.relative_to(RAIZ)).replace("\\", "/")) for p in archivos_reales]
    t_logs = [t for t in t_logs if t is not None]
    if t_esp is None or not t_logs:
        informe("FALTA", "esperadas.json y la bitácora real deben estar en commits")
    else:
        informe("OK" if all(antes(t_esp, t) for t in t_logs) else "FALTA",
                "esperadas.json tiene un commit anterior a la bitácora real")

# 8. evaluar.py corre
if archivos_reales and (RAIZ / "app/evaluar.py").exists():
    r = subprocess.run([sys.executable, "-m", "app.evaluar", *[str(p.relative_to(RAIZ)) for p in archivos_reales]],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    informe("OK" if r.returncode == 0 else "FALTA", "python -m app.evaluar corre con las bitácoras reales")

# 9. Traza, análisis y README
traza = leer("traza_manual.md")
informe("OK" if traza and "(escriba aquí)" not in traza and len(traza) > 3000 else "FALTA", "traza_manual.md llena")
analisis = leer("evaluacion/analisis.md")
informe("OK" if all(i in analisis for i in IDS) else "FALTA", "analisis.md menciona las 10 preguntas")
informe("OK" if leer("README.md") and "COMPLETAR" not in leer("README.md") else "FALTA", "README.md sin marcas COMPLETAR")
if es_repo:
    n = len((git("log", "--format=%h") or "").splitlines())
    informe("OK" if n >= 6 else "AVISO", "%d commits en el historial (se esperan varios)" % n)

print()
print("Resultado: %d OK, %d FALTA, %d AVISO" % (resultados.count("OK"), resultados.count("FALTA"), resultados.count("AVISO")))
sys.exit(1 if "FALTA" in resultados else 0)
