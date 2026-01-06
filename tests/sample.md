# Comprehensive Markdown Test

This file contains all supported markdown features for testing the mdsync converter.

## Text Formatting

This paragraph demonstrates **bold text**, _italic text_, **_bold and italic_**, ~~strikethrough~~, and `inline code`.

You can also combine them: **bold with _italic_ inside** and _italic with **bold** inside_.

## Headings

### Heading Level 3

All three heading levels are supported.

## Links

Here's a [link to GitHub](https://github.com) and another [link to Google](https://google.com).

## Math Equations

### Inline Math

The mass-energy equation is $E=mc^2$, where $E$ is energy, $m$ is mass, and $c$ is the speed of light.

The quadratic formula is $x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}$ for solving $ax^2 + bx + c = 0$.

### Block Math

The Gaussian integral:

$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

Maxwell's equations:

$$
\nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}
$$

$$
\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}
$$

## Lists

### Bulleted Lists

- First item
- Second item
- Third item with **bold** and _italic_
- Fourth item with `code`

### Numbered Lists

1. First step
2. Second step
3. Third step
4. Fourth step

### Nested Lists

- Top level item 1
  - Nested item 1.1
  - Nested item 1.2
    - Deep nested item 1.2.1
    - Deep nested item 1.2.2
  - Nested item 1.3
- Top level item 2
  - Nested item 2.1
  - Nested item 2.2
- Top level item 3

### Nested Numbered Lists

1. First level item 1
   1. Second level item 1.1
   2. Second level item 1.2
      1. Third level item 1.2.1
      2. Third level item 1.2.2
   3. Second level item 1.3
2. First level item 2
   1. Second level item 2.1
   2. Second level item 2.2
3. First level item 3

### Task Lists (Checkboxes)

- [ ] Unchecked task 1
- [x] Checked task 1
- [ ] Unchecked task 2
- [x] Checked task 2
- [ ] Task with **bold** text
- [x] Task with _italic_ text

### Nested Task Lists

- [ ] Parent task 1
  - [ ] Child task 1.1
  - [x] Child task 1.2 (completed)
  - [ ] Child task 1.3
- [x] Parent task 2 (completed)
  - [x] Child task 2.1 (completed)
  - [ ] Child task 2.2
- [ ] Parent task 3
  - [ ] Child task 3.1
    - [ ] Deep child task 3.1.1
    - [x] Deep child task 3.1.2 (completed)

### Mixed Nested Lists

1. Numbered item 1
   - Bullet item 1.1
   - Bullet item 1.2
     1. Nested number 1.2.1
     2. Nested number 1.2.2
2. Numbered item 2
   - [ ] Task item 2.1
   - [x] Task item 2.2 (completed)

## Code Blocks

### Python Code

```python
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test the function
result = fibonacci(10)
print(f"The 10th Fibonacci number is {result}")
```

### JavaScript Code

```javascript
function factorial(n) {
  if (n === 0 || n === 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

console.log(`5! = ${factorial(5)}`);
```

### Plain Text

```
This is a plain text code block
with multiple lines
and no syntax highlighting.
```

## Tables

| Feature         | Status  | Priority | Notes               |
| --------------- | ------- | -------- | ------------------- |
| Text formatting | ✅ Done | High     | Bold, italic, code  |
| Math equations  | ✅ Done | High     | Inline and block    |
| Lists           | ✅ Done | High     | All types supported |
| Tables          | ✅ Done | Medium   | Basic tables        |
| Images          | ❌ TODO | Low      | Not implemented yet |

## Blockquotes

> This is a blockquote.
> It can span multiple lines.
>
> And even have **bold** and _italic_ text.
>
> Single line blockquote with `inline code`.

## Dividers

Content above divider

---

Content below divider

---

More content after second divider

## Complex Example

Here's a complex example combining multiple features:

### Project Tasks

1. **Phase 1: Planning**
   - [x] Define requirements
   - [x] Create design document
   - [ ] Review with team
2. **Phase 2: Development**

   - [ ] Implement core features
     - [x] Text formatting
     - [x] Math support ($E=mc^2$)
     - [x] List handling
     - [ ] Image support
   - [ ] Write tests
   - [ ] Code review

3. **Phase 3: Testing**
   - [ ] Unit tests
   - [ ] Integration tests
   - [ ] Performance benchmarks

### Implementation Formula

The complexity estimation uses: $C = \sum_{i=1}^{n} w_i \cdot t_i$ where $w_i$ is the weight and $t_i$ is the time for task $i$.

---

## End of Test File

This comprehensive test file includes:

- ✅ Headings (H1, H2, H3)
- ✅ Text formatting (bold, italic, strikethrough, code)
- ✅ Links
- ✅ Math equations (inline and block)
- ✅ Lists (bulleted, numbered, nested, task lists)
- ✅ Code blocks (Python, JavaScript, plain text)
- ✅ Tables
- ✅ Blockquotes
- ✅ Dividers
