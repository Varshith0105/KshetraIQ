import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

/**
 * Separate dev-mode on-demand bundles (.next-dev) from production builds
 * (.next-kshetraiq) so running `next dev` and `next build` never corrupt each
 * other's chunk manifests and runtime modules (e.g. "Cannot find module './477.js'").
 */
const nextConfig = (phase) => {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;
  return {
    distDir: isDev ? ".next-dev" : ".next-kshetraiq",
  };
};

export default nextConfig;
