import ast
import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("AUTOQUIZ.AST")

class ASTParser:
    """
    Multi-Modal Code & LaTeX AST Parser (UC-6, REQ_02, TC-22 to TC-25).
    Preserves exact indentation, special syntax characters (< > & \\ { }),
    and extracts AST node representations for programming and mathematical equations.
    """

    @staticmethod
    def parse_text_blocks(raw_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parses text and extracts AST code blocks, LaTeX math formulas, and standard text chunks.
        Returns (chunks, warnings).
        """
        chunks = []
        warnings = []
        
        # 1. Check for unclosed code fences (Exception 6.0.E.1 / TC-24)
        fence_count = raw_text.count("```")
        if fence_count % 2 != 0:
            warnings.append("Malformed Syntax Block: Unclosed code fence detected. Falling back to raw text chunking with warning.")
            logger.warning(warnings[-1])
            # Return raw text chunks with warning flag (TC-24)
            return [{
                "chunk_id": "chunk_raw_fallback_0",
                "content": raw_text,
                "type": "raw_text_warning",
                "warning": "Unclosed code fence",
                "has_code": False,
                "has_latex": False,
                "ast_nodes": []
            }], warnings

        # 2. Check for obviously invalid LaTeX math (e.g. unclosed braces or unfinished commands like \frac{1}{)
        latex_invalid_pattern = re.search(r'\\frac\{[^{}]*\}\{[^{}]*$', raw_text) or re.search(r'\\frac\{[^{}]*$', raw_text)
        if latex_invalid_pattern:
            warnings.append("Malformed Syntax Block: Invalid LaTeX expression detected. Falling back to raw text chunking.")
            logger.warning(warnings[-1])
            return [{
                "chunk_id": "chunk_raw_fallback_0",
                "content": raw_text,
                "type": "raw_text_warning",
                "warning": "Invalid LaTeX syntax",
                "has_code": False,
                "has_latex": False,
                "ast_nodes": []
            }], warnings

        # 3. Extract code blocks (preserving indentation and characters < > & \ { } - TC-25)
        code_block_regex = re.compile(r'```([a-zA-Z0-9_\+\#]*)\n([\s\S]*?)```', re.MULTILINE)
        last_idx = 0
        block_idx = 0

        for match in code_block_regex.finditer(raw_text):
            start, end = match.span()
            lang = match.group(1).strip().lower() or "code"
            code_content = match.group(2) # Preserves exact formatting and indentation

            # Preceding text before code block
            preceding_text = raw_text[last_idx:start].strip()
            if preceding_text:
                text_sub_chunks = ASTParser._process_text_and_latex(preceding_text, f"txt_{block_idx}")
                chunks.extend(text_sub_chunks)

            # Analyze AST for Python code
            ast_nodes = []
            if lang in ["python", "py"]:
                try:
                    tree = ast.parse(code_content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            ast_nodes.append(f"FunctionDef:{node.name}")
                        elif isinstance(node, ast.ClassDef):
                            ast_nodes.append(f"ClassDef:{node.name}")
                        elif isinstance(node, ast.For):
                            ast_nodes.append("ForLoop")
                        elif isinstance(node, ast.While):
                            ast_nodes.append("WhileLoop")
                        elif isinstance(node, ast.If):
                            ast_nodes.append("IfStatement")
                except SyntaxError as e:
                    warnings.append(f"Python AST syntax notice on block {block_idx}: {str(e)}")
                    logger.warning(warnings[-1])
            else:
                # C++, Java, or pseudo-code regex heuristic AST nodes
                if "class " in code_content:
                    ast_nodes.append("ClassDeclaration")
                if "void " in code_content or "int " in code_content:
                    ast_nodes.append("MethodDeclaration")

            chunks.append({
                "chunk_id": f"chunk_code_{block_idx}",
                "content": code_content,
                "raw_fence": match.group(0),
                "type": "ast_code",
                "language": lang,
                "ast_nodes": ast_nodes,
                "has_code": True,
                "has_latex": False
            })
            last_idx = end
            block_idx += 1

        # Remaining text
        remaining_text = raw_text[last_idx:].strip()
        if remaining_text:
            text_sub_chunks = ASTParser._process_text_and_latex(remaining_text, f"txt_tail_{block_idx}")
            chunks.extend(text_sub_chunks)

        if not chunks:
            # Fallback for plain text
            chunks.append({
                "chunk_id": "chunk_0",
                "content": raw_text,
                "type": "text",
                "has_code": False,
                "has_latex": False,
                "ast_nodes": []
            })

        return chunks, warnings

    @staticmethod
    def _process_text_and_latex(text: str, prefix: str) -> List[Dict[str, Any]]:
        """Extracts text paragraphs and checks for inline and display LaTeX math equations."""
        result = []
        # LaTeX patterns: $...$, $$...$$, \sum, \int, \frac{}{}
        latex_equations = re.findall(r'(\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\\[[\s\S]*?\\\]|\\\(.*?\\\))', text)
        has_latex = len(latex_equations) > 0 or bool(re.search(r'\\(sum|int|frac|alpha|beta|theta|sigma|partial|infty)', text))

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            para_has_latex = bool(re.search(r'(\$|\\sum|\\int|\\frac)', para))
            result.append({
                "chunk_id": f"chunk_{prefix}_{i}",
                "content": para,
                "type": "ast_latex" if para_has_latex else "text",
                "has_code": False,
                "has_latex": para_has_latex,
                "latex_equations": [eq for eq in latex_equations if eq in para],
                "ast_nodes": ["LaTeX_Formula"] if para_has_latex else []
            })
        return result

