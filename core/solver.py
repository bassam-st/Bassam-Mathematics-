# core/solver.py — Bassam Math Pro (v2.5)
import sympy as sp
import math
import re

x, y = sp.symbols('x y', real=True)

def smart_solve(expr_text: str):
    expr_text = expr_text.replace('^', '**').strip()
    expr = None
    try:
        expr = sp.sympify(expr_text)
    except Exception as e:
        return {"error": f"حدث خطأ أثناء قراءة المعادلة: {e}"}

    # 🔍 تحديد نوع المسألة
    if re.search(r'تفاضل|مشتقة|deriv', expr_text):
        return differentiate(expr)
    elif re.search(r'تكامل|integr', expr_text):
        return integrate(expr)
    elif any(op in expr_text for op in ['=', '==']):
        return solve_equation(expr_text)
    else:
        return basic_analysis(expr)

def differentiate(expr):
    deriv = sp.diff(expr, x)
    steps = [
        "نطبق قاعدة التفاضل: d(xⁿ)/dx = n·xⁿ⁻¹",
        f"نشتق كل حد من المعادلة:",
        f"→ المشتقة هي: {sp.latex(deriv)}"
    ]
    return {
        "type": "تفاضل",
        "steps": steps,
        "result": str(deriv)
    }

def integrate(expr):
    integ = sp.integrate(expr, x)
    steps = [
        "نستخدم قاعدة التكامل: ∫xⁿ dx = xⁿ⁺¹ / (n+1) + C",
        f"→ نتيجة التكامل: {sp.latex(integ)} + C"
    ]
    return {
        "type": "تكامل",
        "steps": steps,
        "result": str(integ) + " + C"
    }

def solve_equation(expr_text):
    left, right = expr_text.split('=')
    left = sp.sympify(left)
    right = sp.sympify(right)
    eq = sp.Eq(left, right)
    sol = sp.solve(eq, x)
    return {
        "type": "معادلة",
        "steps": ["ننقل جميع الحدود إلى طرف واحد", "نحل المعادلة لإيجاد قيمة x"],
        "result": str(sol)
    }

def basic_analysis(expr):
    val = None
    try:
        val = expr.evalf()
        steps = [
            "نقوم بتبسيط التعبير الحسابي خطوة بخطوة.",
            f"القيمة النهائية هي: {val}"
        ]
        return {
            "type": "حساب",
            "steps": steps,
            "result": str(val)
        }
    except:
        return {"error": "تعذر تحليل التعبير، تأكد من كتابته بشكل صحيح."}
