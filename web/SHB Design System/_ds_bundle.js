/* @ds-bundle: {"format":4,"namespace":"SHBDesignSystem_1dd17a","components":[{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"}],"sourceHashes":{"components/core/Button.jsx":"55422436cf35","components/core/Card.jsx":"cc0d22f385d2","components/core/IconButton.jsx":"e34a4a606cae","components/feedback/Badge.jsx":"ef3c5b478456","components/feedback/Dialog.jsx":"cdd1b6f25f83","components/feedback/Toast.jsx":"281063c0b4b8","components/feedback/Tooltip.jsx":"3bad67e1a8da","components/forms/Checkbox.jsx":"7fe0bd6461fb","components/forms/Input.jsx":"48dba45c0946","components/forms/Radio.jsx":"5f13e246b538","components/forms/Select.jsx":"fa4ea591ffc2","components/forms/Switch.jsx":"ae01eef7f1b9","components/navigation/Tabs.jsx":"b5333a5af19a","ui_kits/crm/CustomerProfileScreen.jsx":"19e3854d7203","ui_kits/crm/DashboardScreen.jsx":"0bddf793b732","ui_kits/crm/DealsScreen.jsx":"8944dc63fa5a","ui_kits/crm/LoginScreen.jsx":"f2d48fe20bce","ui_kits/crm/Sidebar.jsx":"28fd39062e36","ui_kits/crm/TopBar.jsx":"1873671aa22e","ui_kits/crm/data.js":"8ee0f2d7a855"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.SHBDesignSystem_1dd17a = window.SHBDesignSystem_1dd17a || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Button.jsx
try { (() => {
const sizeStyles = {
  sm: {
    padding: '6px 12px',
    fontSize: 'var(--text-sm)',
    height: '32px'
  },
  md: {
    padding: '9px 16px',
    fontSize: 'var(--text-base)',
    height: '40px'
  },
  lg: {
    padding: '12px 20px',
    fontSize: 'var(--text-lg)',
    height: '48px'
  }
};
const variantStyles = {
  primary: {
    background: 'var(--brand-primary)',
    color: 'var(--text-on-brand)',
    border: '1px solid var(--brand-primary)'
  },
  accent: {
    background: 'var(--brand-accent)',
    color: 'var(--text-on-accent)',
    border: '1px solid var(--brand-accent)'
  },
  secondary: {
    background: 'var(--surface-card)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-default)'
  },
  ghost: {
    background: 'transparent',
    color: 'var(--brand-primary)',
    border: '1px solid transparent'
  },
  danger: {
    background: 'var(--color-danger-600)',
    color: '#fff',
    border: '1px solid var(--color-danger-600)'
  }
};
const hoverBg = {
  primary: 'var(--brand-primary-hover)',
  accent: 'var(--brand-accent-hover)',
  secondary: 'var(--surface-sunken)',
  ghost: 'var(--surface-sunken)',
  danger: 'var(--color-danger-700)'
};
function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  icon = null,
  onClick,
  type = 'button'
}) {
  const [hover, setHover] = React.useState(false);
  const [active, setActive] = React.useState(false);
  const v = variantStyles[variant] || variantStyles.primary;
  const s = sizeStyles[size] || sizeStyles.md;
  const style = {
    fontFamily: 'var(--font-body)',
    fontWeight: 600,
    borderRadius: 'var(--radius-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'background var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard), opacity var(--duration-fast)',
    opacity: disabled ? 0.45 : 1,
    ...s,
    ...v,
    background: disabled ? v.background : hover ? hoverBg[variant] : v.background,
    transform: active && !disabled ? 'scale(0.98)' : 'scale(1)'
  };
  return /*#__PURE__*/React.createElement("button", {
    type: type,
    disabled: disabled,
    style: style,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setActive(false);
    },
    onMouseDown: () => setActive(true),
    onMouseUp: () => setActive(false)
  }, icon, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function Card({
  children,
  padding = 'var(--space-6)',
  style = {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface-card)',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-sm)',
      border: '1px solid var(--border-subtle)',
      padding,
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function IconButton({
  icon,
  label,
  size = 'md',
  variant = 'ghost',
  onClick,
  disabled = false
}) {
  const [hover, setHover] = React.useState(false);
  const dims = {
    sm: 28,
    md: 36,
    lg: 44
  }[size];
  const variants = {
    ghost: {
      bg: 'transparent',
      hoverBg: 'var(--surface-sunken)',
      color: 'var(--text-secondary)'
    },
    solid: {
      bg: 'var(--brand-primary)',
      hoverBg: 'var(--brand-primary-hover)',
      color: '#fff'
    },
    outline: {
      bg: 'transparent',
      hoverBg: 'var(--surface-sunken)',
      color: 'var(--brand-primary)'
    }
  };
  const v = variants[variant] || variants.ghost;
  return /*#__PURE__*/React.createElement("button", {
    "aria-label": label,
    title: label,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: dims,
      height: dims,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: 'var(--radius-sm)',
      border: variant === 'outline' ? '1px solid var(--border-default)' : 'none',
      background: hover ? v.hoverBg : v.bg,
      color: v.color,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      transition: 'background var(--duration-fast) var(--ease-standard)'
    }
  }, icon);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Badge.jsx
try { (() => {
const toneStyles = {
  neutral: {
    bg: 'var(--surface-sunken)',
    fg: 'var(--text-secondary)'
  },
  success: {
    bg: 'var(--status-success-bg)',
    fg: 'var(--status-success-fg)'
  },
  warning: {
    bg: 'var(--status-warning-bg)',
    fg: 'var(--status-warning-fg)'
  },
  danger: {
    bg: 'var(--status-danger-bg)',
    fg: 'var(--status-danger-fg)'
  },
  info: {
    bg: 'var(--status-info-bg)',
    fg: 'var(--status-info-fg)'
  },
  accent: {
    bg: 'var(--color-orange-100)',
    fg: 'var(--color-orange-800)'
  }
};
function Badge({
  children,
  tone = 'neutral'
}) {
  const t = toneStyles[tone] || toneStyles.neutral;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      padding: '3px 10px',
      borderRadius: 'var(--radius-full)',
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      fontFamily: 'var(--font-body)',
      background: t.bg,
      color: t.fg,
      lineHeight: 1.4
    }
  }, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
function Dialog({
  open,
  title,
  children,
  onClose,
  footer
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'fixed',
      inset: 0,
      background: 'var(--surface-overlay)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100
    },
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      background: 'var(--surface-card)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-lg)',
      width: 420,
      maxWidth: '90vw',
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px 24px',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 'var(--text-xl)'
    }
  }, title), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: 'none',
      fontSize: 20,
      cursor: 'pointer',
      color: 'var(--text-tertiary)'
    }
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 24,
      color: 'var(--text-primary)',
      fontSize: 'var(--text-base)'
    }
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 24px',
      borderTop: '1px solid var(--border-subtle)',
      display: 'flex',
      justifyContent: 'flex-end',
      gap: 10
    }
  }, footer)));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
