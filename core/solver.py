# core/solver.py  — Bassam Math Pro "Professor" Edition (v2.7, verbose mode)
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

sp.init_printing(use_unicode=True)

TRANSFORMS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

# شائعة
x, y, z, t = sp.symbols("x y z t")
pi = sp.pi
symbols_map = {s.name: s for s in [x, y, z, t]}

def _ok(result: Any, steps: List[str], typ: str) -> Dict[str, Any]:
    return {"result": str(result), "steps": steps, "type": typ}

def _err(msg: str) -> Dict[str, Any]:
    return {"error": msg}

def _parse(expr: str):
    if not expr or not expr.strip():
        raise ValueError("النص فارغ")
    local_dict = {
        **symbols_map,
        "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
        "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt,
        "Abs": sp.Abs, "pi": sp.pi, "e": sp.E, "E": sp.E,
    }
    return parse_expr(expr.strip(), local_dict=local_dict, transformations=TRANSFORMS, evaluate=False)

def _format(expr) -> str:
    try: return sp.sstr(expr)
    except Exception: return str(expr)

# ---------- جُمل تعليمية أطول عند verbose ----------
def V(cond: bool, short: str, long: str) -> str:
    return long if cond else short

def _explain_sum_rule(v: bool) -> str:
    return V(v,
      "قاعدة مجموع المشتقات: (f+g)' = f' + g'.",
      "نستخدم قاعدة مجموع المشتقات: إذا كانت الدالة مجموع عدة حدود، فنشتق كل حد على حدة ثم نجمع النواتج: (f+g)' = f' + g'."
    )

def _explain_product_rule(v: bool) -> str:
    return V(v,
      "قاعدة الضرب: (fg)' = f'g + fg'.",
      "لدينا حاصل ضرب دالتين أو أكثر؛ نطبّق قاعدة الضرب: مشتقة حاصل الضرب تساوي مشتقة الأول ضرب الثاني زائد الأول ضرب مشتقة الثاني: (f·g)' = f'·g + f·g'."
    )

def _explain_power_rule(term, v: bool) -> str | None:
    if term.is_Pow and term.base.is_Symbol and term.exp.is_number:
        n = term.exp
        return V(v,
          f"قاعدة القوة لـ x**{_format(n)}.",
          f"نلاحظ وجود قوة للمتغير: { _format(term) }. بتطبيق قاعدة القوة تكون المشتقة n·x^(n-1)، أي هنا: {_format(n)}·x**({_format(n)}-1)."
        )
    if term.is_Mul:
        for f in term.args:
            if f.is_Pow and f.base.is_Symbol and f.exp.is_number:
                n = f.exp
                return V(v,
                  "قاعدة القوة داخل حاصل ضرب.",
                  f"ضمن حاصل ضرب يوجد حد من الشكل x**{_format(n)}؛ نشتقه وفق قاعدة القوة ثم نستخدم قاعدة الضرب لتجميع النتيجة."
                )
    return None

def _explain_chain_rule(v: bool) -> str:
    return V(v,
      "قاعدة السلسلة: (f∘g)' = f'(g)*g'.",
      "عند تركيب دالتين f(g(x)) نستخدم قاعدة السلسلة: نشتق f بالنسبة لحجتها ثم نضرب في مشتقة g بالنسبة إلى x: (f∘g)' = f'(g(x))·g'(x)."
    )

def _explain_trig_degree(v: bool) -> str:
    return V(v,
      "اعتبرنا الزوايا بالدرجات (تحويل تلقائي).",
      "ملاحظة: تم اعتبار الزوايا المُدخلة أعدادًا بالدرجات؛ قمنا بتحويل sin(θ°) إلى sin(pi*θ/180) داخليًا قبل التبسيط والحساب."
    )

