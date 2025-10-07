# main.py — Bassam Mathematics Pro (v2.5, Arabic, Auto + Degrees + Mobile Ready)
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.solver import smart_solve

app = FastAPI(title="Bassam Mathematics Pro — حل تفصيلي ذكي بالعربية")

# ربط الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------
# دوال مساعدة لتنظيف النصوص
# -------------------------------
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"

def _arabic_digits_to_en(s: str) -> str:
    return s.translate(str.maketrans(_AR_DIGITS, _EN_DIGITS))

def _abs_bars_to_Abs(s: str) -> str:
    try:
        return re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    except Exception:
        return s

def _trig_degrees(s: str) -> str:
    def repl(m):
        func = m.group(1)
        num = m.group(2)
        if re.search(r"[a-df-zA-DF-Z_]", num):
            return m.group(0)
        return f"{func}(pi*({num})/180)"
    pattern = r"\b(sin|cos|tan)\s*\(\s*([+\-]?\d+(?:\.\d+)?)\s*\)"
    return re.sub(pattern, repl, s)

def normalize_text(q: str) -> str:
    q = (q or "").strip()
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    q = q.replace("–", "-").replace("—", "-").replace("،", ",")
    q = q.replace("^", "**").replace("π", "pi")
    q = _arabic_digits_to_en(q)
    q = _abs_bars_to_Abs(q)
    q = _trig_degrees(q)
    return q


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
    mode = (data.get("mode", "auto") or "auto").lower()

    q = normalize_text(raw_q)

    # تحديد نوع الحل يدويًا إذا تم اختياره
    if mode in ("derivative", "تفاضل", "mushteq", "deriv"):
        q = "تفاضل " + q
    elif mode in ("integral", "تكامل", "integr"):
        q = "تكامل " + q
    elif mode in ("solve", "معادلة"):
        pass

    out = smart_solve(q)
    if "error" in out:
        return JSONResponse({"ok": False, "error": out["error"]})

    return JSONResponse({
        "ok": True,
        "mode": out.get("type", "auto"),
        "result": out.get("result", ""),
        "steps": out.get("steps", []),
        "raw": q,
    })
