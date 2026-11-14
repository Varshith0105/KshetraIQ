"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircleIcon, InfoIcon, LeafIcon } from "../components/Icons";
import { useAuth } from "../context/AuthContext";

function LoginContent() {
  const router = useRouter();
  const params = useSearchParams();
  const candidate = params.get("redirect") || "/dashboard";
  const redirectPath = candidate.startsWith("/") && !candidate.startsWith("//") ? candidate : "/dashboard";
  const { user, loading, login, getGoogleAuthUrl } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [googleNotice, setGoogleNotice] = useState("");

  useEffect(() => {
    if (!loading && user) router.replace(redirectPath);
  }, [loading, redirectPath, router, user]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    if (!email.trim() || !password) { setError("Enter your email address and password."); return; }
    setSubmitting(true);
    try { await login(email, password, rememberMe); router.replace(redirectPath); }
    catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "Unable to sign in. Please try again."); }
    finally { setSubmitting(false); }
  }

  async function handleGoogle() {
    setGoogleLoading(true); setGoogleNotice("");
    try {
      const callbackUri = `${window.location.origin}/auth/callback`;
      sessionStorage.setItem("kshetraiq_post_auth_redirect", redirectPath);
      const result = await getGoogleAuthUrl(callbackUri);
      if (!result.configured || !result.url) { setGoogleNotice(result.message || "Google Sign-In is not configured on this server."); return; }
      window.location.assign(result.url);
    } catch (reason: unknown) { setGoogleNotice(reason instanceof Error ? reason.message : "Google Sign-In could not be started."); }
    finally { setGoogleLoading(false); }
  }

  return <main className="auth-scene"><div className="auth-card" aria-live="polite">
    <Link href="/" className="auth-brand" aria-label="KshetraIQ home"><span><LeafIcon size={23} /></span><strong>Kshetra<span>IQ</span></strong></Link>
    <p className="auth-kicker">AI-powered agricultural intelligence</p><h1>Welcome back</h1><p className="auth-lede">Sign in to continue to your farm workspace.</p>
    <button className="google-button" type="button" disabled={googleLoading} onClick={handleGoogle}>{googleLoading ? "Connecting to Google…" : "Continue with Google"}</button>
    {googleNotice && <p className="auth-note"><InfoIcon size={15} />{googleNotice}</p>}
    <div className="auth-divider"><span>or continue with email</span></div>
    <form onSubmit={handleSubmit} noValidate>
      {error && <p className="auth-error"><AlertCircleIcon size={15} />{error}</p>}
      <label>Email address<input autoComplete="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="farmer@example.com" required /></label>
      <label>Password<span className="field-action"><Link href="/forgot-password">Forgot password?</Link><button type="button" onClick={() => setShowPassword(!showPassword)}>{showPassword ? "Hide" : "Show"}</button></span><input autoComplete="current-password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      <label className="remember"><input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />Remember me for 30 days</label>
      <button className="auth-submit" disabled={submitting} type="submit">{submitting ? "Signing in…" : "Sign in"}</button>
    </form><p className="auth-footer">New to KshetraIQ? <Link href="/signup">Create an account</Link></p>
  </div></main>;
}

export default function LoginPage() { return <React.Suspense fallback={<main className="auth-scene" />}><LoginContent /></React.Suspense>; }
