# main.py — Bassam Mathematics Pro (v2.7, Arabic NLU + Verbose Explain)
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.solver import smart_solve  # v2.7 supports verbose flag

app = FastAPI(title="Bassam Mathematics Pro — حل تفصيلي ذكي بالعربية")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_ZW_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"

def _strip_zw(s: str) -> str: return _ZW_RE.sub("", s or "")
def _arabic_digits_to_en(s: str) -> str: return s.translate(str.maketrans(_AR_DIGITS, _EN_DIGITS))

_WORD_MAP = [
    ("القيمة المطلقة", "Abs"), ("قيمة مطلقة", "Abs"),
    ("جذر تربيعي", "sqrt"), ("جذر مربع", "sqrt"), ("جذر", "sqrt"),
    ("يساوي", "="), ("تساوي", "="),
    ("زائد", "+"), ("جمع", "+"),
    ("ناقص", "-"), ("طرح", "-"),
    ("في", "*"), ("ضرب", "*"),
    ("على", "/"), ("قسمة", "/"),
    ("باي", "pi"),
]
_TRIG_FUNCS = r"(sin|cos|tan)"

def _replace_ar_words(s: str) -> str:
    s = " " + s + " "
    for w, t in sorted(_WORD_MAP, key=lambda x: -len(x[0])):
        s = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", f" {t} ", s)
    return s.strip()

def _wrap_trig_without_paren(s: str) -> str:
    return re.sub(rf"\b{_TRIG_FUNCS}\s+([A-Za-z0-9_.+-]+)", r"\1(\2)", s)

def _trig_with_degree_no_paren(s: str) -> str:
    return re.sub(rf"\b{_TRIG_FUNCS}\s+([+\-]?\d+(?:\.\d+)?)\s*(?:درجة|°)", r"\1(\2)", s)

def _abs_bars_to_Abs(s: str) -> str:
    try: return re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    except Exception: return s

def _trig_degrees_in_paren(s: str) -> str:
    def repl(m):
        func, num = m.group(1), m.group(2)
        if re.search(r"[a-df-zA-DF-Z_]", num): return m.group(0)
        return f"{func}(pi*({num})/180)"
    return re.sub(rf"\b{_TRIG_FUNCS}\s*\(\s*([+\-]?\d+(?:\.\d+)?)\s*\)", repl, s)

def normalize_text(q: str) -> str:
    q = _strip_zw(q)
    q = (q or "").strip()
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    q = q.replace("–", "-").replace("—", "-").replace("،", ",").replace("°", " درجة")
    q = q.replace("^", "**").replace("π", "pi")
    q = _arabic_digits_to_en(q)
    q = _replace_ar_words(q)
    q = _trig_with_degree_no_paren(q)
    q = _wrap_trig_without_paren(q)
    q = _abs_bars_to_Abs(q)
    q = _trig_degrees_in_paren(q)
    q = re.sub(r"\s+", " ", q).replace(" (", "(").replace(") ", ")").strip()
    return q

def parse_intent_ar(raw: str):
    s = _strip_zw((raw or "")).lower()
    if re.search(r"(اشتق|مشتق|تفاضل|المشتقة)", s):
        m = re.search(r"(?:اشتق|مشتق|تفاضل|المشتقة)\s*(.*)", s)
        expr = m.group(1).strip() if m and m.group(1) else "x"
        return "derivative", expr
    if re.search(r"(تكامل|اكامل|أوجد التكامل|∫)", s):
        m = re.search(r"(?:تكامل|اكامل|أوجد التكامل|∫)\s*(.*)", s)
        expr = m.group(1).strip() if m and m.group(1) else "x"
        return "integral", expr
    if re.search(r"(حل|أوجد|جد)\s*(?:المعادلة|النظام)?", s) and ("=" in s or ";" in s):
        return "solve", raw
    return "auto", raw

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "بسّام ماث برو — حل تفصيلي بالعربية"}
    )

@app.post("/solve")
async def solve_api(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "صيغة الطلب غير صحيحة"})

    raw_q = data.get("q", "") or ""
    ui_mode = (data.get("mode", "auto") or "auto").lower()
    explain = (data.get("explain", "normal") or "normal").lower()

    # trigger verbose إن كتب المستخدم كلمات دلالية
    verbose_triggers = ("شرح", "بالتفصيل", "#شرح", "شرح موسع", "شرح مُوسّع")
    verbose = explain in ("extended", "verbose") or any(t in raw_q for t in verbose_triggers)

    inferred_mode, inferred_expr = parse_intent_ar(raw_q)
    mode = ui_mode if ui_mode != "auto" else inferred_mode
    expr_raw = raw_q if ui_mode != "auto" else inferred_expr
    expr = normalize_text(expr_raw)

    if mode == "derivative":   query = f"تفاضل {expr}"
    elif mode == "integral":   query = f"تكامل {expr}"
    elif mode == "solve":      query = expr
    else:                      query = expr

    out = smart_solve(query, verbose=verbose)
    if "error" in out:
        return JSONResponse({"ok": False, "error": out["error"]})

    return JSONResponse({
        "ok": True,
        "mode": out.get("type", mode),
        "result": out.get("result", ""),
        "steps": out.get("steps", []),
        "raw": query,
        "verbose": verbose,
    })
