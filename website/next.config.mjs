/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static studio site: emit plain HTML into out/ (deployable anywhere).
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true }, // we render plain <img>, not next/image
};

export default nextConfig;
