---
apply: always
---

### 🧠 PyCharm AI Chat – Refined Rules and Best Practices

---

### **Guidelines**

**1. Type Safety**
- Use explicit type casting where appropriate.  
- Avoid ambiguous or dynamically typed variables unless necessary.  
- Prefer static typing with modern type hints (`PEP 484`, `PEP 604`).  

**2. Code Style**
- Follow **PEP 8** standards for indentation, spacing, naming, and line length (≤ 79 chars).  
- Maintain consistent code formatting across files (e.g., **Black**, **isort**, **flake8**).  

**3. Naming Conventions**
- Use descriptive and consistent variable, function, and class names.  
- Conventions:  
  - Variables/functions → `lower_case_with_underscores`  
  - Classes → `CapitalizedWords`  
  - Constants → `ALL_CAPS`  

**4. Documentation**
- Provide clear, concise **docstrings** (PEP 257).  
- Document parameters, return values, exceptions, and examples when relevant.  

**5. Error Handling**
- Provide informative, actionable error messages.  
- Avoid `except Exception:` unless necessary.  
- Catch and handle specific exceptions.  

**6. Code Compatibility**
- Maintain **compatibility with existing code** and architecture.  
- Avoid introducing breaking changes without clear justification.  
- Ensure new code integrates seamlessly with existing dependencies and imports.  

**7. Change Severity**
- Only suggest **enhancements or modifications of medium severity or higher**:  
  - *Low severity:* minor formatting, stylistic tweaks → ignore unless requested.  
  - *Medium severity:* improvements in clarity, efficiency, or maintainability.  
  - *High severity:* bug fixes, logic corrections, or security improvements.  

---

### **Chat Best Practices**

**1. Code Presentation**
- Always provide code suggestions in fenced blocks (```python ... ```).  
- Include a brief, clear explanation after each snippet.  

**2. Context Awareness**
- Summarize long discussions periodically to maintain clarity.  
- Reference earlier context or file content when applicable.  

**3. Project Understanding**
- Understand the **project structure and architecture** before making changes.  
- Recognize module relationships, dependencies, and design patterns.  
- Respect existing layering, dependency rules, and organizational conventions.  

**4. Project Consistency**
- Follow all **project-specific conventions** (naming, directory layout, and formatting).  
- Do not override local configuration files such as `.editorconfig`, `pyproject.toml`, or linting rules.  

**5. Uncertainty Handling**
- Ask clarifying questions when context or intent is unclear before proceeding.  

**6. Language and Scope**
- Only provide code suggestions in **supported project languages**.  
- Avoid introducing new languages or frameworks unless explicitly requested.  

---

### **Custom Instructions**

**1. File-Specific Rules**
- Apply targeted rule sets via wildcards:  
  - `*.py` → Apply Python rules and standards.  
  - `test_*.py` → Apply testing and mocking conventions.  

**2. Contextual Enforcement**
- Use markers such as `[PYTHON-STYLE]`, `[TESTING]`, or `[SECURITY]` for scoped rules.  
- Enforce these only when their corresponding marker is detected.  

**3. Final Review Before Acceptance**
- Verify all code suggestions meet the following criteria:  
  - Adheres to **PEP 8** and local project guidelines.  
  - Maintains **logical correctness** and **compatibility**.  
  - Meets **medium or higher severity** improvement standards.  
  - Preserves or improves **test coverage**.  
  - Aligns with **project structure, architecture, and version requirements**.  
