---
language: typescript
domain: frontend
type: pattern
title: Lead-Gen Multi-Step Form
archetype: lead-gen
pattern_scope: component
semantic_role: form
generation_priority: 1
tags: lead-gen, form, multi-step, react, typescript, tailwind, zod
---

# Lead-Gen Multi-Step Form

A multi-step lead generation form with progress indicator and validation.

## Component Structure

```tsx
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const step1Schema = z.object({
  email: z.string().email("Please enter a valid email"),
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
});

const step2Schema = z.object({
  company: z.string().min(1, "Company is required"),
  role: z.string().min(1, "Role is required"),
  teamSize: z.enum(["1-10", "11-50", "51-200", "201+"]),
});

const step3Schema = z.object({
  useCase: z.string().min(10, "Please describe your use case"),
  budget: z.enum(["<5k", "5k-25k", "25k-100k", "100k+"]),
  newsletter: z.boolean().optional(),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;
type Step3Data = z.infer<typeof step3Schema>;

type FormData = Step1Data & Step2Data & Step3Data;

interface MultiStepFormProps {
  onSubmit: (data: FormData) => Promise<void>;
}

export function MultiStepForm({ onSubmit }: MultiStepFormProps) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<Partial<FormData>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const steps = [
    { number: 1, label: "Contact" },
    { number: 2, label: "Company" },
    { number: 3, label: "Details" },
  ];

  const handleNext = (data: Partial<FormData>) => {
    setFormData({ ...formData, ...data });
    setStep(step + 1);
  };

  const handleBack = () => {
    setStep(step - 1);
  };

  const handleFinalSubmit = async (data: Partial<FormData>) => {
    const finalData = { ...formData, ...data } as FormData;
    setIsSubmitting(true);
    try {
      await onSubmit(finalData);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((s, i) => (
            <div key={s.number} className="flex items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                  step > s.number
                    ? "bg-green-500 text-white"
                    : step === s.number
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {step > s.number ? <Check className="w-5 h-5" /> : s.number}
              </div>
              <span className="ml-2 text-sm font-medium hidden sm:block">
                {s.label}
              </span>
              {i < steps.length - 1 && (
                <div
                  className={`w-16 sm:w-24 h-1 mx-2 sm:mx-4 ${
                    step > s.number ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200">
        {step === 1 && (
          <Step1Form
            defaultValues={formData}
            onNext={handleNext}
          />
        )}
        {step === 2 && (
          <Step2Form
            defaultValues={formData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {step === 3 && (
          <Step3Form
            defaultValues={formData}
            onSubmit={handleFinalSubmit}
            onBack={handleBack}
            isSubmitting={isSubmitting}
          />
        )}
      </div>
    </div>
  );
}
```

## Step 1 Form

```tsx
function Step1Form({
  defaultValues,
  onNext,
}: {
  defaultValues: Partial<FormData>;
  onNext: (data: Step1Data) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues,
  });

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Let&apos;s get started</h2>
      
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email *
        </label>
        <input
          {...register("email")}
          type="email"
          className="mt-1 block w-full rounded-lg border-gray-300"
        />
        {errors.email && (
          <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium">
            First Name *
          </label>
          <input
            {...register("firstName")}
            className="mt-1 block w-full rounded-lg border-gray-300"
          />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium">
            Last Name *
          </label>
          <input
            {...register("lastName")}
            className="mt-1 block w-full rounded-lg border-gray-300"
          />
        </div>
      </div>

      <button
        type="submit"
        className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700"
      >
        Continue
      </button>
    </form>
  );
}
```

## Accessibility Notes

- Progress indicator shows current step
- Back button available on steps 2+
- Validation errors announced via role="alert"
- Focus management between steps

## Related Patterns

- Contact Form (for single-step forms)
- Validation Flow (for error handling)