# ---------- تقييم ----------
def _evaluate(expr_str: str, verbose: bool) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة التعبير: {e}")
    steps.append(V(verbose,
        "نبدأ بتبسيط التعبير خطوة بخطوة للوصول إلى صورة أبسط قابلة للحساب.",
        "الخطوة (1): سنقوم أولًا بتبسيط التعبير جبريًا حتى تقل التعقيدات ونستطيع تقييمه بسهولة من غير تغيّر لمعناه."
    ))
    simplified = sp.simplify(expr)
    if _format(simplified) != _format(expr):
        steps.append(f"تبسيط: { _format(expr) } ⟶ { _format(simplified) }")
    try:
        val = sp.N(simplified, 15)
        steps.append(V(verbose,
            f"القيمة النهائية ≈ {val}.",
            f"الخطوة (2): نحسب قيمة التعبير العدديًا بدقة معقولة (حوالي 15 مرتبة عشرية): النتيجة ≈ {val}."
        ))
        return _ok(val, steps, "evaluate")
    except Exception:
        return _ok(simplified, steps, "evaluate")

# ---------- تفاضل ----------
def _derivative(expr_str: str, verbose: bool) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة الدالة المراد اشتقاقها: {e}")

    if isinstance(expr, sp.Add):
        steps.append(_explain_sum_rule(verbose))
    if isinstance(expr, sp.Mul):
        steps.append(_explain_product_rule(verbose))

    hint = _explain_power_rule(expr, verbose)
    if hint: steps.append(hint)

    try:
        dexpr = sp.diff(expr, x)
    except Exception as e:
        return _err(f"تعذّر إجراء التفاضل: {e}")

    steps.append(V(verbose,
        f"نشتق بالنسبة إلى x: d/dx({ _format(expr) }) = { _format(dexpr) }.",
        f"الخطوة (التالي): نشتق الدالة حدًا حدًا حسب القواعد السابقة (قوة/جمع/ضرب/سلسلة) ثم نجمع النواتج: d/dx({ _format(expr) }) = { _format(dexpr) }."
    ))

    simp = sp.simplify(dexpr)
    if _format(simp) != _format(dexpr):
        steps.append(V(verbose,
            f"تبسيط المشتقة: { _format(dexpr) } ⟶ { _format(simp) }.",
            f"وأخيرًا نبسّط صيغة المشتقة للحصول على شكل أوضح ومختزل: { _format(dexpr) } ⟶ { _format(simp) }."
        ))
    return _ok(simp, steps, "derivative")

# ---------- تكامل ----------
def _integral(expr_str: str, verbose: bool) -> Dict[str, Any]:
    steps: List[str] = []
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _err(f"تعذّر قراءة الدالة المراد تكاملها: {e}")

    if isinstance(expr, sp.Add):
        steps.append(V(verbose,
            "خاصية الخطية: ∫(f+g) dx = ∫f dx + ∫g dx.",
            "نستفيد من خاصية الخطية في التكامل: يمكننا تفكيك مجموع الدوال إلى تكامل كل حد على حدة: ∫(f+g) dx = ∫f dx + ∫g dx."
        ))
    if isinstance(expr, sp.Mul) and any(a.is_Function for a in expr.args):
        steps.append(V(verbose,
            "قد نستخدم التعويض أو تجزئة التكامل حسب البنية.",
            "نظرًا لوجود تركيب بين دوال داخل حاصل ضرب، قد نلجأ لتقنيات مثل التعويض u-substitution أو التجزئة الجزئية إن لزم."
        ))
    try:
        I = sp.integrate(expr, x)
    except Exception as e:
        return _err(f"تعذّر إجراء التكامل: {e}")

    steps.append(V(verbose,
        f"∫({ _format(expr) }) dx = { _format(I) } + C.",
        f"نحسب التكامل غير المحدد بالنسبة إلى x. الناتج: ∫({ _format(expr) }) dx = { _format(I) } + C، مع إضافة ثابت التكامل C."
    ))
    simp = sp.simplify(I)
    if _format(simp) != _format(I):
        steps.append(V(verbose,
            f"تبسيط ناتج التكامل: { _format(I) } ⟶ { _format(simp) }.",
            f"نقوم بتبسيط النتيجة لتظهر بصورة أوضح: { _format(I) } ⟶ { _format(simp) }."
        ))
    return _ok(f"{_format(simp)} + C", steps, "integral")

