# core/solver.py  — Bassam Math Pro "Professor" Edition (v2.6)
# يشرح كل خطوة بالعربية بطريقة تعليمية
from __future__ import annotations

import re
from typing import List, Dict, Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    convert_xor,
    implicit_multiplication_application,
)

# إعداد عام
sp.init_printing(use_unicode=True)

# محوّلات sympy (تسمح بـ 2x, 3sin(x), ^ → **)
TRANSFORMS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

# متغيرات شائعة
x, y, z, t = sp.symbols("x y z t")
pi = sp.pi
symbols_map = {s.name: s for s in [x, y, z, t]}


def _ok(result: Any, steps: List[str], typ: str) -> Dict[str, Any]:
    return {"result": str(result), "steps": steps, "type": typ}


def _err(msg: str) -> Dict[str, Any]:
    return {"error": msg}


def _parse(expr: str):
    """
    يحاول تحويل النص إلى تعبير SymPy.
    """
    # أمان بسيط: منع دوال غير معروفة
    expr = expr.strip()
    if not expr:
        raise ValueError("النص فارغ")

    # أسماء دوال شائعة نسمح بها:
    local_dict = {
        **symbols_map,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "log": sp.log,
        "ln": sp.log,
        "sqrt": sp.sqrt,
        "Abs": sp.Abs,
        "pi": sp.pi,
        "e": sp.E,
    }
    return parse_expr(expr, local_dict=local_dict, transformations=TRANSFORMS, evaluate=False)


def _format(expr) -> str:
    try:
        return sp.sstr(expr)
    except Exception:
        return str(expr)


# ---------- أدوات تعليمية ----------
def _explain_power_rule(term) -> str | None:
    # محاولة اكتشاف a*x^n
    if term.is_Pow and term.base.is_Symbol and term.exp.is_number:
        n = term.exp
        return f"قاعدة القوة: مشتقة x**{_format(n)} هي { _format(n) }*x**({ _format(n) }-1)."
    if term.is_Mul:
        # ابحث عن x**n داخل الضرب
        for f in term.args:
            if f.is_Pow and f.base.is_Symbol and f.exp.is_number:
                n = f.exp
                return ("قاعدة القوة داخل ضرب: "
                        f"إذا كان { _format(f) } ضمن حاصل ضرب، فمشتقته { _format(n) }*x**({ _format(n) }-1) "
                        "ونستعمل قاعدة الضرب إن لزم.")
    return None


def _explain_sum_rule() -> str:
    return "قاعدة مجموع المشتقات: مشتقة (f + g) = f' + g'."


def _explain_product_rule() -> str:
    return "قاعدة الضرب: مشتقة (f*g) = f'*g + f*g'."


def _explain_chain_rule() -> str:
    return "قاعدة السلسلة: مشتقة f(g(x)) = f'(g(x)) * g'(x)."


def _explain_trig_degree() -> str:
    return ("ملاحظة: تم اعتبار الزوايا بالدرجات، "
            "فقد تم تحويل sin(θ°) تلقائيًا إلى sin(pi*θ/180) قبل التقييم.")


# ---------- تقييم حسابي ----------
def _evaluate(expr_str: str) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة التعبير: {e}")

    # محاولة تبسيط تدريجي
    steps.append("نقوم بتبسيط التعبير خطوة بخطوة.")
    simplified = sp.simplify(expr)
    if _format(simplified) != _format(expr):
        steps.append(f"تبسيط: { _format(expr) } ⟶ { _format(simplified) }")

    # تقييم عددي إن أمكن
    try:
        val = sp.N(simplified, 15)
        steps.append(f"القيمة النهائية هي: {val}")
        return _ok(val, steps, "evaluate")
    except Exception:
        return _ok(simplified, steps, "evaluate")


# ---------- تفاضل ----------
def _derivative(expr_str: str) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة الدالة المراد اشتقاقها: {e}")

    # قواعد تفسيرية
    if isinstance(expr, sp.Add):
        steps.append(_explain_sum_rule())

    if isinstance(expr, sp.Mul):
        steps.append(_explain_product_rule())

    # لمحات عن قاعدة القوة
    power_hint = _explain_power_rule(expr)
    if power_hint:
        steps.append(power_hint)

    # تفاضل فعلي
    try:
        dexpr = sp.diff(expr, x)
    except Exception as e:
        return _err(f"تعذّر إجراء التفاضل: {e}")

    steps.append(f"نشتق بالنسبة إلى x: d/dx({ _format(expr) }) = { _format(dexpr) }")

    # تبسيط
    simp = sp.simplify(dexpr)
    if _format(simp) != _format(dexpr):
        steps.append(f"تبسيط المشتقة: { _format(dexpr) } ⟶ { _format(simp) }")

    return _ok(simp, steps, "derivative")


