# main.py — Bassam Mathematics Pro (TEACHING EDITION)
# خطوات تعليمية مفصّلة: تقييم، معادلات، تفاضل، تكامل، مصفوفات

import re
from typing import Any, Dict, List, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# SymPy
from sympy import (
    symbols, Eq, sympify, simplify, diff, integrate, latex, factor, expand,
    together, apart, Matrix, eye, S, nroots, Poly, discriminant, Symbol,
    fraction, Rational
)
from sympy.functions import sin, cos, tan, exp, log, Abs, sqrt
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application
)

# ------------------------------------------------------------
# إعداد تطبيق الويب
# ------------------------------------------------------------
app = FastAPI(title="Bassam Mathematics Pro — Teaching Edition")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

# ------------------------------------------------------------
# أدوات مساعدة
# ------------------------------------------------------------
def L(obj) -> str:
    try: return latex(obj)
    except Exception: return str(obj)

def step(title: str, content: str) -> Dict[str, str]:
    return {"title": title, "content": content}

def normalize_text(q: str) -> str:
    q = q.replace("÷", "/").replace("×", "*").replace("√", "sqrt")
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    q = q.translate(trans).strip()
    return q

def parse(q: str):
    return parse_expr(q, transformations=TRANSFORMS)

def choose_symbol(expr):
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    return syms[0] if syms else symbols("x")

