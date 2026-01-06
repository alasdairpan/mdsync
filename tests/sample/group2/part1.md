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
