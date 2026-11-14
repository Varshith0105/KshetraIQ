/**
 * Keep KshetraIQ's generated artifacts separate from the stale `.next` tree
 * created by earlier interrupted builds. Never run `next dev` and `next build`
 * concurrently against this directory.
 */
const nextConfig = {
  distDir: ".next-kshetraiq",
};

export default nextConfig;