# ------------------------------------------------------------
# 1) متتبع خطوات للتقييم خطوة بخطوة (PEMDAS)
# ------------------------------------------------------------
def trace_eval(expr) -> Tuple[Any, List[Dict[str, str]]]:
    """
    يعرض كيف نقيّم التعبير وفق ترتيب العمليات:
    - الأقواس
    - القوى
    - الضرب/القسمة
    - الجمع/الطرح
    """
    steps: List[Dict[str, str]] = []

    def _trace(e):
        # ثابت أو رمز
        if e.is_Number or (e.is_Symbol and not e.is_Function):
            return e
        # أقواس داخلية (الأجزاء)
        if e.is_Add:
            parts = list(e.as_ordered_terms())
            computed = [_trace(p) for p in parts]
            before = e
            after = sum(computed)
            steps.append(step("جمع/طرح", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        if e.is_Mul:
            parts = list(e.as_ordered_factors())
            computed = [_trace(p) for p in parts]
            before = e
            after = S.One
            for p in computed: after *= p
            steps.append(step("ضرب/قسمة", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        if e.is_Pow:
            base = _trace(e.base)
            expn = _trace(e.exp)
            before = e
            after = base**expn
            steps.append(step("قوة", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        if e.is_Function:
            args2 = [ _trace(a) for a in e.args ]
            before = e
            after = e.func(*args2)
            steps.append(step("دالة", f"${L(before)} \\Rightarrow {L(after)}$"))
            return after
        # افتراضي: بس رجّع نفسه
        return e

    # 1) توحيد المقامات إن وجِدت
    t = together(expr)
    if t != expr:
        steps.append(step("توحيد المقامات", f"${L(expr)} \\Rightarrow {L(t)}$"))
    e2 = _trace(t)
    # 2) تبسيط نهائي
    simp = simplify(e2)
    if simp != e2:
        steps.append(step("تبسيط", f"${L(e2)} \\Rightarrow {L(simp)}$"))
    # 3) قيمة عددية
    val = simp.evalf()
    p, q = fraction(simp)
    nice = simp if q == 1 else Rational(p, q)
    steps.append(step("قيمة عددية", f"${L(simp)} = {L(val)}$"))
    return (nice, steps)

def do_evaluate(text: str) -> Dict[str, Any]:
    expr = parse(text)
    res, steps = trace_eval(expr)
    return {"mode":"evaluate","ok":True,"result":str(res),"result_latex":L(res),"steps":steps}

# ------------------------------------------------------------
# 2) التفاضل — مع ذكر القواعد المستعملة
# ------------------------------------------------------------
def rule_name(term, x: Symbol) -> str:
    # محاولات مبسطة لاستخراج القاعدة
    if term.is_Pow and term.base==x:
        return "قاعدة القوة: d(x^n)/dx = n x^{n-1}"
    if term.is_Mul and any(t.has(x) for t in term.args):
        return "قاعدة الضرب: (uv)' = u'v + uv'"
    if term.is_Add:
        return "قاعدة الجمع: (u+v)' = u' + v'"
    if term.func in (sin,cos,tan,exp,log,sqrt):
        return f"قاعدة مشتقة {term.func.__name__}"
    return "قواعد عامة + تبسيط"

def do_derivative(text: str) -> Dict[str, Any]:
    expr = parse(text)
    x = choose_symbol(expr)
    steps: List[Dict[str,str]] = []
    steps.append(step("الدالة", f"$f({L(x)})={L(expr)}$"))

    # تفكيك إلى حدود قبل الاشتقاق
    add_terms = list(expr.as_ordered_terms()) if expr.is_Add else [expr]
    for t in add_terms:
        d_t = diff(t, x)
        steps.append(step("اشتقاق حد", f"${L(t)} \\Rightarrow {L(d_t)}$ — {rule_name(t,x)}"))

    d = simplify(diff(expr, x))
    steps.append(step("جمع وتبسيط", f"$f'({L(x)})={L(d)}$"))
    return {"mode":"derivative","ok":True,"result":str(d),"result_latex":L(d),"steps":steps}

# ------------------------------------------------------------
# 3) التكامل — مع خطوات (تجزئة جزئية/قواعد أساسية)
# ------------------------------------------------------------
BASIC_INTS = {
    sin: "\\int \\sin x\\,dx = -\\cos x",
    cos: "\\int \\cos x\\,dx = \\sin x",
    exp: "\\int e^{x}\\,dx = e^{x}",
    log: "\\int \\log x\\,dx = x\\log x - x",
}

def do_integral(text: str) -> Dict[str, Any]:
    expr = parse(text)
    x = choose_symbol(expr)
    steps: List[Dict[str,str]] = []
    steps.append(step("الدالة", f"$f({L(x)})={L(expr)}$"))

    t = together(expr)
    if t != expr:
        steps.append(step("توحيد المقامات", f"${L(expr)} \\Rightarrow {L(t)}$"))
        expr = t

    # لو دالة نسبية: جرّب تجزئة جزئية
    if expr.is_rational_function(x):
        ap = apart(expr, x)
        if ap != expr:
            steps.append(step("تجزئة جزئية", f"${L(expr)} \\Rightarrow {L(ap)}$"))
            expr = ap

    # عرض قواعد أساسية عندما تنطبق
    if expr.is_Add:
        for term in expr.as_ordered_terms():
            steps.append(step("تكامل حد", f"$\\int {L(term)}\\,dx$"))
    else:
        steps.append(step("التكامل", f"$\\int {L(expr)}\\,dx$"))

    F = simplify(integrate(expr, x))
    steps.append(step("النتيجة", f"$\\int {L(expr)}\\,dx = {L(F)} + C$"))
    return {"mode":"integral","ok":True,"result":str(F),"result_latex":L(F)+" + C","steps":steps}

# ------------------------------------------------------------
# 4) المعادلات والأنظمة — خطوات تعليمية
# ------------------------------------------------------------
def parse_equations(text: str):
    parts = [p.strip() for p in text.split(";") if p.strip()]
    eqs = []
    for p in parts or [text]:
        if "=" in p:
            l, r = p.split("=",1)
            eqs.append((parse(l), parse(r)))
        else:
            eqs.append((parse(p), S.Zero))
    return eqs

def symbols_of(eqs):
    syms=set()
    for L,R in eqs: syms |= (L-R).free_symbols
    return sorted(syms, key=lambda s:s.name)

def do_solve(text: str) -> Dict[str,Any]:
    steps=[]
    eqs = parse_equations(text)

    # نظام خطي (أكثر من معادلة)
    if len(eqs) > 1:
        syms = symbols_of(eqs)
        rows=[]; rhs=[]
        for L,R in eqs:
            expr = simplify(L-R)
            row=[expr.expand().coeff(s) for s in syms]
            const=-expr.subs({s:0 for s in syms})
            rows.append(row); rhs.append([const])
        A = Matrix(rows); b = Matrix(rhs)
        steps.append(step("صياغة مصفوفية", f"نكتب النظام على الشكل $A\\,X=b$ حيث $X=[{', '.join(map(str,syms))}]^T$"))
        steps.append(step("A و b", f"$A={L(A)},\\quad b={L(b)}$"))
        Aug = A.row_join(b)
        steps.append(step("المصفوفة المُعزَّزة", f"$[A|b]={L(Aug)}$"))
        R, pivots = Aug.rref()
        steps.append(step("تحويل صفّي (RREF)", f"$[A|b] \\Rightarrow {L(R)}$ (أعمدة محورية: {pivots})"))
        # استخراج حل من RREF
        from sympy import linsolve
        sol = linsolve((A,b))
        steps.append(step("استخراج الحل", f"${L(sol)}$"))
        return {"mode":"solve","ok":True,"result":str(sol),"result_latex":L(sol),"steps":steps}

    # معادلة واحدة
    LHS,RHS = eqs[0]
    steps.append(step("المعادلة", f"${L(LHS)}={L(RHS)}$"))
    expr = simplify(LHS-RHS)
    steps.append(step("نقل الحدود", f"${L(LHS)}-{L(RHS)}=0 \\Rightarrow {L(expr)}=0$"))
    x = choose_symbol(expr)

    try:
        P = Poly(expr, x)
        deg = P.degree()
        steps.append(step("درجة كثير الحدود", f"${deg}$"))

        if deg==1:
            sol = P.solve(x)
            steps.append(step("حل خطي", f"نرتّب ونقسم على معامل {L(x)} \\Rightarrow {L(sol)}"))
        elif deg==2:
            D = discriminant(P)
            steps.append(step("المميز", f"$\\Delta = {L(D)}$"))
            steps.append(step("صيغة تربيعية", "$x=\\frac{-b\\pm\\sqrt{\\Delta}}{2a}$"))
            sol = P.solve(x)
        elif deg in (3,4):
            steps.append(step("حل تحليلي", "نستخدم صيغ التكعيبي/الرباعي مع SymPy"))
            sol = P.solve(x)
        else:
            roots = [c for c in nroots(P)]
            steps.append(step("حل عددي", "للدرجات ≥5 نستخدم nroots"))
            return {"mode":"solve","ok":True,"result":str(roots),"result_latex":L(roots),"steps":steps}

        return {"mode":"solve","ok":True,"result":str(sol),"result_latex":L(sol),"steps":steps}
    except Exception:
        from sympy import solveset
        sol = solveset(expr, x)
        return {"mode":"solve","ok":True,"result":str(sol),"result_latex":L(sol),"steps":steps}

# ------------------------------------------------------------
# 5) المصفوفات — خطوات تعليمية
# ------------------------------------------------------------
def parse_matrix_like(s: str) -> Matrix:
    s = normalize_text(s)
    if s.startswith("Matrix("):
        return parse(s)
    if s.startswith("[[") and s.endswith("]]"):
        return parse(f"Matrix({s})")
    rows = [r.strip() for r in re.split(r";|\n", s) if r.strip()]
    data = []
    for r in rows:
        data.append([parse(c) for c in re.split(r"[,\s]+", r) if c])
    return Matrix(data)

def do_matrix(text: str) -> Dict[str,Any]:
    s = normalize_text(text)
    steps: List[Dict[str,str]] = []

    low = s.lower()
    # det()
    if low.startswith("det("):
        A = parse_matrix_like(s[4:-1])
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        d = A.det()
        steps.append(step("المحدد", f"$\\det(A)={L(d)}$"))
        return {"mode":"matrix","ok":True,"result":str(d),"result_latex":L(d),"steps":steps}

    # inv()
    if low.startswith("inv("):
        A = parse_matrix_like(s[4:-1])
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        if A.rows!=A.cols:
            steps.append(step("تحقق", "لا يوجد معكوس لغير المربعة"))
            return {"mode":"matrix","ok":True,"result":"غير مربعة","result_latex":"","steps":steps}
        Aug = A.row_join(eye(A.rows))
        steps.append(step("تهيئة المعكوس", f"$[A|I]={L(Aug)}$"))
        R, piv = Aug.rref()
        Ainv = R[:, A.rows:]
        steps.append(step("خطوات صفّية مختصرة", f"RREF → أعمدة محورية {piv}"))
        steps.append(step("المعكوس", f"$A^{{-1}}={L(Ainv)}$"))
        return {"mode":"matrix","ok":True,"result":str(Ainv),"result_latex":L(Ainv),"steps":steps}

    # eigen*
    if "eigenvals" in low:
        A = parse_matrix_like(re.sub(r"eigenvals\s*\(|\)$","",s,flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        steps.append(step("المعادلة المميِّزة", "$\\det(A-\\lambda I)=0$"))
        ev = A.eigenvals()
        return {"mode":"matrix","ok":True,"result":str(ev),"result_latex":L(ev),"steps":steps}

    if "eigenvects" in low:
        A = parse_matrix_like(re.sub(r"eigenvects?\s*\(|\)$","",s,flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        steps.append(step("حل (A-λI)v=0", "لكل قيمة ذاتية λ نستخرج فضاءً ذاتيًا"))
        ev = A.eigenvects()
        return {"mode":"matrix","ok":True,"result":str(ev),"result_latex":L(ev),"steps":steps}

    if low.startswith(("diag(","diagonalize(")):
        A = parse_matrix_like(re.sub(r"diag(?:onalize)?\s*\(|\)$","",s,flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        try:
            P, D = A.diagonalize()
            steps.append(step("مصَفوفة التشابه", "$A=PDP^{-1}$"))
            steps.append(step("P", f"$P={L(P)}$"))
            steps.append(step("D", f"$D={L(D)}$"))
            return {"mode":"matrix","ok":True,"result":"diagonalized","result_latex":f"P={L(P)},\\ D={L(D)}","steps":steps}
        except Exception:
            steps.append(step("غير قطري", "A غير قابلة للتقطيع قطريًا"))
            return {"mode":"matrix","ok":True,"result":"not diagonalizable","result_latex":"","steps":steps}

    if low.startswith("jordan("):
        A = parse_matrix_like(re.sub(r"jordan\s*\(|\)$","",s,flags=re.I))
        steps.append(step("المصفوفة", f"$A={L(A)}$"))
        J, P = A.jordan_normal_form()
        steps.append(step("شكل جوردان", f"$J={L(J)}$"))
        return {"mode":"matrix","ok":True,"result":"jordan","result_latex":L(J),"steps":steps}

    # إدخال مصفوفة خام: أعرض معلومات
    A = parse_matrix_like(s)
    steps.append(step("المصفوفة", f"$A={L(A)}$"))
    steps.append(step("الأبعاد", f"${A.shape}$"))
    steps.append(step("RREF مختصر", f"${L(A.rref()[0])}$"))
    return {"mode":"matrix","ok":True,"result":f"Matrix {A.shape}","result_latex":"","steps":steps}

# ------------------------------------------------------------
# كشف الوضع تلقائيًا
# ------------------------------------------------------------
def detect_mode(text: str) -> str:
    t = text.lower().strip()
    if t.startswith("deriv") or t.startswith("مشتق"): return "derivative"
    if t.startswith("integ") or t.startswith("تكامل"): return "integral"
    if any(k in t for k in ["eigen","det(","inv(","rank","[[","matrix(","jordan(","diag("]): return "matrix"
    if ";" in t or "=" in t: return "solve"
    return "evaluate"

# ------------------------------------------------------------
# واجهات API
# ------------------------------------------------------------
@app.post("/solve")
async def solve_api(request: Request):
    data = await request.json()
    q: str = normalize_text(data.get("q",""))
    mode: str = data.get("mode","auto")

    # أوامر عربية قصيرة
    if q.startswith("مشتق "): return do_derivative(q.replace("مشتق ","",1))
    if q.startswith("تكامل "): return do_integral(q.replace("تكامل ","",1))
    if not q: return JSONResponse({"ok": False, "error": "empty_query"})

    try:
        m = detect_mode(q) if mode=="auto" else mode
        if m=="derivative": out = do_derivative(q)
        elif m=="integral": out = do_integral(q)
        elif m=="matrix": out = do_matrix(q)
        elif m=="solve": out = do_solve(q)
        else: out = do_evaluate(q)
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Bassam Math Pro"})
