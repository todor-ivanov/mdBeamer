# Syntax controls
## Compilation fixture

- Author: mdBeamer
- Date: 2026-09-10

---

# Slide sizing[fontsize=\tiny]
## Theme subtitle

SlideBody

- ListOne
  - ListTwo
    - ListThree

::: fontsize=\small

LocalBody

- LocalList

:::

RestoredBody

| Label | Value |
| :--- | ---: |
| InheritedTable | 42 |

---

# Sized tables[fontsize=\small]

::: table fontsize=\footnotesize width=100% widths="20%,60%,20%"

| Name | Description | Count |
| :--- | :---: | ---: |
| ExplicitTable | A longer description which wraps across multiple lines within the assigned column width. | 42 |

:::

AfterTable

::: fontsize=\tiny

::: table width=80%

| Label | Value |
| :--- | ---: |
| BlockTable | 17 |

:::

:::

---

# Tables inside columns[fontsize=\small]

::: columns

::: column width=55% valign=top

::: table fontsize=\tiny widths="35%,65%"

| Name | Description |
| :--- | :--- |
| ColumnTable | This text wraps within a table in a narrower Beamer column. |

:::

ColumnAfter

:::

::: column width=45% valign=top

::: fontsize=\footnotesize

```Python
print("inherited code size")
```

```Python[fontsize=\tiny]
print("explicit code size")
```

:::

:::

:::

---

# Title-only frame[fontsize=\tiny]

---

# Default sizing

DefaultBody

| Label | Value |
| :--- | ---: |
| DefaultTable | 89 |
