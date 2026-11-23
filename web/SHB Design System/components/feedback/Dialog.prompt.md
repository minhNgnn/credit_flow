Modal dialog with dark overlay, header + close, optional footer actions.

```jsx
<Dialog open={open} title="Close account" onClose={close} footer={<><Button variant="secondary" onClick={close}>Cancel</Button><Button variant="danger">Confirm</Button></>}>
  This action cannot be undone.
</Dialog>
```
