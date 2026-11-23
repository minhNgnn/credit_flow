Text input field for forms, with label, hint, and error states.

```jsx
<Input label="Email" placeholder="you@bank.com" hint="We'll never share this" />
<Input label="Account number" error="This account was not found" />
```

Variants: `size` (sm/md/lg). Pass `disabled` to gray out. Focus ring uses `--shadow-focus` (navy) or `--shadow-focus-accent` on error.