# ---------- تكامل ----------
def _integral(expr_str: str) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة الدالة المراد تكاملها: {e}")

    # تلميحات قواعد
    if isinstance(expr, sp.Add):
        steps.append("خاصية الخطية: ∫(f + g) dx = ∫f dx + ∫g dx.")
    if isinstance(expr, sp.Mul) and any(a.is_Function for a in expr.args):
        steps.append("قد نستخدم التعويض أو تجزئة التكامل حسب البنية.")

    try:
        I = sp.integrate(expr, x)
    except Exception as e:
        return _err(f"تعذّر إجراء التكامل: {e}")

    steps.append(f"نقوم بإيجاد تكامل: ∫({ _format(expr) }) dx = { _format(I) } + C")
    simp = sp.simplify(I)
    if _format(simp) != _format(I):
        steps.append(f"تبسيط ناتج التكامل: { _format(I) } ⟶ { _format(simp) }")
    steps.append("ملاحظة: نضيف ثابت التكامل +C لأن التكامل غير محدد.")
    return _ok(f"{_format(simp)} + C", steps, "integral")


# ---------- حل معادلات/أنظمة ----------
def _solve_equations(expr_str: str) -> Dict[str, Any]:
    """
    يدعم:
      - معادلة واحدة: x^2 - 5x + 6 = 0
      - نظام بمعادلات مفصولة بفاصلة منقوطة ;   مثل:  x + y = 10; 2*x - y = 4
    """
    steps: List[str] = []
    parts = [p.strip() for p in expr_str.split(";") if p.strip()]
    eqs = []

    try:
        if len(parts) == 1:
            if "=" in parts[0]:
                left, right = parts[0].split("=", 1)
                eqs.append(sp.Eq(_parse(left), _parse(right)))
            else:
                # اعتبره = 0
                eqs.append(sp.Eq(_parse(parts[0]), sp.Integer(0)))
        else:
            for p in parts:
                if "=" in p:
                    L, R = p.split("=", 1)
                    eqs.append(sp.Eq(_parse(L), _parse(R)))
                else:
                    eqs.append(sp.Eq(_parse(p), 0))
    except Exception as e:
        return _err(f"تعذّر تفسير المعادلات: {e}")

    steps.append("نقل كل الحدود إلى طرف واحد لجعلها مساوية للصفر حيث يلزم.")
    for i, eq in enumerate(eqs, 1):
        steps.append(f"المعادلة {i}: { _format(eq.lhs) } = { _format(eq.rhs) }")

    # تحديد المتغيرات تلقائياً من الرموز المستخدمة
    vars_set = set()
    for eq in eqs:
        vars_set |= set(eq.free_symbols)
    vars_list = sorted(list(vars_set), key=lambda s: s.name) or [x]

    steps.append("نحل النظام بالطرق الجبرية الرمزية (حذف/إحلال/جوس-جوردان حسب البنية).")

    try:
        sol = sp.solve(eqs, *vars_list, dict=True)
    except Exception as e:
        return _err(f"تعذّر الحل الرمزي: {e}")

    if not sol:
        return _err("لم يتم العثور على حلول (قد لا يكون للنظام حل أو غير محدد).")

    # صياغة الحل
    if len(sol) == 1:
        s = sol[0]
        for k, v in s.items():
            steps.append(f"نحصل على: {k} = { _format(sp.simplify(v)) }")
        return _ok({str(k): str(sp.simplify(v)) for k, v in s.items()}, steps, "solve")
    else:
        txt = []
        for i, s in enumerate(sol, 1):
            one = ", ".join(f"{k}={_format(sp.simplify(v))}" for k, v in s.items())
            txt.append(f"حل {i}: {one}")
            steps.append(f"حل {i}: {one}")
        return _ok("; ".join(txt), steps, "solve")


# ---------- موجه ذكي يختار المهمة ----------
def smart_solve(query: str) -> Dict[str, Any]:
    """
    يستقبل نصًا (قد يكون عربيًا حرًا بعد تطبيع main.py/js)
    ويحاول تحديد المهمة: تفاضل، تكامل، حل، أو تقييم.
    """
    if not query or not query.strip():
        return _err("المدخل فارغ.")

    q = query.strip()

    # إشعار عن الدرجات إن كان فيها sin/cos/tan رقم
    if re.search(r"\b(sin|cos|tan)\s*\(\s*[+\-]?\d", q):
        # تم تحويل الدرجات سابقًا في الطرف الأمامي، نذكر ذلك كتعليم.
        trig_note = _explain_trig_degree()
    else:
        trig_note = None

    # كشف المهمة بنص عربي بسيط (قد يكون main.py سبق وقررها)
    if q.startswith("تفاضل "):
        expr = q[len("تفاضل "):].strip()
        out = _derivative(expr)
        if trig_note and "steps" in out:
            out["steps"].insert(0, trig_note)
        return out

    if q.startswith("تكامل "):
        expr = q[len("تكامل "):].strip()
        out = _integral(expr)
        if trig_note and "steps" in out:
            out["steps"].insert(0, trig_note)
        return out

    # إذا فيه = أو ; نعتبره حل نظام/معادلة
    if ("=" in q) or (";" in q):
        out = _solve_equations(q)
        if trig_note and "steps" in out:
            out["steps"].insert(0, trig_note)
        return out

    # خلاف ذلك تقييم حسابي
    out = _evaluate(q)
    if trig_note and "steps" in out:
        out["steps"].insert(0, trig_note)
    return out
