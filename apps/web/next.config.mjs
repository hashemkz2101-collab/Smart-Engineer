// The browser talks only to this origin; /api/* is proxied to the FastAPI service so
// the session cookie stays first-party and no CORS configuration is needed.
// When the API runs on another origin, start it with
// SMART_ENGINEER_ALLOWED_ORIGINS=<this site's origin> (see README).
const apiOrigin = process.env.SMART_ENGINEER_API_ORIGIN ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
