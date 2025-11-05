# Kindroot Consumer Frontend

A mobile-first, single-page website designed to help parents support each other through an engaging quiz experience.

## Overview

This is a simple, lightweight React + TypeScript application built with Vite and styled with TailwindCSS. The site emphasizes authenticity and peer support over commercial branding.

**Website URL:** kindroot.io  
**Quiz URL:** https://form.typeform.com/to/sf98mAlp

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Mobile-First Design** - Optimized for mobile devices

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The site will be available at `http://localhost:3001`

### Build for Production

```bash
# Create optimized production build
npm run build

# Preview production build locally
npm run preview
```

## Project Structure

```
consumer_frontend/
├── src/
│   ├── components/
│   │   ├── Hero.tsx       # Hero section with primary CTA
│   │   └── About.tsx      # About/Why section
│   ├── App.tsx            # Main app component
│   ├── main.tsx           # App entry point
│   └── index.css          # Global styles and Tailwind
├── public/                # Static assets
├── index.html             # HTML template
└── package.json           # Dependencies and scripts
```

## Design Principles

Following the PRD guidelines:

- **Simple & Clean** - Minimal, uncluttered design
- **Mobile-First** - Optimized for 80%+ mobile traffic
- **Authentic** - Grassroots aesthetic, not overly polished
- **Accessible** - WCAG 2.1 Level AA compliant
- **Fast** - Target load time under 3 seconds on 3G

## Key Features

### Hero Section
- Clear headline explaining value proposition
- Prominent "Take the Quiz" CTA button
- Mobile-optimized (44x44px minimum tap target)
- Links to Typeform quiz

### About Section
- Warm, conversational tone
- Explains "parents helping parents" mission
- Personal, authentic messaging
- Secondary CTA to start quiz

## Performance Targets

- **Page Weight:** Under 1MB total
- **Load Time:** Under 3 seconds on 3G
- **Mobile-First:** 320px - 767px primary focus
- **Accessibility:** WCAG 2.1 Level AA

## Browser Support

- iOS Safari (last 2 versions)
- Chrome Mobile (last 2 versions)
- Chrome Desktop (last 2 versions)
- Firefox (last 2 versions)
- Edge (last 2 versions)

## Development Notes

- Keep it simple - resist adding unnecessary features
- Maintain authentic, grassroots feel
- Mobile experience is the priority
- When in doubt, choose simplicity

## License

Private - Kindroot Project
