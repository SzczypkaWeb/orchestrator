---
name: frontend-forms
description: Use this skill whenever building or modifying forms in a React frontend repo (frontend-shell, react-app, next-app). Covers form state, validation, and reusable field components.
---

# Frontend Forms Convention

- Form state + validation: `react-hook-form` + `Zod` via `zodResolver`. Never use per-field `useState` or inline regex strings for validation.
- Async submission (loading/error state): TanStack Query's `useMutation`. Never track loading/error manually with `useState`.
- Reusable fields: compose primitives from `shared-ui` (`TextField`, `PasswordField`, `FormError`, `SubmitButton`). Never build raw inputs from scratch.
- Do not build a generic, config-driven "form builder" component — compose primitives directly per form.