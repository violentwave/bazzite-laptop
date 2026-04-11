---
language: typescript
domain: frontend
type: recipe
title: Modal Lightbox Animation
archetype: landing-page
pattern_scope: motion
semantic_role: modal
generation_priority: 5
tags: animation, modal, lightbox, dialog, react, typescript, tailwind
---

# Modal Lightbox Animation

An accessible modal/lightbox with entrance/exit animations and keyboard navigation.

## Component Implementation

```tsx
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = "md",
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();

  const sizeClasses = {
    sm: "max-w-md",
    md: "max-w-lg",
    lg: "max-w-2xl",
    xl: "max-w-4xl",
  };

  // Focus management
  useEffect(() => {
    if (!isOpen) return;

    const modal = modalRef.current;
    if (!modal) return;

    const previouslyFocused = document.activeElement as HTMLElement;

    // Focus first focusable or the modal itself
    const focusable = modal.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    (focusable || modal).focus();

    return () => {
      previouslyFocused?.focus();
    };
  }, [isOpen]);

  // Close on escape and backdrop click
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${
          prefersReducedMotion ? "" : "duration-300"
        }`}
        style={{ opacity: isOpen ? 1 : 0 }}
      />

      {/* Modal */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className={`relative w-full ${sizeClasses[size]} bg-white rounded-xl shadow-2xl transition-all ${
          prefersReducedMotion ? "" : "duration-300"
        }`}
        style={{
          transform: isOpen ? "scale(1) translateY(0)" : "scale(0.95) translateY(10px)",
          opacity: isOpen ? 1 : 0,
        }}
      >
        {/* Header */}
        {(title || onClose) && (
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            {title && (
              <h2 id="modal-title" className="text-xl font-semibold">
                {title}
              </h2>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}
```

## Usage

```tsx
const [isModalOpen, setIsModalOpen] = useState(false);

<button onClick={() => setIsModalOpen(true)}>Open Modal</button>

<Modal
  isOpen={isModalOpen}
  onClose={() => setIsModalOpen(false)}
  title="Confirm Action"
  size="md"
>
  <p>Are you sure you want to proceed?</p>
  <div className="mt-4 flex gap-3">
    <button onClick={() => setIsModalOpen(false)}>Cancel</button>
    <button onClick={handleConfirm}>Confirm</button>
  </div>
</Modal>
```

## Accessibility Notes

- Returns focus to trigger on close
- Escape closes modal
- Click outside closes modal
- aria-labelledby links to title

## Related Patterns

- Mobile Menu (similar patterns)
- Portfolio Gallery (for image lightbox)
