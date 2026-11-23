Primary interactive control for actions across the CRM — forms, toolbars, dialogs.

```jsx
<Button variant="primary" size="md" onClick={() => save()}>Save changes</Button>
<Button variant="accent">Create deal</Button>
<Button variant="secondary" size="sm">Cancel</Button>
```

Variants: `primary` (navy, main actions), `accent` (orange, high-emphasis/CTA), `secondary` (outlined), `ghost` (text-only), `danger` (destructive). Sizes: `sm` `md` `lg`. Set `disabled` to gray out; pass `icon` for a leading icon node.
