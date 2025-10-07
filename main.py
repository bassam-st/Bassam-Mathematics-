# main.py — Bassam Mathematics Pro (v2.6, Arabic NLU + OCR-tolerant)
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.solver import smart_solve  # كما هو

app = FastAPI(title="Bassam Mathematics Pro — حل تفصيلي ذكي بالعربية")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------
# أدوات مساعدة
# -------------------------------

# إزالة المحارف غير المرئية (اتجاه/تحكم)
_ZW_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")

_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"

def _strip_zw(s: str) -> str:
    return _ZW_RE.sub("", s or "")

def _arabic_digits_to_en(s: str) -> str:
    return s.translate(str.maketrans(_AR_DIGITS, _EN_DIGITS))

# استبدال كلمات عربية بترميز رياضي
_WORD_MAP = [
    ("القيمة المطلقة", "Abs"),
    ("قيمة مطلقة", "Abs"),
    ("جذر تربيعي", "sqrt"),
    ("جذر مربع", "sqrt"),
    ("جذر", "sqrt"),
    ("يساوي", "="), ("تساوي", "="),
    ("زائد", "+"), ("جمع", "+"),
    ("ناقص", "-"), ("طرح", "-"),
    ("في", "*"), ("ضرب", "*"),
    ("على", "/"), ("قسمة", "/"),
    ("باي", "pi"),
]

def _replace_ar_words(s: str) -> str:
    s = " " + s + " "
    for w, t in sorted(_WORD_MAP, key=lambda x: -len(x[0])):
        s = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", f" {t} ", s)
    return s.strip()

# sin 60 درجة → sin(60)  ،  sin(60) → sin(pi*60/180)
_TRIG_FUNCS = r"(sin|cos|tan)"

def _wrap_trig_without_paren(s: str) -> str:
    # sin x → sin(x)
    return re.sub(rf"\b{_TRIG_FUNCS}\s+([A-Za-z0-9_.+-]+)", r"\1(\2)", s)

def _trig_with_degree_no_paren(s: str) -> str:
    # sin 60 درجة → sin(60)
    return re.sub(rf"\b{_TRIG_FUNCS}\s+([+\-]?\d+(?:\.\d+)?)\s*(?:درجة|°)", r"\1(\2)", s)

def _abs_bars_to_Abs(s: str) -> str:
    try:
        return re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    except Exception:
        return s

def _trig_degrees_in_paren(s: str) -> str:
    # sin(60) -> sin(pi*60/180) إذا كان داخل القوس رقم فقط
    def repl(m):
        func, num = m.group(1), m.group(2)
        if re.search(r"[a-df-zA-DF-Z_]", num):
            return m.group(0)  # متغير/رمز، اتركه
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

    # تنظيف فراغات زائدة
    q = re.sub(r"\s+", " ", q)
    q = q.replace(" (", "(").replace(") ", ")")
    return q.strip()

# اكتشاف النيّة من العربية الحرة
def parse_intent_ar(raw: str):
    """
    يعيد (mode, expr)
    mode: 'derivative' | 'integral' | 'solve' | 'auto'
    """
    s = _strip_zw(raw or "").lower()

    # مؤشرات
    if re.search(r"(اشتق|مشتق|تفاضل|المشتقة)", s):
        # جرّب استخراج ما بعد الكلمة
        m = re.search(r"(?:اشتق|مشتق|تفاضل|المشتقة)\s*(.*)", s)
        expr = m.group(1) if m and m.group(1).strip() else "x"
        return "derivative", expr

    if re.search(r"(تكامل|اكامل|أوجد التكامل|∫)", s):
        m = re.search(r"(?:تكامل|اكامل|أوجد التكامل|∫)\s*(.*)", s)
        expr = m.group(1) if m and m.group(1).strip() else "x"
        return "integral", expr

    if re.search(r"(حل|أوجد|جد)\s*(?:المعادلة|النظام)?", s) and ("=" in s or ";" in s):
        # إن كان في مساواة/نظام نُبقي النص كله عادة
        return "solve", raw

    # لا شيء خاص
    return "auto", raw


# -------------------------------
# الواجهات
# -------------------------------
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

    # ذكاء لغوي: استنتاج الوضع من العربية الحرة
    inferred_mode, inferred_expr = parse_intent_ar(raw_q)

    # أولوية اختيار المستخدم من القائمة، وإلا استخدم المستنتج
    mode = ui_mode if ui_mode != "auto" else inferred_mode
    expr_raw = raw_q if ui_mode != "auto" else inferred_expr

    # تنظيف/تطبيع
    expr = normalize_text(expr_raw)

    # بناء مطلب solver كنص (يتعامل معه كما تعوّدنا)
    if mode == "derivative":
        query = f"تفاضل {expr}"
    elif mode == "integral":
        query = f"تكامل {expr}"
    elif mode == "solve":
        query = expr  # وجود = أو ; سيُفهم كحل معادلة/نظام
    else:
        query = expr

    out = smart_solve(query)
    if "error" in out:
        return JSONResponse({"ok": False, "error": out["error"]})

    return JSONResponse({
        "ok": True,
        "mode": out.get("type", mode),
        "result": out.get("result", ""),
        "steps": out.get("steps", []),
        "raw": query,
    })
