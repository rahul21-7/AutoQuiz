import os
from pathlib import Path

def create_samples():
    base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)

    # 1. python_algorithms.md (Matches TC-22: 10-line Python function with nested indentation & LaTeX \frac{a}{b})
    md_content = """# Machine Learning & Algorithmic Optimization

## Section 1: Optimization Functions
Optimization algorithms minimize empirical loss functions across training datasets.
Consider the mathematical loss formulation with LaTeX equation:
$$L(\\theta) = \\frac{1}{N} \\sum_{i=1}^N (y_i - f(x_i; \\theta))^2 + \\lambda \\frac{a}{b}$$
In this formulation, $\\sum$ aggregates observation errors and $\\frac{a}{b}$ weights the L2 regularizer penalty.

## Section 2: Gradient Step Computation
The following Python algorithm demonstrates a ten-line optimization step with preserved nested indentation and AST logic:

```python
def compute_gradient_step(weights, gradients, learning_rate):
    \"\"\"Performs constrained gradient descent update with nested conditionals.\"\"\"
    updated_weights = []
    for w, g in zip(weights, gradients):
        if abs(g) > 1e-5:
            delta = learning_rate * g
            new_val = w - delta
            if new_val < -10.0:
                new_val = -10.0
            updated_weights.append(new_val)
        else:
            updated_weights.append(w)
    return updated_weights
```

## Section 3: Convergence Criteria
Training halts when the relative parameter update $\\Delta < \\epsilon$ or when validation loss exhibits overfitting. Overfitting occurs when training accuracy approaches 100% while validation loss spikes exponentially.
"""
    with open(base / "python_algorithms.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. business_essentials.txt
    txt_content = """Business Essentials and Financial Management

1. Revenue and Cost Structures
Revenue generation represents the gross inflow of economic benefits during operating cycles.
Fixed costs remain unchanged regardless of production volume, including factory leases, core administrative salaries, and equipment depreciation.
Variable costs vary in direct proportion to manufacturing output, encompassing raw materials, direct packaging, and hourly factory labor.

2. Breakeven Analysis and Profit Margins
The breakeven point occurs where total revenue precisely equals total fixed and variable expenses.
Contribution margin ratio indicates the percentage of sales revenue remaining to cover fixed operational overhead.
Working capital represents the operational liquidity available to fulfill immediate debt obligations.
"""
    with open(base / "business_essentials.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)

    # 3. one_sentence.txt (for Exception 2.0.E.1 / TC-32: Insufficient context)
    with open(base / "one_sentence.txt", "w", encoding="utf-8") as f:
        f.write("Machine learning is a subset of artificial intelligence.")

    # 4. Valid PDF generation using raw PDF 1.4 syntax
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 480 >>
stream
BT
/F1 14 Tf
50 720 Td
(Lecture 3: Machine Learning Overfitting and Model Evaluation) Tj
0 -24 Td
/F1 10 Tf
(Overfitting is a fundamental modeling pathology in statistical learning.) Tj
0 -18 Td
(A key sign of overfitting is high training accuracy coupled with low test accuracy.) Tj
0 -18 Td
(Regularization techniques like Dropout and Weight Decay penalize excessive complexity.) Tj
0 -18 Td
(Cross-validation partitions the dataset into k folds to obtain unbiased generalization estimates.) Tj
0 -18 Td
(Retrieval-Augmented Generation RAG combines vector retrieval with large language models.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000756 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
823
%%EOF
"""
    with open(base / "ml_overfitting.pdf", "wb") as f:
        f.write(pdf_content)

    # 5. Empty / scanned PDF with no text layer (for TC-12)
    empty_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 0 >>
stream
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000201 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
253
%%EOF
"""
    with open(base / "scanned_empty.pdf", "wb") as f:
        f.write(empty_pdf)

    print("Sample datasets created successfully!")

if __name__ == "__main__":
    create_samples()

