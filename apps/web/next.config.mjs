// The browser talks only to this origin; /api/* is proxied to the FastAPI service so
// the session cookie stays first-party and no CORS configuration is needed.
// When the API runs on another origin, start it with
// SMART_ENGINEER_ALLOWED_ORIGINS=<this site's origin> (see README).
const apiOrigin = process.env.SMART_ENGINEER_API_ORIGIN ?? "http://127.0.0.1:8000";

// Defensive headers for every page (SEC-001). The Content-Security-Policy deliberately
// leaves script and style sources unrestricted: Next.js emits inline bootstrap scripts
// and a strict script policy would need per-request nonces. It still blocks framing,
// plugins, base-tag hijacking and form posts to other origins. HSTS is left to the TLS
// terminator in front of the site (it must only be sent over HTTPS).
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  },
];

/** @type {import('next').NextConfig} */
const devOrigins = process.env.SMART_ENGINEER_DEV_ORIGINS?.split(",").filter(Boolean);

const nextConfig = {
  poweredByHeader: false,
  // Only for the Next.js dev server opened through a forwarded Codespaces address.
  ...(devOrigins?.length ? { allowedDevOrigins: devOrigins } : {}),
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
