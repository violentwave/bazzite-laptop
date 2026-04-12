# Analytics & Forms Integration

Standards for analytics implementation, form handling, and conversion tracking.

---

## Purpose

This document defines requirements and best practices for integrating analytics, forms, and conversion tracking into generated websites. It ensures consistent implementation across all projects.

---

## Analytics Integration

### Supported Analytics Platforms

| Platform | Use Case | Integration |
|----------|----------|-------------|
| Google Analytics 4 | Standard web analytics | gtag.js / Google Tag Manager |
| Plausible | Privacy-focused analytics | Script embed |
| Fathom | Simple, privacy-first | Script embed |
| Mixpanel | Product analytics | SDK + server-side |
| PostHog | Open-source, self-hosted | SDK + server-side |
| Amplitude | Product + user analytics | SDK + server-side |

### Google Analytics 4 Setup

#### Basic Implementation

```html
<!-- In <head> or via layout component -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

#### React/Next.js Implementation

```typescript
// lib/analytics.ts
export const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_ID;

// Track page views
export function trackPageView(url: string) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('config', GA_MEASUREMENT_ID, {
      page_path: url,
    });
  }
}

// Track custom events
export function trackEvent(
  action: string,
  category: string,
  label: string,
  value?: number
) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
      value: value,
    });
  }
}

// Type declarations
declare global {
  interface Window {
    gtag: (
      command: string,
      action: string,
      params?: Record<string, unknown>
    ) => void;
    dataLayer: unknown[];
  }
}
```

#### GA4 Event Categories

| Event Name | Category | When to Fire |
|------------|----------|--------------|
| `page_view` | Engagement | Route change |
| `form_submit` | Form | Successful submission |
| `form_start` | Form | First field interaction |
| `click` | CTA | Button/link click |
| `scroll` | Engagement | Scroll depth milestones |
| `video_start` | Video | Video play |
| `video_complete` | Video | Video finished |
| `purchase` | E-commerce | Transaction complete |
| `sign_up` | Authentication | Account created |
| `login` | Authentication | User logged in |

### Analytics Checklist

**Pre-Launch:**
- [ ] GA4 property created
- [ ] Measurement ID (G-XXXXXXXXXX) obtained
- [ ] Data stream configured for website
- [ ] Enhanced measurement enabled (scrolls, outbound clicks, site search, video engagement)
- [ ] Cross-domain tracking configured (if multiple domains)
- [ ] Internal traffic filter set up
- [ ] Goals/events configured in GA4

**Implementation:**
- [ ] GA script added to site header
- [ ] Page view tracking on route changes
- [ ] Custom events for key user actions
- [ ] Conversion events marked as "key events"
- [ ] E-commerce tracking (if applicable)
- [ ] User ID tracking enabled (if authenticated)

**Post-Launch:**
- [ ] Verify data flowing in Realtime reports
- [ ] Test all custom events in DebugView
- [ ] Configure audience segments
- [ ] Set up custom dashboards
- [ ] Schedule automated reports

---

## Form Integration Requirements

### Form Types

| Form Type | Purpose | Integration Requirements |
|-----------|---------|-------------------------|
| Contact | General inquiries | Email notification, CRM sync |
| Newsletter | Email capture | ESP integration (Mailchimp, etc.) |
| Lead Capture | Sales leads | CRM integration (HubSpot, etc.) |
| Quote Request | Complex inquiries | Email + CRM + workflow |
| Login/Register | Authentication | Auth provider integration |
| Support | Help requests | Ticket system integration |

### Form Handling Architecture

```typescript
// types/form.ts
export interface FormConfig {
  id: string;
  endpoint: string;
  method: 'POST' | 'GET';
  fields: FieldConfig[];
  successAction: SuccessAction;
  errorHandling: ErrorHandling;
  analytics: AnalyticsConfig;
}

export interface FieldConfig {
  name: string;
  type: 'text' | 'email' | 'phone' | 'select' | 'textarea' | 'checkbox' | 'file';
  label: string;
  required: boolean;
  validation?: ValidationRule[];
}

