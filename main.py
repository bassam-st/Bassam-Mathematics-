import os
from flask import Flask, render_template, request, jsonify
from sympy import symbols, Eq, solve, simplify, diff, integrate, sin, cos, tan, pi
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
import re

app = Flask(__name__, template_folder="templates", static_folder="static")

# متغيرات رمزية افتراضية
x, y, z = symbols("x y z")
SYMS = {"x": x, "y": y, "z": z, "pi": pi}

# تجهيز محول القراءة (يدعم 3x و x^2 …)
TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# --- أدوات تنسيق بسيطة لإرجاع نص مفهوم للواجهة ---
def pretty_ar(expr_str: str) -> str:
    """
    نحاول إرجاع ناتج بشكل x^3 - 5x^2 + … مع إخفاء ضرب العدد بالمتغير.
    الواجهة تقوم أيضاً بعملية تحسين شكلية، لكننا نُعيد شكلاً لطيفاً هنا.
    """
    s = expr_str.replace("**", "^")
    # 3*x -> 3x
    s = re.sub(r"(\b\d+)\s*\*\s*([a-zA-Z])", r"\1\2", s)
    # (-1)*x -> -x ، و 1*x -> x
    s = re.sub(r"(^|[^a-zA-Z0-9_])1\*([a-zA-Z])", r"\1\2", s)
    s = re.sub(r"(^|[^a-zA-Z0-9_])-?1\*([a-zA-Z])", r"\1-\2", s)
    # مسافات أنظف
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_input(txt: str) -> str:
    """تنظيف المدخلات: رموز ضرب/قسمة، أسهم، أرقام عربية…"""
    # أرقام عربية-هندية -> عربية
    ar_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(ar_digits):
        txt = txt.replace(d, str(i))

    # ضرب/قسمة/ناقص
    txt = txt.replace("×", "*").replace("·", "*").replace("•", "*")
    txt = txt.replace("÷", "/")
    txt = txt.replace("−", "-").replace("—", "-")
    # ^ للأس
    txt = txt.replace("^", "**")
    # دوال شائعة مكتوبة عربية
    txt = txt.replace("جا", "sin").replace("جتا", "cos").replace("ظا", "tan")
    txt = txt.replace("π", "pi")
    return txt.strip()

def parse_math(expr_text: str):
    """تحويل نص إلى تعبير SymPy مع دعم 3x و x^2 إلخ."""
    expr_text = normalize_input(expr_text)
    # يسمح بـ 3x و 2(x+1) … الخ
    return parse_expr(expr_text, transformations=TRANSFORMS, local_dict=SYMS)

def detect_mode(text: str, client_mode: str) -> str:
    """تحديد نوع المسألة إذا كان الوضع تلقائي."""
    t = text.strip()
    low = t.lower()
    if client_mode != "auto":
        return client_mode
    # كلمات عربية
    if any(k in t for k in ["تفاضل", "اشتق", "مشتقة", "مشتقه", "d/dx"]):
        return "diff"
    if any(k in t for k in ["تكامل", "integral", "∫"]):
        return "int"
    if "=" in t or "معادلة" in t or "حل" in t:
        return "equation"
    return "calc"

def extract_after_keyword(text: str, keywords) -> str:
    """نأخذ ما بعد الكلمة المفتاحية (مثلاً: تفاضل 3x^2)."""
    for k in keywords:
        if k in text:
            return text.split(k, 1)[1].strip()
    return text

@app.route("/")
def home():
    return render_template("index.html")

@app.post("/solve")
def solve_api():
    """
    يُتوقع استقبال JSON مثل:
    { "text": "...", "mode": "auto|calc|diff|int|equation", "verbose": true, "format": "ar|en" }
    ويُعاد:
    { "result": "...", "steps": ["...", ...] }
    """
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get("text", "")).strip()
        mode = str(data.get("mode", "auto"))
        verbose = bool(data.get("verbose", True))

        if not text:
            return jsonify(error="المدخل فارغ. اكتب مسألة رياضية."), 400

        # تحديد الوضع
        mode = detect_mode(text, mode)

        steps = []
        result_expr = None  # قد يكون تعبيراً أو قائمة حلول

        # --------- تفاضل ---------
        if mode == "diff":
            expr_str = extract_after_keyword(text, ["تفاضل", "اشتق", "مشتقة", "مشتقه", "d/dx"])
            expr = parse_math(expr_str)
            steps.append("سنوجد المشتقة بالنسبة إلى x باستخدام قواعد التفاضل.")
            result_expr = diff(expr, x)
            if verbose:
                steps.append(f"طبقنا القاعدة: d/dx({pretty_ar(str(expr))}) = {pretty_ar(str(result_expr))}")

        # --------- تكامل ---------
        elif mode == "int":
            expr_str = extract_after_keyword(text, ["تكامل", "integral", "∫"])
            expr = parse_math(expr_str)
            steps.append("سنحسب التكامل غير المحدد بالنسبة إلى x.")
            result_expr = integrate(expr, x)
            if verbose:
                steps.append(f"∫ {pretty_ar(str(expr))} dx = {pretty_ar(str(result_expr))} + C (ثابت التكامل)")

        # --------- معادلة ---------
        elif mode == "equation":
            # صيغة: ... = ...
            if "=" not in text:
                # حاول استخراج المعادلة بعد كلمه "حل"
                t = extract_after_keyword(text, ["حل", "معادلة"])
            else:
                t = text
            t_norm = normalize_input(t)
            if "=" not in t_norm:
                return jsonify(error="لم أجد علامة = في المعادلة."), 400

            left, right = t_norm.split("=", 1)
            left_expr = parse_math(left)
            right_expr = parse_math(right)

            steps.append("ننقل الحدود إلى طرف واحد لتصبح المعادلة على صورة f(x)=0.")
            eq_expr = simplify(left_expr - right_expr)
            steps.append(f"f(x) = {pretty_ar(str(eq_expr))} = 0")
            roots = solve(Eq(eq_expr, 0), x)  # قد يُرجع قائمة
            result_expr = roots
            if verbose:
                steps.append("نستخدم طرق التحليل/الحلول الرمزية لإيجاد قيم x التي تجعل f(x)=0.")

        # --------- حساب/تبسيط ---------
        else:
            expr_str = text
            # شيل كلمات عربية لو وُجدت
            for k in ["احسب", "بسط", "حساب", "تبسيط"]:
                expr_str = expr_str.replace(k, "")
            expr = parse_math(expr_str)
            if verbose:
                steps.append("نقوم بتبسيط التعبير الجبري خطوة بخطوة لكتابة صورة أبسط قابلة للحساب.")
            result_expr = simplify(expr)

        # تجهيز النتيجة كنص
        if isinstance(result_expr, list):
            # حلول معادلة
            pretty_solutions = [pretty_ar(str(s)) for s in result_expr]
            result_text = ", ".join(pretty_solutions) if pretty_solutions else "لا توجد حلول حقيقية (أو الحلول مركبة)."
        else:
            result_text = pretty_ar(str(result_expr))

        return jsonify(result=result_text, steps=steps)

    except Exception as e:
        # إظهار رسالة مفهومة للمستخدم
        return jsonify(error=f"حدث خطأ أثناء القراءة/الحل: {str(e)}"), 400


if __name__ == "__main__":
    # للتشغيل محلياً أو على Render بخيار start: python3 main.py
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
