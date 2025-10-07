# main.py — Bassam Mathematics Pro
import re, math, json, traceback
from typing import List, Dict, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sympy import *
from sympy.parsing.sympy_parser import parse_expr
from sympy.solvers import solve

# تهيئة التطبيق
app = FastAPI(title="Bassam Mathematics Pro — Advanced Solver")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# أوامر شائعة للمستخدمين بالعربية
ARABIC_COMMANDS = {
    "مشتق": "diff",
    "تكامل": "integrate",
    "حل": "solve",
    "محدد": "det",
    "معكوس": "inv",
    "رتبة": "rank",
    "قطري": "diagonalize",
    "جوردان": "jordan",
}

# ==================================================================
# دالة المعالجة الرئيسية
# ==================================================================
@app.post("/solve")
async def solve_math(request: Request):
    try:
        data = await request.json()
        q = data.get("q", "").strip()
        mode = data.get("mode", "auto")

        # استبدال الكلمات العربية بما يقابلها
        for k, v in ARABIC_COMMANDS.items():
            q = q.replace(k, v)

        # تحويل الجذر التربيعي إلى sqrt
        q = q.replace("√", "sqrt")

        # تفاضل/تكامل بالعربية
        if q.startswith("مشتق "):
            expr = q.replace("مشتق ", "").strip()
            x = symbols("x")
            result = diff(sympify(expr), x)
            return JSONResponse({"ok": True, "result": str(result),
                                 "result_latex": latex(result),
                                 "steps": [{"title": "الخطوة", "content": f"مشتقة {expr} بالنسبة إلى x"}]})

        if q.startswith("تكامل "):
            expr = q.replace("تكامل ", "").strip()
            x = symbols("x")
            result = integrate(sympify(expr), x)
            return JSONResponse({"ok": True, "result": str(result),
                                 "result_latex": latex(result),
                                 "steps": [{"title": "الخطوة", "content": f"تكامل {expr} بالنسبة إلى x"}]})

        # أوضاع محددة
        x, y, z, a, b, c = symbols("x y z a b c")

        # ===================== المصفوفات =====================
        if "Matrix" in q or "[[" in q:
            try:
                M = Matrix(eval(q))
                detM = M.det()
                rankM = M.rank()
                invM = None
                steps = [
                    {"title": "المصفوفة", "content": str(M)},
                    {"title": "المحدد |A|", "content": str(detM)},
                    {"title": "الرتبة Rank(A)", "content": str(rankM)},
                ]
                if detM != 0:
                    invM = M.inv()
                    steps.append({"title": "المعكوس A⁻¹", "content": str(invM)})
                if "eigenvals" in q or "eigenvects" in q:
                    eigvals = M.eigenvals()
                    eigvects = M.eigenvects()
                    steps.append({"title": "القيم الذاتية", "content": str(eigvals)})
                    steps.append({"title": "المتجهات الذاتية", "content": str(eigvects)})
                return JSONResponse({"ok": True, "result": str(M),
                                     "result_latex": latex(M),
                                     "steps": steps})
            except Exception as e:
                pass

        # ===================== حل معادلات =====================
        if "=" in q or ";" in q:
            try:
                # الأنظمة تفصل بـ ;
                eqs = [Eq(*map(sympify, e.split("="))) for e in q.split(";") if "=" in e]
                vars_all = list({v for e in eqs for v in e.free_symbols})
                sol = solve(eqs, vars_all, dict=True)
                return JSONResponse({"ok": True, "result": str(sol),
                                     "result_latex": latex(sol),
                                     "steps": [{"title": "حل النظام", "content": str(eqs)}]})
            except Exception as e:
                pass

        # ===================== حل عددي =====================
        if mode == "solve" or ("=" in q):
            try:
                sol = solve(q)
                return JSONResponse({"ok": True, "result": str(sol),
                                     "result_latex": latex(sol),
                                     "steps": [{"title": "حل المعادلة", "content": str(q)}]})
            except Exception:
                pass

        # ===================== التقييم والتبسيط =====================
        expr = sympify(q)
        simplified = simplify(expr)
        result_val = simplified
        steps = [{"title": "التبسيط", "content": str(simplified)}]
        return JSONResponse({"ok": True, "result": str(result_val),
                             "result_latex": latex(result_val),
                             "steps": steps})

    except Exception as e:
        tb = traceback.format_exc()
        return JSONResponse({"ok": False, "error": str(e), "trace": tb})


# ==================================================================
# صفحة الواجهة
# ==================================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Bassam Mathematics Pro"})