export interface AnalyticsConfig {
  formSubmitEvent: string;
  formSuccessEvent: string;
  formErrorEvent: string;
  conversionGoal: string;
}
```

### Integration Providers

#### Netlify Forms

```html
<form name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field">
  <input type="hidden" name="form-name" value="contact" />
  <p class="hidden">
    <label>Don't fill this out: <input name="bot-field" /></label>
  </p>
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message"></textarea>
  <button type="submit">Send</button>
</form>
```

**Netlify Forms Features:**
- Spam filtering (honeypot + reCAPTCHA)
- Email notifications
- Slack notifications
- Export to CSV
- Webhook integration

#### Formspree

```html
<form action="https://formspree.io/f/{form_id}" method="POST">
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message"></textarea>
  <input type="hidden" name="_subject" value="New Contact Form Submission" />
  <button type="submit">Send</button>
</form>
```

#### Custom API Endpoint

```typescript
// lib/forms.ts
export async function submitForm<T extends Record<string, unknown>>(
  endpoint: string,
  data: T,
  options?: {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
    analytics?: {
      formName: string;
      eventName: string;
    };
  }
) {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Form submission failed: ${response.status}`);
    }

    // Track analytics event
    if (options?.analytics) {
      trackEvent('form_submit', 'Form', options.analytics.formName);
      trackEvent(options.analytics.eventName, 'Conversion', options.analytics.formName);
    }

    options?.onSuccess?.();
    return await response.json();
  } catch (error) {
    options?.onError?.(error as Error);
    throw error;
  }
}
```

### Form Validation Requirements

| Field Type | Client-Side | Server-Side |
|------------|-------------|-------------|
| Email | Regex + HTML5 validation | Email service validation |
| Phone | Format mask | SMS verification (optional) |
| Required | HTML5 `required` | Required check |
| URL | Format validation | URL reachability (optional) |
| File | Type + size limit | Virus scan + type verification |

```typescript
// lib/validation.ts
export const validationRules = {
  email: {
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    message: 'Please enter a valid email address',
  },
  phone: {
    pattern: /^\+?[\d\s-()]{10,}$/,
    message: 'Please enter a valid phone number',
  },
  url: {
    pattern: /^https?:\/\/[^\s/$.?#].[^\s]*$/,
    message: 'Please enter a valid URL',
  },
  minLength: (min: number) => ({
    validate: (value: string) => value.length >= min,
    message: `Must be at least ${min} characters`,
  }),
  maxLength: (max: number) => ({
    validate: (value: string) => value.length <= max,
    message: `Must be no more than ${max} characters`,
  }),
};
```

### Form Analytics Tracking

```typescript
// Track form interactions
export function trackFormInteraction(
  formName: string,
  action: 'start' | 'submit' | 'success' | 'error',
  metadata?: Record<string, unknown>
) {
  switch (action) {
    case 'start':
      trackEvent('form_start', 'Form', formName);
      break;
    case 'submit':
      trackEvent('form_submit', 'Form', formName);
      break;
    case 'success':
      trackEvent('form_success', 'Form', formName);
      // Mark as conversion
      trackEvent(`${formName}_conversion`, 'Conversion', formName);
      break;
    case 'error':
      trackEvent('form_error', 'Form', formName);
      if (metadata?.errorMessage) {
        trackEvent('form_error_detail', 'Form', `${formName}: ${metadata.errorMessage}`);
      }
      break;
  }
}
```

---

## Conversion Tracking Setup

### Key Events and Conversions

| Event | Priority | GA4 Key Event | Purpose |
|-------|----------|---------------|---------|
| Form Submit | High | Yes | Lead capture |
| Demo Request | High | Yes | Sales pipeline |
| Sign Up | High | Yes | User acquisition |
| Purchase | Critical | Yes | Revenue |
| Video Complete | Medium | No | Engagement |
| File Download | Medium | No | Content engagement |
| Scroll Depth | Low | No | Engagement |

### GA4 Key Events Configuration

```javascript
// Mark events as conversions in GA4
gtag('event', 'generate_lead', {
  currency: 'USD',
  value: 0,
});

// E-commerce purchase
gtag('event', 'purchase', {
  currency: 'USD',
  value: 99.99,
  transaction_id: 'T12345',
  items: [{
    item_id: 'SKU_12345',
    item_name: 'Product Name',
    price: 99.99,
    quantity: 1,
  }],
});
```

### Conversion Tracking Checklist

- [ ] Key events identified from brief
- [ ] Events implemented in code
- [ ] Events marked as conversions in GA4
- [ ] Conversion values assigned (if applicable)
- [ ] Google Ads linked (for ad campaigns)
- [ ] Conversion import from GA4 to Ads (if applicable)

---

## Third-Party Integrations

### CRM Integration (HubSpot, Salesforce, etc.)

```typescript
// lib/crm.ts
export async function syncToCRM(data: {
  email: string;
  name: string;
  company?: string;
  source: string;
}) {
  // HubSpot example
  const response = await fetch('https://api.hubapi.com/crm/v3/objects/contacts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.HUBSPOT_API_KEY}`,
    },
    body: JSON.stringify({
      properties: {
        email: data.email,
        firstname: data.name.split(' ')[0],
        lastname: data.name.split(' ').slice(1).join(' '),
        company: data.company,
        lead_source: data.source,
      },
    }),
  });

  return response.json();
}
```

### Email Service Integration (SendGrid, Mailchimp)

```typescript
// lib/email.ts
export async function subscribeToNewsletter(email: string) {
  // Mailchimp example
  const response = await fetch(
    `https://${process.env.MAILCHIMP_SERVER}.api.mailchimp.com/3.0/lists/${process.env.MAILCHIMP_LIST_ID}/members`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.MAILCHIMP_API_KEY}`,
      },
      body: JSON.stringify({
        email_address: email,
        status: 'subscribed',
        tags: ['website-signup'],
      }),
    }
  );

  return response.json();
}
```

### Slack Notifications

```typescript
// lib/notifications.ts
export async function notifySlack(message: {
  channel: string;
  text: string;
  blocks?: unknown[];
}) {
  const webhookUrl = process.env.SLACK_WEBHOOK_URL;
  if (!webhookUrl) return;

  await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      channel: message.channel,
      text: message.text,
      blocks: message.blocks,
    }),
  });
}

// Usage
await notifySlack({
  channel: '#leads',
  text: `New contact form submission from ${email}`,
});
```

---

## Privacy and Compliance

### GDPR/CCPA Requirements

- [ ] Cookie consent banner implemented
- [ ] Analytics only fires after consent
- [ ] Privacy policy linked in footer
- [ ] Data retention policy documented
- [ ] Right to deletion supported
- [ ] Data export functionality available

### Cookie Consent Implementation

```typescript
// lib/consent.ts
type ConsentLevel = 'necessary' | 'functional' | 'analytics' | 'marketing';

const consent = {
  necessary: true, // Always true
  functional: false,
  analytics: false,
  marketing: false,
};

export function getConsent(): typeof consent {
  if (typeof window === 'undefined') return consent;
  
  const stored = localStorage.getItem('cookie_consent');
  if (stored) {
    return JSON.parse(stored);
  }
  return consent;
}

export function setConsent(level: ConsentLevel, value: boolean) {
  const current = getConsent();
  current[level] = value;
  localStorage.setItem('cookie_consent', JSON.stringify(current));
  
  // Initialize analytics only if consented
  if (level === 'analytics' && value) {
    initializeAnalytics();
  }
}

export function initializeAnalytics() {
  const consent = getConsent();
  if (!consent.analytics) return;
  
  // Load GA4
  const script = document.createElement('script');
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  script.async = true;
  document.head.appendChild(script);
}
```

---

## Pre-Launch Analytics Checklist

- [ ] GA4 property created and data stream configured
- [ ] GA4 script installed and tested
- [ ] Enhanced measurement enabled
- [ ] Custom events implemented for all CTAs
- [ ] Form submission tracking implemented
- [ ] Conversion events marked as key events
- [ ] Test traffic filtered (IP exclusion)
- [ ] Cross-domain tracking configured (if needed)
- [ ] Privacy consent flow implemented
- [ ] DebugView tested with real events
- [ ] Real-time data visible in GA4

---

## References

- [Website Brief Schema](website-brief-schema.md) — Project brief
- [Deployment Target Pack](deployment-target-pack.md) — Platform guides
- [Environment Config Checklist](environment-config-checklist.md) — Environment variables
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Go-live procedures