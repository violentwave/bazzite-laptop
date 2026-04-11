# Lead-Generation Sites

Prompts and scaffold guidance for multi-step conversion funnels.

---

## Purpose

Lead-gen sites **capture prospect information** through progressive qualification. They balance persuasion with friction reduction, using multi-step forms to increase conversion.

---

## Funnel Architecture

### Stage 1: Awareness (Landing Page)

**Goal:** Attract and educate

**Elements:**
- Compelling headline
- Problem agitation
- Solution preview
- CTA to assessment/quiz

### Stage 2: Interest (Quiz/Assessment)

**Goal:** Qualify and engage

**Elements:**
- 3-5 questions
- Progress indicator
- Immediate value preview
- Low friction (no email yet)

### Stage 3: Desire (Results/Value)

**Goal:** Show personalized value

**Elements:**
- Results/score
- Personalized recommendation
- Social proof
- Email capture for full report

### Stage 4: Action (Contact/Book)

**Goal:** Get contact info or meeting

**Elements:**
- Form (name, email, phone)
- Calendar booking (optional)
- Trust signals
- Clear next steps

---

## Page Types

### 1. Landing Page

Similar to standard landing page but with quiz/assessment CTA instead of direct form.

**Key difference:**
- Primary CTA: "Take the 2-minute assessment"
- Secondary CTA: "See how it works"
- Form comes later in funnel

### 2. Quiz/Assessment

**Prompt:**

```markdown
TASK: Build a multi-step quiz with progress tracking.

CONTEXT:
- Steps: [3-5 questions]
- Progress: [step indicator]
- Questions: [list with options]
- Logic: [branching or linear]

FORMAT:
- Quiz.tsx
- Question.tsx
- ProgressBar.tsx
- Navigation (back/next)

CONSTRAINTS:
- One question per screen
- Progress saved (localStorage)
- Back button available
- Skip option (if applicable)
- Mobile: full-screen steps
```

### 3. Results Page

**Prompt:**

```markdown
TASK: Create a personalized results page.

CONTEXT:
- Score/categories: [define outcomes]
- Personalized text: [based on answers]
- Recommendation: [next step/product]

FORMAT:
- Results.tsx
- ScoreDisplay.tsx
- RecommendationCard.tsx
- EmailCapture.tsx

CONSTRAINTS:
- Results load immediately
- Visual summary of answers
- Clear CTA for next step
- Share results option
```

### 4. Pricing Page (Optional)

**Purpose:** Present options before contact

**Structure:**
- 2-4 pricing tiers
- Feature comparison
- Recommended tier highlighted
- "Get Started" CTA per tier

**Prompt:**

```markdown
TASK: Build a pricing page with 3 tiers.

CONTEXT:
- Tiers: [Basic/Pro/Enterprise]
- Prices: [monthly/annual toggle]
- Features: [list per tier]
- Recommended: [middle tier]

FORMAT:
- pricing.tsx
- PricingTable.tsx
- PricingTier.tsx
- BillingToggle.tsx

CONSTRAINTS:
- Recommended tier visually distinct
- Feature comparison clear
- Toggle accessible
- CTA prominent per tier
- Money-back guarantee visible
```

### 5. Contact/Booking

**Prompt:**

```markdown
TASK: Create a contact form optimized for lead capture.

CONTEXT:
- Fields: [name, email, phone, company, message]
- Required: [name, email]
- Optional: [calendar booking]

FORMAT:
- ContactForm.tsx
- FormField.tsx
- Validation with Zod
- Success state

CONSTRAINTS:
- Progressive disclosure (show fields as needed)
- Validation inline
- Loading state on submit
- Success message with next steps
- Privacy policy link
```

---

## Form Optimization

### Field Order (Least to Most Personal)

1. First name
2. Email
3. Company (optional)
4. Phone (optional)
5. Message/project details

### Progressive Profiling

```tsx
// Show additional fields only if needed
function ContactForm() {
  const [step, setStep] = useState(1);
  
  return (
    <form>
      {step === 1 && (
        <>
          <NameField />
          <EmailField />
          <Button onClick={() => setStep(2)}>Continue</Button>
        </>
      )}
      {step === 2 && (
        <>
          <PhoneField optional />
          <CompanyField optional />
          <MessageField />
          <Button type="submit">Send</Button>
        </>
      )}
    </form>
  );
}
```

### Validation Patterns

```tsx
import { z } from 'zod';

const formSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  email: z.string().email('Valid email required'),
  phone: z.string().optional(),
  company: z.string().optional(),
  message: z.string().min(10, 'Please provide more details'),
});
```

---

## Trust-Building Elements

### Throughout Funnel

- Client logos (social proof)
- Trust badges (security, certifications)
- Testimonials (relevant to stage)
- Guarantee (money-back, satisfaction)
- Privacy assurance

### Form-Specific

- SSL security indicator
- Privacy policy link
- "We respect your inbox" message
- Expected response time

---

## Progress Indicators

### Stepper

```tsx
function Stepper({ currentStep, totalSteps }) {
  return (
    <div className="flex items-center space-x-2">
      {Array.from({ length: totalSteps }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'h-2 w-8 rounded-full transition-colors',
            i < currentStep ? 'bg-blue-600' : 'bg-gray-200'
          )}
        />
      ))}
    </div>
  );
}
```

### Percentage

```tsx
function ProgressBar({ current, total }) {
  const percentage = Math.round((current / total) * 100);
  
  return (
    <div className="w-full">
      <div className="h-2 w-full rounded-full bg-gray-200">
        <div
          className="h-2 rounded-full bg-blue-600 transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-gray-600">
        Step {current} of {total} ({percentage}%)
      </p>
    </div>
  );
}
```

---

## Example File Structure

```
src/
├── pages/
│   ├── index.tsx (landing)
│   ├── quiz.tsx
│   ├── results.tsx
│   ├── pricing.tsx
│   └── contact.tsx
├── components/
│   ├── quiz/
│   │   ├── Quiz.tsx
│   │   ├── Question.tsx
│   │   ├── AnswerOption.tsx
│   │   ├── ProgressBar.tsx
│   │   └── QuizNavigation.tsx
│   ├── pricing/
│   │   ├── PricingTable.tsx
│   │   ├── PricingTier.tsx
│   │   └── BillingToggle.tsx
│   ├── forms/
│   │   ├── ContactForm.tsx
│   │   ├── FormField.tsx
│   │   └── ValidationMessage.tsx
│   └── results/
│       ├── ResultsDisplay.tsx
│       ├── ScoreCard.tsx
│       └── Recommendation.tsx
├── lib/
│   ├── quiz-data.ts
│   └── scoring-logic.ts
└── hooks/
    └── useQuizProgress.ts
```

---

## Conversion Optimization

### Principles

1. **One goal per page**
2. **Remove navigation distractions**
3. **Progressive disclosure**
4. **Immediate feedback**
5. **Social proof at decision points**

### A/B Testing Ideas

- Headline variations
- CTA button text
- Number of form fields
- Progress indicator style
- Trust badge placement

---

## Validation Checklist

- [ ] Quiz works on mobile
- [ ] Progress saved if user leaves
- [ ] Form validation clear
- [ ] Loading states on submit
- [ ] Success confirmation
- [ ] Privacy policy linked
- [ ] Follow-up email configured
- [ ] Analytics tracking on each step

---

## References

- [Lead Gen Best Practices](https://unbounce.com/lead-generation/)
- [Form Optimization Guide](https://baymard.com/blog/form-optimization)
- [Conversion Funnel Design](https://www.nngroup.com/articles/conversion-rate-optimization/)
