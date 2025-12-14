import fs from 'fs';

// Write environment variables to a file that Vite can read
const envContent = `
VITE_SUPABASE_URL=${process.env.VITE_SUPABASE_URL || ''}
VITE_SUPABASE_ANON_KEY=${process.env.VITE_SUPABASE_ANON_KEY || ''}
VITE_API_URL=${process.env.VITE_API_URL || ''}
`.trim();

console.log('Writing .env.production with Vercel env vars...');
console.log('VITE_SUPABASE_URL exists:', !!process.env.VITE_SUPABASE_URL);
console.log('VITE_SUPABASE_ANON_KEY exists:', !!process.env.VITE_SUPABASE_ANON_KEY);

fs.writeFileSync('.env.production', envContent);
console.log('.env.production created');
