# main.py — Bassam Math Pro (v2.5, Arabic, Auto detect, Degrees)
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# العقل (أرسلته لك سابقًا في core/solver.py)
from core.solver import smart_solve

app = FastAPI(title="Bassam Mathematics Pro — Auto Arabic + Degrees")

# مسارات الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# -------------------------
# أدوات مساعدة لتنظيف النص
# -------------------------
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"

def _arabic_digits_to_en(s: str) -> str:
    return s.translate(str.maketrans(_AR_DIGITS, _EN_DIGITS))

def _abs_bars_to_Abs(s: str) -> str:
    # يحوّل |شيء| إلى Abs(شيء)
    try:
        return re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    except Exception:
        return s

def _trig_degrees(s: str) -> str:
    """
    يحوّل sin(60) أو cos(30.5) أو tan(-45) إلى راديان تلقائيًا
    بشرط أن يكون الوسيط عددًا فقط (بدون متغيرات).
    sin(60)  -> sin(pi*60/180)
    """
    def repl(m):
        func = m.group(1)
        num  = m.group(2)
        # تجاهل إذا كان داخلها متغيرات/رموز
        if re.search(r"[a-df-zA-DF-Z_]", num):  # أي حرف غير e (حتى لا نتداخل مع 1e-3)
            return m.group(0)
        return f"{func}(pi*({num})/180)"

    pattern = r"\b(sin|cos|tan)\s*\(\s*([+\-]?\d+(?:\.\d+)?)\s*\)"
    return re.sub(pattern, repl, s)

def normalize_text(q: str) -> str:
    q = (q or "").strip()

    # استبدال الرموز الشائعة
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    q = q.replace("–", "-").replace("—", "-").replace("،", ",")
    q = q.replace("^", "**").replace("π", "pi")

    # أرقام عربية -> إنجليزية
    q = _arabic_digits_to_en(q)

    # مطلق |x| -> Abs(x)
    q = _abs_bars_to_Abs(q)

    # تحويل الدرجات في الدوال المثلثية
    q = _trig_degrees(q)

    return q


# -------------------------
# واجهات التطبيق
# -------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "بسّام ماث برو — حل تفصيلي بالعربية"
        },
    )

@app.post("/solve")
async def solve_api(request: Request):
    """
    يستقبل JSON: {"q": "...", "mode": "auto|derivative|integral|solve|matrix"}
    نحن نستخدم smart_solve الذي يتعرّف تلقائيًا، لكن إن جاء mode
    نمرر كلمة مفتاحية في النص لنجبر الوضع المطلوب.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "صيغة الطلب غير صحيحة"})

    raw_q = data.get("q", "") or ""
    mode  = (data.get("mode", "auto") or "auto").lower()

    # تنظيف وتحضير النص (عربي -> إنجليزي، الرموز، الدرجات…)
    q = normalize_text(raw_q)

    # نجبر الوضع إذا حدّده المستخدم من الواجهة
    # بإضافة كلمة مفتاحية يفهمها smart_solve
    if mode in ("derivative", "تفاضل", "mushteq", "deriv"):
        q = "تفاضل " + q
    elif mode in ("integral", "تكامل", "integr"):
        q = "تكامل " + q
    elif mode in ("solve", "معادلة"):
        # لا شيء خاص هنا، smart_solve سيكتشف وجود =
        pass
    # "matrix" يُعالج عادة في واجهة منفصلة، ويمكنك تمديده لاحقًا

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
