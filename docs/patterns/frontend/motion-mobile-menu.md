---
language: typescript
domain: frontend
type: recipe
title: Mobile Menu Animation
archetype: landing-page
pattern_scope: motion
semantic_role: navigation
generation_priority: 4
tags: animation, mobile-menu, hamburger, react, typescript, tailwind
---

# Mobile Menu Animation

An accessible mobile menu with smooth open/close animations and focus trap.

## Component Implementation

```tsx
interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function MobileMenu({ isOpen, onClose, children }: MobileMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const firstFocusableRef = useRef<HTMLElement>(null);
  const prefersReducedMotion = useReducedMotion();

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;

    const menu = menuRef.current;
    if (!menu) return;

    // Focus first element
    const focusableElements = menu.querySelectorAll(
      'a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    if (firstElement) {
      firstElement.focus();
    }

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    document.addEventListener("keydown", handleTabKey);
    return () => document.removeEventListener("keydown", handleTabKey);
  }, [isOpen]);

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  return (
    <div
      ref={menuRef}
      className={`fixed inset-0 z-50 ${isOpen ? "pointer-events-auto" : "pointer-events-none"}`}
      role="dialog"
      aria-modal="true"
      aria-hidden={!isOpen}
    >
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${
          prefersReducedMotion ? "" : "duration-300"
        }`}
        style={{ opacity: isOpen ? 1 : 0 }}
        onClick={onClose}
      />

      {/* Menu Panel */}
      <div
        className={`absolute right-0 top-0 h-full w-80 max-w-full bg-white shadow-xl transition-transform ${
          prefersReducedMotion ? "" : "duration-300 ease-out"
        }`}
        style={{
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
        }}
      >
        <div className="p-4">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-gray-100 rounded-lg"
            aria-label="Close menu"
          >
            <X className="w-6 h-6" />
          </button>
          {children}
        </div>
      </div>
    </div>
  );
}
```

## Hamburger Button

```tsx
interface HamburgerButtonProps {
  isOpen: boolean;
  onClick: () => void;
}

export function HamburgerButton({ isOpen, onClick }: HamburgerButtonProps) {
  return (
    <button
      onClick={onClick}
      className="relative w-10 h-10 flex items-center justify-center"
      aria-expanded={isOpen}
      aria-label={isOpen ? "Close menu" : "Open menu"}
    >
      <span className="sr-only">Menu</span>
      <div className="relative w-6 h-5">
        <span
          className={`absolute left-0 w-6 h-0.5 bg-current transition-all duration-300 ${
            isOpen ? "top-2 rotate-45" : "top-0"
          }`}
        />
        <span
          className={`absolute left-0 top-2 w-6 h-0.5 bg-current transition-all duration-300 ${
            isOpen ? "opacity-0" : "opacity-100"
          }`}
        />
        <span
          className={`absolute left-0 w-6 h-0.5 bg-current transition-all duration-300 ${
            isOpen ? "top-2 -rotate-45" : "top-4"
          }`}
        />
      </div>
    </button>
  );
}
```

## Accessibility Notes

- Focus trap keeps keyboard navigation inside menu
- Escape key closes menu
- aria-expanded on toggle button
- Body scroll locked when open

## Related Patterns

- Navigation Header (for integration)
- Modal/Lightbox (similar focus management)
