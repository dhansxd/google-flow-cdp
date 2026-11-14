"""Local focus and hit-test checks around the native Browser Harness input helpers."""
import ast
import functools
import json
import time
from pathlib import Path


def install(namespace):
    native = namespace['fill_input']
    if getattr(native, '_original_chrome_focus_guard', False) is True:
        return
    js, wait = namespace['js'], namespace['wait_for_element']

    @functools.wraps(native)
    def fill_input(selector, text, clear_first=True, timeout=0.0):
        if timeout > 0 and not wait(selector, timeout=timeout):
            raise RuntimeError(f'fill_input: element not found: {selector!r}')
        focused = js(
            f'(()=>{{const e=document.querySelector({json.dumps(selector)});'
            'if(!e || e.disabled || e.readOnly)return false;'
            'e.focus();return document.activeElement===e;})()'
        )
        if focused is not True:
            raise RuntimeError(f'fill_input: element missing, not editable, or not focused: {selector!r}')
        return native(selector, text, clear_first=clear_first, timeout=0.0)

    fill_input._original_chrome_focus_guard = True
    namespace['fill_input'] = fill_input

    def click_element(selector, timeout=10):
        deadline = time.monotonic() + timeout
        while True:
            point = js(f'''(() => {{
              const matches = Array.from(document.querySelectorAll({json.dumps(selector)}))
                .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
              if (matches.length > 1) throw Error('Click selector matches multiple visible elements');
              const element = matches[0];
              if (!element || element.disabled || element.getAttribute('aria-disabled') === 'true') return null;
              element.scrollIntoView({{block: 'nearest', inline: 'nearest'}});
              const rect = element.getBoundingClientRect();
              if (!rect.width || !rect.height) return null;
              const x = rect.x + rect.width / 2, y = rect.y + rect.height / 2;
              if (!element.contains(document.elementFromPoint(x, y))) return null;
              return [x, y];
            }})()''')
            if point is not None:
                return namespace['click_at_xy'](*point)
            if time.monotonic() >= deadline:
                raise RuntimeError(f'click_element: element not ready: {selector!r}')
            time.sleep(.05)

    namespace['click_element'] = click_element


def prepare_code(code):
    """Load local input checks while keeping Python's leading imports legal."""
    if not isinstance(code, str) or not code.strip():
        return code
    try:
        body = ast.parse(code).body
    except SyntaxError:
        return code  # Let the native runner report the original syntax error.
    last = None
    for index, node in enumerate(body):
        if ((index == 0 and isinstance(node, ast.Expr)
             and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
                or (isinstance(node, ast.ImportFrom) and node.module == '__future__')):
            last = node
        else:
            break
    load = f"__import__('runpy').run_path({str(Path(__file__).resolve())!r})['install'](globals())"
    if last is None:
        return load + '\n' + code
    # AST columns are UTF-8 byte offsets. Insert before a trailing semicolon/comment,
    # including when a future import and the first action share one line.
    source = code.encode('utf-8')
    offset = sum(map(len, source.splitlines(keepends=True)[:last.end_lineno - 1])) + last.end_col_offset
    return (source[:offset] + (';' + load).encode('utf-8') + source[offset:]).decode('utf-8')
