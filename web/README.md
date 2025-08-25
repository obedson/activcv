# AI CV Agent - Frontend

Next.js frontend application for the AI CV Agent platform.

## Features

- Modern, responsive UI with Tailwind CSS
- shadcn/ui component library
- TypeScript for type safety
- Supabase authentication integration
- Real-time job status updates
- Multi-step profile forms
- Document management interface

## Getting Started

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your Supabase configuration
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```

4. **Open http://localhost:3000**

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── app/              # Next.js App Router pages
├── components/       # Reusable UI components
├── lib/             # Utility functions and configurations
└── types/           # TypeScript type definitions
```

## Environment Variables

Create a `.env.local` file with:

```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```