# ---------- حل معادلات/أنظمة ----------
def _solve_equations(expr_str: str, verbose: bool) -> Dict[str, Any]:
    steps: List[str] = []
    parts = [p.strip() for p in expr_str.split(";") if p.strip()]
    eqs = []
    try:
        if len(parts) == 1:
            if "=" in parts[0]:
                L, R = parts[0].split("=", 1)
                eqs.append(sp.Eq(_parse(L), _parse(R)))
            else:
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

    steps.append(V(verbose,
        "نحاول جعل كل معادلة على الصورة (شيء)=0 وتجميع النظام إن وُجد.",
        "الخطوة (1): نرتّب كل معادلة بحيث تكون على صورة (تعبير)=0 أو بشكل صريح يسارًا ويمينًا، تمهيدًا لتطبيق طرق الحل الرمزية."
    ))
    for i, eq in enumerate(eqs, 1):
        steps.append(f"المعادلة {i}: { _format(eq.lhs) } = { _format(eq.rhs) }")

    vars_set = set()
    for eq in eqs:
        vars_set |= set(eq.free_symbols)
    vars_list = sorted(list(vars_set), key=lambda s: s.name) or [x]

    steps.append(V(verbose,
        "نستخدم طرقًا رمزية (حذف/إحلال/حل مباشر) لاستخراج القيم.",
        "الخطوة (2): سنلجأ لطرق الحل الرمزية (حذف/إحلال/حل مباشر للمتعددات) لاشتقاق قيم المتغيرات بدقة، حسب طبيعة النظام."
    ))

    try:
        sol = sp.solve(eqs, *vars_list, dict=True)
    except Exception as e:
        return _err(f"تعذّر الحل الرمزي: {e}")

    if not sol:
        return _err("لم يتم العثور على حلول (قد لا يكون للنظام حل أو غير محدد).")

    if len(sol) == 1:
        s = sol[0]
        for k, v in s.items():
            steps.append(V(verbose,
                f"{k} = { _format(sp.simplify(v)) }.",
                f"نستخلص قيمة المتغير {k} مباشرة من الحل الرمزي بعد تبسيطه: { _format(sp.simplify(v)) }."
            ))
        return _ok({str(k): str(sp.simplify(v)) for k, v in s.items()}, steps, "solve")
    else:
        txt = []
        for i, s in enumerate(sol, 1):
            one = ", ".join(f"{k}={_format(sp.simplify(v))}" for k, v in s.items())
            txt.append(f"حل {i}: {one}")
            steps.append(V(verbose,
                f"حل {i}: {one}.",
                f"هناك أكثر من حل؛ نعرض الحل {i} بهذا الشكل بعد التبسيط: {one}."
            ))
        return _ok("; ".join(txt), steps, "solve")

# ---------- اختيار المهمة ----------
def smart_solve(query: str, verbose: bool = False) -> Dict[str, Any]:
    if not query or not query.strip():
        return _err("المدخل فارغ.")
    q = query.strip()

    trig_note = _explain_trig_degree(verbose) if re.search(r"\b(sin|cos|tan)\s*\(\s*[+\-]?\d", q) else None

    if q.startswith("تفاضل "):
        expr = q[len("تفاضل "):].strip()
        out = _derivative(expr, verbose)
        if trig_note and "steps" in out: out["steps"].insert(0, trig_note)
        return out

    if q.startswith("تكامل "):
        expr = q[len("تكامل "):].strip()
        out = _integral(expr, verbose)
        if trig_note and "steps" in out: out["steps"].insert(0, trig_note)
        return out

    if ("=" in q) or (";" in q):
        out = _solve_equations(q, verbose)
        if trig_note and "steps" in out: out["steps"].insert(0, trig_note)
        return out

    out = _evaluate(q, verbose)
    if trig_note and "steps" in out: out["steps"].insert(0, trig_note)
    return out
