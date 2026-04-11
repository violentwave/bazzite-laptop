---
language: typescript
domain: frontend
type: pattern
title: Portfolio Gallery Component
archetype: portfolio
pattern_scope: component
semantic_role: gallery
generation_priority: 2
tags: portfolio, gallery, lightbox, react, typescript, tailwind
---

# Portfolio Gallery Component

A responsive portfolio gallery with modal lightbox for showcasing creative work.

## Component Structure

```tsx
interface PortfolioItem {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  fullImage: string;
  category?: string;
  tags?: string[];
}

interface PortfolioGalleryProps {
  items: PortfolioItem[];
  columns?: 2 | 3 | 4;
}

export function PortfolioGallery({ items, columns = 3 }: PortfolioGalleryProps) {
  const [selectedItem, setSelectedItem] = useState<PortfolioItem | null>(null);

  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <>
      <div className={`grid ${gridCols[columns]} gap-6`}>
        {items.map((item) => (
          <PortfolioCard
            key={item.id}
            item={item}
            onClick={() => setSelectedItem(item)}
          />
        ))}
      </div>

      {selectedItem && (
        <Lightbox
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onNext={() => {
            const currentIndex = items.findIndex((i) => i.id === selectedItem.id);
            const nextIndex = (currentIndex + 1) % items.length;
            setSelectedItem(items[nextIndex]);
          }}
          onPrev={() => {
            const currentIndex = items.findIndex((i) => i.id === selectedItem.id);
            const prevIndex = (currentIndex - 1 + items.length) % items.length;
            setSelectedItem(items[prevIndex]);
          }}
        />
      )}
    </>
  );
}

function PortfolioCard({
  item,
  onClick,
}: {
  item: PortfolioItem;
  onClick: () => void;
}) {
  return (
    <figure className="group cursor-pointer" onClick={onClick}>
      <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-gray-100">
        <img
          src={item.thumbnail}
          alt={item.title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-300 flex items-center justify-center">
          <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-medium">
            View Project
          </span>
        </div>
      </div>
      <figcaption className="mt-4">
        <h3 className="text-lg font-semibold">{item.title}</h3>
        {item.category && (
          <p className="text-sm text-gray-500">{item.category}</p>
        )}
      </figcaption>
    </figure>
  );
}

function Lightbox({
  item,
  onClose,
  onNext,
  onPrev,
}: {
  item: PortfolioItem;
  onClose: () => void;
  onNext: () => void;
  onPrev: () => void;
}) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onNext();
      if (e.key === "ArrowLeft") onPrev();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, onNext, onPrev]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={item.title}
    >
      <button
        className="absolute top-4 right-4 text-white p-2 hover:bg-white/10 rounded-lg"
        onClick={onClose}
        aria-label="Close"
      >
        <X className="w-6 h-6" />
      </button>

      <button
        className="absolute left-4 text-white p-2 hover:bg-white/10 rounded-lg"
        onClick={(e) => {
          e.stopPropagation();
          onPrev();
        }}
        aria-label="Previous image"
      >
        <ChevronLeft className="w-8 h-8" />
      </button>

      <button
        className="absolute right-4 text-white p-2 hover:bg-white/10 rounded-lg"
        onClick={(e) => {
          e.stopPropagation();
          onNext();
        }}
        aria-label="Next image"
      >
        <ChevronRight className="w-8 h-8" />
      </button>

      <div
        className="max-w-5xl max-h-[80vh] px-4"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={item.fullImage}
          alt={item.title}
          className="max-w-full max-h-[70vh] object-contain"
        />
        <div className="mt-4 text-white">
          <h2 className="text-xl font-semibold">{item.title}</h2>
          <p className="mt-1 text-gray-300">{item.description}</p>
          {item.tags && (
            <div className="mt-2 flex gap-2">
              {item.tags.map((tag, i) => (
                <span
                  key={i}
                  className="px-2 py-1 text-xs bg-white/10 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## Accessibility Notes

- Figure/figcaption for semantic structure
- Lazy loading for thumbnails
- Lightbox has keyboard navigation (arrows, escape)
- role="dialog" and aria-modal for lightbox

## Related Patterns

- Testimonial Section (for social proof)
- Hero Section (for portfolio intro)
