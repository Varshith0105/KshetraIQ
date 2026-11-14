"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { getApiBaseUrl } from "../context/AuthContext";

export default function ResetPasswordPage() {
  const [token, setToken] = useState(""); const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState(""); const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  useEffect(() => setToken(new URLSearchParams(window.location.search).get("token") || ""), []);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setMessage(""); if (!token) { setError("This password-reset link is missing its token."); return; } if (password.length < 8) { setError("Use at least 8 characters."); return; } if (password !== confirm) { setError("Passwords do not match."); return; } setBusy(true); try { const result = await fetch(`${getApiBaseUrl()}/api/v1/auth/password-reset/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, password, confirm_password: confirm }) }); const body = await result.json().catch(() => null); if (!result.ok) throw new Error(body?.detail || "Unable to reset password."); setMessage("Password updated. You can now sign in."); } catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "Unable to reset password."); } finally { setBusy(false); } }
  return <main className="auth-scene"><div className="auth-card"><p className="auth-kicker">Secure password reset</p><h1>Choose a new password</h1><p className="auth-lede">Your existing sessions will be signed out after this change.</p><form onSubmit={submit}>{error && <p className="auth-error">{error}</p>}<label>New password<input required minLength={8} autoComplete="new-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label><label>Confirm new password<input required minLength={8} autoComplete="new-password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label><button className="auth-submit" disabled={busy}>{busy ? "Updating…" : "Update password"}</button></form>{message && <p className="auth-note">{message} <Link href="/login">Sign in</Link></p>}</div></main>;
}
