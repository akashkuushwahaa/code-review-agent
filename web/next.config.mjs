/** @type {import('next').NextConfig} */
const nextConfig = {
  // Lean production image for Docker (copies only what the server needs).
  output: "standalone",
};

export default nextConfig;
