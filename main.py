# main.py  — Bassam Math v7.1 (Flask)
# شرح عربي + دعم x^2 و 3x + تفاضل/تكامل/حل معادلات وحسابات
# مهيّأ لـ Render (HTTP على port 10000) ويُفضَّل تشغيله بـ gunicorn

from __future__ import annotations
from flask import Flask, request, jsonify, send_from_directory
from sympy import (
    symbols, Eq, sin, cos, tan, asin, acos, atan,
    sqrt, pi, sympify, simplify, diff, integrate, solve, SympifyError
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application
)
import re, os

app = Flask(__name__, static_folder="static", template_folder="templates")

# ===== إعدادات عامّة =====
x, y, z = symbols("x y z")  # المتغيّرات الافتراضية
DEFAULT_VAR = x

# تحويلات آمنة للقراءة (x^2 -> x**2) + ضرب ضمني (3x -> 3*x)
TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

# كلمات مفتاحية عربية/إنجليزية لاكتشاف النيّة
KW_DERIV = ["تفاضل", "مشتق", "اشتق", "derivative", "differentiate", "d/dx"]
KW_INTEG = ["تكامل", "integral", "integrate", "∫"]
KW_SOLVE = ["حل", "معادلة", "solve", "="]
KW_CALC  = ["احسب", "حساب", "evaluate", "calc", "حسِب", "Compute"]

# نعتبر الدوال المثلثية بالـ **درجات** افتراضيًا (كما طلبت)
USE_DEGREES_DEFAULT = True

# ========= أدوات مساعدة =========
def to_python_power(s: str) -> str:
    """x^2 -> x**2 ، كما نحاول تنظيف مسافات وأحرف عربية شائعة."""
    s = s.replace("^", "**")
    # أرقام عربية/هندية إلى إنجليزية
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    s = s.translate(trans)
    # فواصل عربية
    s = s.replace("،", ",")
    # ضرب صريح لبعض الأنماط الشائعة: بين رقم ومتغيّر أو قوس
    s = re.sub(r"(\d)([a-zA-Z\(])", r"\1*\2", s)  # 3x -> 3*x ، 2(x+1)->2*(x+1)
    return s

def parse_expression(text: str):
    """
    يحوّل نصًا رياضيًا إلى تعبير SymPy مع:
    - دعم x^2
    - دعم الضرب الضمني 3x → 3*x
    """
    try:
        text = to_python_power(text)
        expr = parse_expr(text, transformations=TRANSFORMS)
        return expr
    except Exception as e:
        raise SympifyError(str(e))

def degreesify(expr):
    """
    إذا كان وضع الدرجات مفعّلًا، نحوّل sin(60) إلخ إلى sin(60*pi/180)
    دون التأثير على sin(x) الرمزية.
    """
    # استبدال عدد داخل الدوال المثلثية فقط
    def _degify(fsym, arg):
        try:
            # لو وسيط عددي بحت
            if arg.free_symbols:
                return fsym(arg)  # اتركه كما هو (رمزي)
            return fsym(arg * pi / 180)
        except Exception:
            return fsym(arg)

    return (expr
            .replace(lambda e: e.func == sin and len(e.args) == 1,
                     lambda e: _degify(sin, e.args[0]))
            .replace(lambda e: e.func == cos and len(e.args) == 1,
                     lambda e: _degify(cos, e.args[0]))
            .replace(lambda e: e.func == tan and len(e.args) == 1,
                     lambda e: _degify(tan, e.args[0])))

def detect_intent(text: str) -> str:
    """يُحاول معرفة المطلوب: derivative / integral / solve / calc"""
    t = text.strip()
    low = t.lower()

    # إن وُجدت علامة = نميل لنمط حل المعادلات
    if "=" in t:
        return "solve"

    # كلمات مفتاحية
    if any(k in t for k in KW_DERIV) or any(k in low for k in ["derivative", "d/dx"]):
        return "derivative"
    if any(k in t for k in KW_INTEG) or "integral" in low:
        return "integral"
    if any(k in t for k in KW_SOLVE):
        return "solve"
    if any(k in t for k in KW_CALC):
        return "calc"

    # افتراضيًا: حساب/تبسيط
    return "calc"

def strip_command_words(t: str) -> str:
    """يحذف كلمات الأوامر مثل (تفاضل، تكامل، حل...) ويعيد الجزء الرياضي فقط."""
    words = KW_DERIV + KW_INTEG + KW_SOLVE + KW_CALC + ["مشتقة", "اشتقاق", "اشتق", "إيجاد", "ايجاد"]
    out = t
    for w in sorted(words, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(w)}\b", " ", out, flags=re.IGNORECASE)
    # إحلال الإشارة =
    out = out.replace("= 0", "=0").strip()
    return out.strip()

def arabic_poly(expr) -> str:
    """عرض ودّي: x**3 -> x^3 ، * -> (مخفي)، مع أرقام عادية؛ لأجل القراءة."""
    s = str(expr)
    s = s.replace("**", "^")
    s = s.replace("*", "·")
    return s

# ========= محلّلات و حلول =========
def solve_calc(expr_text: str, use_degrees=True):
    steps = []
    try:
        expr = parse_expression(expr_text)
        if use_degrees:
            expr = degreesify(expr)
        simp = simplify(expr)
        steps.append("نقوم بتبسيط التعبير خطوة بخطوة.")
        steps.append(f"التعبير بعد التبسيط: {arabic_poly(simp)}")
        # قيمة عددية تقربية إن أمكن (بدقّة معقولة)
        val = None
        try:
            val = float(simp.evalf(15))
            steps.append(f"القيمة النهائية (تقريبًا): {val}")
        except Exception:
            steps.append("التعبير رمزي ولا يقيَّم عدديًا مباشرة.")
        return {"mode": "حساب", "steps": steps, "result": str(simp if val is None else val)}
    except Exception as e:
        return {"error": f"خطأ في القراءة/الحساب: {e}"}