const toneStyles = {
  neutral: {
    bg: 'var(--surface-inverse)',
    fg: '#fff'
  },
  success: {
    bg: 'var(--status-success-bg)',
    fg: 'var(--status-success-fg)'
  },
  warning: {
    bg: 'var(--status-warning-bg)',
    fg: 'var(--status-warning-fg)'
  },
  danger: {
    bg: 'var(--status-danger-bg)',
    fg: 'var(--status-danger-fg)'
  }
};
function Toast({
  children,
  tone = 'neutral',
  onDismiss
}) {
  const t = toneStyles[tone] || toneStyles.neutral;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      background: t.bg,
      color: t.fg,
      padding: '12px 16px',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-lg)',
      fontFamily: 'var(--font-body)',
      fontSize: 'var(--text-sm)',
      fontWeight: 500,
      minWidth: 260
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1
    }
  }, children), onDismiss && /*#__PURE__*/React.createElement("button", {
    onClick: onDismiss,
    style: {
      background: 'none',
      border: 'none',
      color: 'inherit',
      cursor: 'pointer',
      opacity: 0.7,
      fontSize: 16
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function Tooltip({
  children,
  label,
  side = 'top'
}) {
  const [show, setShow] = React.useState(false);
  const pos = {
    top: {
      bottom: '100%',
      left: '50%',
      transform: 'translateX(-50%)',
      marginBottom: 6
    },
    bottom: {
      top: '100%',
      left: '50%',
      transform: 'translateX(-50%)',
      marginTop: 6
    }
  }[side] || {};
  return /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      display: 'inline-flex'
    },
    onMouseEnter: () => setShow(true),
    onMouseLeave: () => setShow(false)
  }, children, show && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      ...pos,
      background: 'var(--surface-inverse)',
      color: '#fff',
      fontSize: 'var(--text-xs)',
      fontFamily: 'var(--font-body)',
      padding: '5px 10px',
      borderRadius: 'var(--radius-xs)',
      whiteSpace: 'nowrap',
      boxShadow: 'var(--shadow-sm)',
      zIndex: 10
    }
  }, label));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function Checkbox({
  label,
  checked,
  onChange,
  disabled = false
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => !disabled && onChange && onChange(!checked),
    style: {
      width: 18,
      height: 18,
      borderRadius: 'var(--radius-xs)',
      border: `1.5px solid ${checked ? 'var(--brand-primary)' : 'var(--border-strong)'}`,
      background: checked ? 'var(--brand-primary)' : 'var(--surface-card)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'background var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)',
      flexShrink: 0
    }
  }, checked && /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "12",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "white",
    strokeWidth: "3",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("polyline", {
    points: "20 6 9 17 4 12"
  }))), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-base)',
      color: 'var(--text-primary)'
    }
  }, label));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function Input({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
  disabled = false,
  error,
  hint,
  size = 'md'
}) {
  const [focused, setFocused] = React.useState(false);
  const heights = {
    sm: 32,
    md: 40,
    lg: 48
  };
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      fontFamily: 'var(--font-body)',
      width: '100%'
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-sm)',
      fontWeight: 600,
      color: 'var(--text-primary)'
    }
  }, label), /*#__PURE__*/React.createElement("input", {
    type: type,
    value: value,
    placeholder: placeholder,
    disabled: disabled,
    onChange: onChange,
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false),
    style: {
      height: heights[size],
      padding: '0 12px',
      borderRadius: 'var(--radius-sm)',
      border: `1px solid ${error ? 'var(--color-danger-600)' : focused ? 'var(--border-focus)' : 'var(--border-default)'}`,
      boxShadow: focused ? error ? 'var(--shadow-focus-accent)' : 'var(--shadow-focus)' : 'none',
      fontSize: 'var(--text-base)',
      fontFamily: 'var(--font-body)',
      color: 'var(--text-primary)',
      background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
      outline: 'none',
      transition: 'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)'
    }
  }), error ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-xs)',
      color: 'var(--color-danger-700)'
    }
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-xs)',
      color: 'var(--text-tertiary)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function Radio({
  label,
  checked,
  onChange,
  disabled = false,
  name
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => !disabled && onChange && onChange(),
    style: {
      width: 18,
      height: 18,
      borderRadius: '50%',
      border: `1.5px solid ${checked ? 'var(--brand-primary)' : 'var(--border-strong)'}`,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0
    }
  }, checked && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: '50%',
      background: 'var(--brand-primary)'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-base)',
      color: 'var(--text-primary)'
    }
  }, label));
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function Select({
  label,
  value,
  onChange,
  options = [],
  disabled = false,
  hint
}) {
  const [focused, setFocused] = React.useState(false);
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      fontFamily: 'var(--font-body)',
      width: '100%'
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-sm)',
      fontWeight: 600,
      color: 'var(--text-primary)'
    }
  }, label), /*#__PURE__*/React.createElement("select", {
    value: value,
    onChange: onChange,
    disabled: disabled,
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false),
    style: {
      height: 40,
      padding: '0 12px',
      borderRadius: 'var(--radius-sm)',
      border: `1px solid ${focused ? 'var(--border-focus)' : 'var(--border-default)'}`,
      boxShadow: focused ? 'var(--shadow-focus)' : 'none',
      fontSize: 'var(--text-base)',
      fontFamily: 'var(--font-body)',
      color: 'var(--text-primary)',
      background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
      outline: 'none'
    }
  }, options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label))), hint && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-xs)',
      color: 'var(--text-tertiary)'
    }
  }, hint));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function Switch({
  checked,
  onChange,
  disabled = false,
  label
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => !disabled && onChange && onChange(!checked),
    style: {
      width: 40,
      height: 22,
      borderRadius: 'var(--radius-full)',
      background: checked ? 'var(--brand-primary)' : 'var(--color-gray-300)',
      position: 'relative',
      transition: 'background var(--duration-fast) var(--ease-standard)',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 2,
      left: checked ? 20 : 2,
      width: 18,
      height: 18,
      borderRadius: '50%',
      background: '#fff',
      boxShadow: 'var(--shadow-xs)',
      transition: 'left var(--duration-fast) var(--ease-standard)'
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-base)',
      color: 'var(--text-primary)'
    }
  }, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function Tabs({
  tabs = [],
  value,
  onChange
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 4,
      borderBottom: '1px solid var(--border-subtle)',
      fontFamily: 'var(--font-body)'
    }
  }, tabs.map(t => {
    const active = t.value === value;
    return /*#__PURE__*/React.createElement("button", {
      key: t.value,
      onClick: () => onChange && onChange(t.value),
      style: {
        padding: '10px 16px',
        background: 'transparent',
        border: 'none',
        borderBottom: `2px solid ${active ? 'var(--brand-accent)' : 'transparent'}`,
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        fontWeight: active ? 600 : 500,
        fontSize: 'var(--text-sm)',
        cursor: 'pointer',
        transition: 'color var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)'
      }
    }, t.label);
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/CustomerProfileScreen.jsx
try { (() => {
function CustomerProfileScreen({
  customer,
  onBack
}) {
  const {
    Card,
    Badge,
    Tabs,
    Button
  } = window.SHBDesignSystem_1dd17a;
  const {
    deals,
    formatCurrency
  } = window.CRMData;
  const [tab, setTab] = React.useState('overview');
  const customerDeals = deals.filter(d => d.name.startsWith(customer.name.split(' ')[0]));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 28,
      fontFamily: 'var(--font-body)',
      display: 'flex',
      flexDirection: 'column',
      gap: 18
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    style: {
      background: 'none',
      border: 'none',
      color: 'var(--text-link)',
      cursor: 'pointer',
      fontSize: 'var(--text-sm)',
      padding: 0,
      marginBottom: 12
    }
  }, "\u2190 Back to dashboard"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontSize: 'var(--text-3xl)',
      fontWeight: 700
    }
  }, customer.name), /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'var(--text-secondary)',
      fontSize: 'var(--text-sm)',
      marginTop: 4
    }
  }, customer.segment, " \xB7 RM ", customer.rm, " \xB7 Last contact ", customer.lastContact)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary"
  }, "Log activity"), /*#__PURE__*/React.createElement(Button, {
    variant: "primary"
  }, "Send statement")))), /*#__PURE__*/React.createElement(Tabs, {
    tabs: [{
      value: 'overview',
      label: 'Overview'
    }, {
      value: 'deals',
      label: 'Deals'
    }, {
      value: 'documents',
      label: 'Documents'
    }],
    value: tab,
    onChange: setTab
  }), tab === 'overview' && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3,1fr)',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Total balance"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-2xl)',
      fontWeight: 700,
      marginTop: 6
    }
  }, formatCurrency(customer.balance))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Status"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8
    }
  }, /*#__PURE__*/React.createElement(Badge, {
    tone: customer.status === 'Active' ? 'success' : customer.status === 'At risk' ? 'danger' : 'warning'
  }, customer.status))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Relationship manager"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-base)',
      fontWeight: 600,
      marginTop: 6
    }
  }, customer.rm))), tab === 'deals' && /*#__PURE__*/React.createElement(Card, {
    padding: "0"
  }, customerDeals.length === 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 20,
      color: 'var(--text-tertiary)',
      fontSize: 'var(--text-sm)'
    }
  }, "No deals yet for this customer."), customerDeals.map(d => /*#__PURE__*/React.createElement("div", {
    key: d.id,
    style: {
      padding: '14px 20px',
      borderTop: '1px solid var(--border-subtle)',
      display: 'flex',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-sm)'
    }
  }, d.name), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-sm)'
    }
  }, formatCurrency(d.value))))), tab === 'documents' && /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'var(--text-tertiary)',
      fontSize: 'var(--text-sm)'
    }
  }, "No documents on file yet.")));
}
window.CustomerProfileScreen = CustomerProfileScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/CustomerProfileScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/DashboardScreen.jsx
try { (() => {
const statusTone = {
  'Active': 'success',
  'Pending review': 'warning',
  'At risk': 'danger'
};
function DashboardScreen({
  onOpenCustomer
}) {
  const {
    Card,
    Badge
  } = window.SHBDesignSystem_1dd17a;
  const {
    customers,
    deals,
    activity,
    formatCurrency
  } = window.CRMData;
  const totalAUM = customers.reduce((s, c) => s + c.balance, 0);
  const openDeals = deals.filter(d => d.stage !== 'Closed won');
  const pipelineValue = openDeals.reduce((s, d) => s + d.value, 0);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 28,
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Assets under management"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontSize: 'var(--text-3xl)',
      fontWeight: 700,
      marginTop: 6
    }
  }, formatCurrency(totalAUM))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Open pipeline value"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontSize: 'var(--text-3xl)',
      fontWeight: 700,
      marginTop: 6,
      color: 'var(--brand-primary)'
    }
  }, formatCurrency(pipelineValue))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, "Customers"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontSize: 'var(--text-3xl)',
      fontWeight: 700,
      marginTop: 6
    }
  }, customers.length))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1.6fr 1fr',
      gap: 16,
      alignItems: 'start'
    }
  }, /*#__PURE__*/React.createElement(Card, {
    padding: "0",
    style: {
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      borderBottom: '1px solid var(--border-subtle)',
      fontWeight: 600
    }
  }, "Customers"), /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 'var(--text-sm)'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      textAlign: 'left',
      color: 'var(--text-tertiary)',
      fontSize: 'var(--text-xs)',
      textTransform: 'uppercase',
      letterSpacing: '0.04em'
    }
  }, /*#__PURE__*/React.createElement("th", {
    style: {
      padding: '10px 20px'
    }
  }, "Name"), /*#__PURE__*/React.createElement("th", {
    style: {
      padding: '10px 12px'
    }
  }, "Segment"), /*#__PURE__*/React.createElement("th", {
    style: {
      padding: '10px 12px'
    }
  }, "Status"), /*#__PURE__*/React.createElement("th", {
    style: {
      padding: '10px 20px',
      textAlign: 'right'
    }
  }, "Balance"))), /*#__PURE__*/React.createElement("tbody", null, customers.map(c => /*#__PURE__*/React.createElement("tr", {
    key: c.id,
    onClick: () => onOpenCustomer && onOpenCustomer(c),
    style: {
      borderTop: '1px solid var(--border-subtle)',
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '12px 20px',
      fontWeight: 500
    }
  }, c.name), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '12px 12px',
      color: 'var(--text-secondary)'
    }
  }, c.segment), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '12px 12px'
    }
  }, /*#__PURE__*/React.createElement(Badge, {
    tone: statusTone[c.status] || 'neutral'
  }, c.status)), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '12px 20px',
      textAlign: 'right',
      fontFamily: 'var(--font-mono)'
    }
  }, formatCurrency(c.balance))))))), /*#__PURE__*/React.createElement(Card, {
    padding: "0"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      borderBottom: '1px solid var(--border-subtle)',
      fontWeight: 600
    }
  }, "Recent activity"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column'
    }
  }, activity.map(a => /*#__PURE__*/React.createElement("div", {
    key: a.id,
    style: {
      padding: '14px 20px',
      borderTop: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      gap: 4
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-sm)'
    }
  }, a.text), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-xs)',
      color: 'var(--text-tertiary)'
    }
  }, a.time)))))));
}
window.DashboardScreen = DashboardScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/DashboardScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/DealsScreen.jsx
try { (() => {
const stages = ['Discovery', 'Proposal', 'Negotiation', 'Closed won'];
const stageTone = {
  'Discovery': 'info',
  'Proposal': 'warning',
  'Negotiation': 'accent',
  'Closed won': 'success'
};
function DealsScreen() {
  const {
    Card,
    Badge
  } = window.SHBDesignSystem_1dd17a;
  const {
    deals,
    formatCurrency
  } = window.CRMData;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 28,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 16,
      alignItems: 'start'
    }
  }, stages.map(stage => {
    const items = deals.filter(d => d.stage === stage);
    const total = items.reduce((s, d) => s + d.value, 0);
    return /*#__PURE__*/React.createElement("div", {
      key: stage,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 600,
        fontSize: 'var(--text-sm)'
      }
    }, stage), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 'var(--text-xs)',
        color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)'
      }
    }, formatCurrency(total))), items.map(d => /*#__PURE__*/React.createElement(Card, {
      key: d.id,
      padding: "var(--space-4)"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 'var(--text-sm)',
        fontWeight: 500,
        marginBottom: 8
      }
    }, d.name), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-base)',
        fontWeight: 600,
        color: 'var(--brand-primary)'
      }
    }, formatCurrency(d.value)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 10
      }
    }, /*#__PURE__*/React.createElement(Badge, {
      tone: stageTone[d.stage]
    }, d.owner), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 'var(--text-xs)',
        color: 'var(--text-tertiary)'
      }
    }, d.close)))), items.length === 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 'var(--text-xs)',
        color: 'var(--text-tertiary)',
        padding: '8px 0'
      }
    }, "No deals in this stage."));
  })));
}
window.DealsScreen = DealsScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/DealsScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/LoginScreen.jsx
try { (() => {
function LoginScreen({
  onLogin
}) {
  const {
    Input,
    Button
  } = window.SHBDesignSystem_1dd17a;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--surface-inverse)',
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface-card)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-lg)',
      padding: 40,
      width: 360,
      display: 'flex',
      flexDirection: 'column',
      gap: 20
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logo/shb-logo.png",
    alt: "SHB",
    style: {
      height: 32,
      alignSelf: 'flex-start'
    }
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 'var(--text-2xl)'
    }
  }, "Sign in"), /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'var(--text-secondary)',
      fontSize: 'var(--text-sm)',
      marginTop: 4
    }
  }, "Access your relationship management workspace.")), /*#__PURE__*/React.createElement(Input, {
    label: "Work email",
    placeholder: "you@shbbank.com"
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Password",
    type: "password",
    placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
  }), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "lg",
    onClick: onLogin,
    style: {
      width: '100%'
    }
  }, "Sign in"), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      fontSize: 'var(--text-xs)',
      color: 'var(--text-tertiary)'
    }
  }, "Protected by SHB's secure access policy.")));
}
window.LoginScreen = LoginScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/LoginScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/Sidebar.jsx
try { (() => {
function Sidebar({
  active = 'dashboard',
  onNavigate
}) {
  const items = [{
    key: 'dashboard',
    label: 'Dashboard'
  }, {
    key: 'customers',
    label: 'Customers'
  }, {
    key: 'deals',
    label: 'Deals'
  }, {
    key: 'accounts',
    label: 'Accounts'
  }, {
    key: 'reports',
    label: 'Reports'
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: 220,
      background: 'var(--surface-card)',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 12px',
      gap: 4,
      fontFamily: 'var(--font-body)',
      flexShrink: 0,
      borderRight: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '0 10px',
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logo/shb-logo.png",
    alt: "SHB",
    style: {
      height: 24
    }
  })), items.map(it => {
    const isActive = it.key === active;
    return /*#__PURE__*/React.createElement("div", {
      key: it.key,
      onClick: () => onNavigate && onNavigate(it.key),
      style: {
        padding: '10px 14px',
        borderRadius: 'var(--radius-sm)',
        cursor: 'pointer',
        fontSize: 'var(--text-sm)',
        fontWeight: isActive ? 600 : 500,
        background: isActive ? 'var(--surface-accent-soft)' : 'transparent',
        color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
        borderLeft: isActive ? '3px solid var(--brand-primary)' : '3px solid transparent',
        transition: 'background var(--duration-fast) var(--ease-standard)'
      }
    }, it.label);
  }));
}
window.Sidebar = Sidebar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/Sidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/TopBar.jsx
try { (() => {
function TopBar({
  title,
  rmName = 'J. Tran'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '18px 28px',
      borderBottom: '1px solid var(--border-subtle)',
      background: 'var(--surface-card)',
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 'var(--text-2xl)',
      color: 'var(--text-primary)'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 34,
      height: 34,
      borderRadius: '50%',
      background: 'var(--color-navy-100)',
      color: 'var(--brand-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 700,
      fontSize: 13
    }
  }, rmName.split(' ').map(s => s[0]).join('')), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-sm)',
      color: 'var(--text-secondary)'
    }
  }, rmName)));
}
window.TopBar = TopBar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/TopBar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/crm/data.js
try { (() => {
if (!window.CRMData) {
  const customers = [{
    id: 'c1',
    name: 'Acme Holdings',
    segment: 'Commercial',
    rm: 'J. Tran',
    status: 'Active',
    balance: 4820340,
    lastContact: 'Jul 8, 2026'
  }, {
    id: 'c2',
    name: 'Nolan & Reyes LLP',
    segment: 'Private',
    rm: 'M. Alvarez',
    status: 'Active',
    balance: 1240500,
    lastContact: 'Jul 10, 2026'
  }, {
    id: 'c3',
    name: 'Green Harbor Foods',
    segment: 'Commercial',
    rm: 'J. Tran',
    status: 'Pending review',
    balance: 892100,
    lastContact: 'Jul 3, 2026'
  }, {
    id: 'c4',
    name: 'Priya Shah',
    segment: 'Private',
    rm: 'S. Okafor',
    status: 'Active',
    balance: 318420,
    lastContact: 'Jun 29, 2026'
  }, {
    id: 'c5',
    name: 'Delta Freight Co.',
    segment: 'Commercial',
    rm: 'M. Alvarez',
    status: 'At risk',
    balance: 2103900,
    lastContact: 'Jun 22, 2026'
  }];
  const deals = [{
    id: 'd1',
    name: 'Acme Holdings — Term loan renewal',
    stage: 'Proposal',
    value: 1200000,
    owner: 'J. Tran',
    close: 'Jul 30, 2026'
  }, {
    id: 'd2',
    name: 'Green Harbor — Working capital line',
    stage: 'Discovery',
    value: 450000,
    owner: 'J. Tran',
    close: 'Aug 12, 2026'
  }, {
    id: 'd3',
    name: 'Nolan & Reyes — Wealth management',
    stage: 'Negotiation',
    value: 780000,
    owner: 'M. Alvarez',
    close: 'Jul 18, 2026'
  }, {
    id: 'd4',
    name: 'Delta Freight — Equipment financing',
    stage: 'Discovery',
    value: 2100000,
    owner: 'M. Alvarez',
    close: 'Sep 1, 2026'
  }, {
    id: 'd5',
    name: 'Priya Shah — Mortgage refinance',
    stage: 'Closed won',
    value: 620000,
    owner: 'S. Okafor',
    close: 'Jun 30, 2026'
  }];
  const activity = [{
    id: 'a1',
    text: 'Statement sent to Acme Holdings',
    time: '2h ago',
    tone: 'success'
  }, {
    id: 'a2',
    text: 'Deal "Wealth management" moved to Negotiation',
    time: '5h ago',
    tone: 'info'
  }, {
    id: 'a3',
    text: 'Green Harbor Foods flagged for review',
    time: 'Yesterday',
    tone: 'warning'
  }, {
    id: 'a4',
    text: 'Payment failed for Delta Freight Co.',
    time: 'Jul 9, 2026',
    tone: 'danger'
  }];
  function formatCurrency(n) {
    return '$' + n.toLocaleString('en-US', {
      maximumFractionDigits: 0
    });
  }
  window.CRMData = {
    customers,
    deals,
    activity,
    formatCurrency
  };
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/crm/data.js", error: String((e && e.message) || e) }); }

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Tabs = __ds_scope.Tabs;

})();
