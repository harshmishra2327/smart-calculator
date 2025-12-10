from flask import Flask, render_template, request, jsonify
import ast
import operator as op
import re
from typing import Optional
from math import isfinite
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='static', template_folder='templates')

# supported operators mapping for AST nodes
_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def safe_eval(node):
    """Safely evaluate an AST node that contains only simple math."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Constant):
        # Python 3.8+ uses Constant for numbers
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Unsupported constant")
    if isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type in _operators:
            return _operators[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in _operators:
            return _operators[op_type](operand)
    raise ValueError("Unsupported expression")


def evaluate_expression(expr: str):
    """Parse and evaluate a math expression string safely."""
    # strip unwanted characters, allow digits, operators, parentheses, decimal point, spaces
    cleaned = re.sub(r"[^0-9\.\+\-\*\/\%\(\)\s\^]", "", expr)
    # convert caret ^ to pow
    cleaned = cleaned.replace('^', '**')
    try:
        node = ast.parse(cleaned, mode='eval')
        result = safe_eval(node)
        # validate numeric
        if not isinstance(result, (int, float)):
            raise ValueError('Result is not numeric')
        if not isfinite(result):
            raise ValueError('Non-finite result')
        # limit magnitude to avoid runaway values
        if abs(result) > 1e308:
            raise ValueError('Result magnitude too large')
        return result
    except Exception as e:
        logging.info('Evaluation failed for expr=%s cleaned=%s: %s', expr, cleaned, e)
        raise ValueError('Could not evaluate expression')


def parse_nl(text: str):
    """Try to convert simple natural language to a math expression.
    Examples: "add 5 and 3", "multiply 4 by 7", "subtract 2 from 9" or plain "5 plus 3".
    """
    t = text.lower().strip()

    # basic operator words
    t = t.replace('plus', '+').replace('minus', '-').replace('times', '*')
    t = t.replace('x', '*').replace('multiplied by', '*').replace('multiply by', '*')
    t = t.replace('divide by', '/').replace('divided by', '/')
    t = t.replace('over', '/')
    t = t.replace('^', '**')

    # handle 'square root of N' -> (N)**0.5
    m = re.match(r".*square root of\s+([\w\s-]+).*", t)
    if m:
        inner = words_to_number_string(m.group(1))
        return f"({inner})**0.5"

    # handle 'A percent of B' -> (A/100)*B
    m = re.match(r".*([\w\s-]+) percent of ([\w\s-]+).*", t)
    if m:
        a = words_to_number_string(m.group(1))
        b = words_to_number_string(m.group(2))
        return f"({a}/100)*({b})"

    # patterns: add A and B / subtract A from B / multiply A by B / divide A by B
    m = re.match(r".*add\s+([\w\s-]+)\s+(and|,)\s*([\w\s-]+).*", t)
    if m:
        return f"{words_to_number_string(m.group(1))} + {words_to_number_string(m.group(3))}"
    m = re.match(r".*subtract\s+([\w\s-]+)\s+from\s+([\w\s-]+).*", t)
    if m:
        return f"{words_to_number_string(m.group(2))} - {words_to_number_string(m.group(1))}"
    m = re.match(r".*multiply\s+([\w\s-]+)\s+(and|by)\s*([\w\s-]+).*", t)
    if m:
        return f"{words_to_number_string(m.group(1))} * {words_to_number_string(m.group(3))}"
    m = re.match(r".*divide\s+([\w\s-]+)\s+by\s+([\w\s-]+).*", t)
    if m:
        return f"{words_to_number_string(m.group(1))} / {words_to_number_string(m.group(2))}"

    # fallback: try converting number words in the whole phrase
    candidate = words_to_number_string(t)
    # replace word-operators again just in case
    candidate = candidate.replace('plus', '+').replace('minus', '-')
    candidate = candidate.replace('times', '*').replace('x', '*')
    candidate = candidate.replace('over', '/')
    return candidate


def words_to_number_string(s: str) -> str:
    """Convert simple English number words inside a string to numeric representation.
    Supports common numbers up to thousands (e.g., 'one hundred twenty three').
    Non-number words are left as-is so we still return a usable expression string.
    """
    s = s.lower()
    # replace hyphens
    s = s.replace('-', ' ')
    tokens = s.split()

    # maps
    small = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19
    }
    tens = {'twenty':20, 'thirty':30, 'forty':40, 'fifty':50, 'sixty':60, 'seventy':70, 'eighty':80, 'ninety':90}
    mults = {'hundred':100, 'thousand':1000}

    out_tokens = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in small or tok in tens:
            # accumulate a number phrase
            num = 0
            # handle teen/small
            if tok in small:
                num += small[tok]
                i += 1
            elif tok in tens:
                num += tens[tok]
                i += 1
                # check next small
                if i < len(tokens) and tokens[i] in small:
                    num += small[tokens[i]]
                    i += 1

            # check multipliers like 'hundred' or 'thousand'
            while i < len(tokens) and tokens[i] in mults:
                num *= mults[tokens[i]]
                i += 1

            out_tokens.append(str(num))
            continue
        # numeric token already
        if re.fullmatch(r'[0-9\.]+', tok):
            out_tokens.append(tok)
            i += 1
            continue
        # non-number token: keep as-is
        out_tokens.append(tok)
        i += 1

    return ' '.join(out_tokens)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json() or {}
    expr = data.get('expression', '')
    if not expr:
        return jsonify({'ok': False, 'error': 'No expression provided'}), 400

    # try to interpret natural language first
    nl_conv = parse_nl(expr)
    # limit input length
    if len(expr) > 300:
        return jsonify({'ok': False, 'error': 'Expression too long'}), 400

    # attempt evaluation and provide clearer errors
    last_err: Optional[str] = None
    for candidate in (nl_conv, expr):
        try:
            result = evaluate_expression(candidate)
            return jsonify({'ok': True, 'result': result, 'expression': candidate, 'input': expr})
        except ValueError as e:
            last_err = str(e)
        except Exception as e:
            logging.exception('Unexpected error evaluating expression')
            last_err = 'Internal error'

    return jsonify({'ok': False, 'error': 'Could not evaluate expression', 'detail': last_err, 'input': expr}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