def solve_derivative(expr_text: str, var=DEFAULT_VAR, use_degrees=True):
    steps = []
    try:
        # السماح بصيغ مثل: y = 3x^3 - 5x^2 + ...
        if "=" in expr_text:
            rhs = expr_text.split("=", 1)[1]
        else:
            rhs = expr_text
        expr = parse_expression(rhs)
        if use_degrees:
            expr = degreesify(expr)
        steps.append(f"المطلوب: إيجاد المشتقة بالنسبة إلى {var}.")
        steps.append(f"الدالة: {arabic_poly(expr)}")
        dexpr = diff(expr, var)
        steps.append("نشتق كل حد على حدة ثم نجمع الحدود.")
        steps.append(f"المشتقة المبسّطة: {arabic_poly(simplify(dexpr))}")
        return {"mode": "تفاضل", "steps": steps, "result": str(simplify(dexpr))}
    except Exception as e:
        return {"error": f"خطأ في التفاضل: {e}"}

def solve_integral(expr_text: str, var=DEFAULT_VAR, use_degrees=True):
    steps = []
    try:
        if "=" in expr_text:
            rhs = expr_text.split("=", 1)[1]
        else:
            rhs = expr_text
        expr = parse_expression(rhs)
        if use_degrees:
            expr = degreesify(expr)
        steps.append(f"المطلوب: تكامل للدالة بالنسبة إلى {var}.")
        steps.append(f"الدالة: {arabic_poly(expr)}")
        iexpr = integrate(expr, var)
        steps.append("نستخدم قواعد التكامل حدًا حدًا (قوة/جمع/ثوابت...).")
        steps.append(f"ناتج التكامل (بدون ثابت C): {arabic_poly(simplify(iexpr))}")
        return {"mode": "تكامل", "steps": steps, "result": str(simplify(iexpr))}
    except Exception as e:
        return {"error": f"خطأ في التكامل: {e}"}

def solve_equation(expr_text: str, var=DEFAULT_VAR, use_degrees=True):
    steps = []
    try:
        # ندعم:  "3x^2=7" أو "حل 3x^2-7=0"
        if "=" not in expr_text:
            # لو ما فيه = نعتبره = 0
            expr_text = f"{expr_text}=0"
        left, right = expr_text.split("=", 1)
        L = parse_expression(left)
        R = parse_expression(right)
        if use_degrees:
            L = degreesify(L); R = degreesify(R)
        eq = Eq(L, R)
        steps.append("نقل كل الحدود لطرف واحد للحصول على صورة قياسية.")
        standard = simplify(L - R)
        steps.append(f"الصورة القياسية: {arabic_poly(standard)} = 0")
        steps.append("نحاول الحل بالتحليل/الصيغ/طرق Sympy المباشرة.")
        sols = solve(eq, var, dict=True)
        if not sols:
            return {"mode": "حل معادلة", "steps": steps + ["لم نجد حلولًا صريحة."], "result": "لا حلول صريحة"}
        steps.append(f"عدد الحلول: {len(sols)}")
        res = []
        for i, sdict in enumerate(sols, 1):
            val = sdict.get(var)
            res.append(f"x{i} = {val}")
        steps.append("ملحوظة: قد تكون بعض الحلول مركّبة إن كانت المعاملات تؤدي لذلك.")
        return {"mode": "حل معادلة", "steps": steps, "result": "; ".join(res)}
    except Exception as e:
        return {"error": f"خطأ في حل المعادلة: {e}"}

# ========= واجهة برمجية بسيطة =========
@app.route("/solve", methods=["POST"])
def api_solve():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "") or ""
    prefer = data.get("prefer", "").strip().lower()  # "derivative|integral|solve|calc"
    deg = data.get("degrees", USE_DEGREES_DEFAULT)
    if not isinstance(deg, bool):
        deg = USE_DEGREES_DEFAULT

    if not text.strip():
        return jsonify({"error": "يرجى إدخال مسألة."}), 400

    # اكتشاف النيّة
    intent = prefer if prefer in ["derivative", "integral", "solve", "calc"] else detect_intent(text)
    pure = strip_command_words(text)

    # حل حسب النيّة
    if intent == "derivative":
        out = solve_derivative(pure, DEFAULT_VAR, use_degrees=deg)
    elif intent == "integral":
        out = solve_integral(pure, DEFAULT_VAR, use_degrees=deg)
    elif intent == "solve":
        out = solve_equation(pure, DEFAULT_VAR, use_degrees=deg)
    else:
        out = solve_calc(pure, use_degrees=deg)

    return jsonify(out), (200 if "error" not in out else 400)

# صفحة اختبار بسيطة (اختيارية): إن لديك templates/index.html ستُستخدم
@app.route("/")
def root():
    # إن لم توجد صفحة، أعدّ رسالة نصية بسيطة
    index_path = os.path.join(app.template_folder or "", "index.html")
    if os.path.exists(index_path):
        return send_from_directory(app.template_folder, "index.html")
    return (
        "<h1>Bassam Math v7.1</h1>"
        "<p>POST /solve مع JSON مثل: {\"text\":\"تفاضل 3x^3-5x^2+4x-7\",\"degrees\":true}</p>"
    )

# ===== تشغيل محلي (للاختبار فقط) =====
if __name__ == "__main__":
    # عند التشغيل المحلي:
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
