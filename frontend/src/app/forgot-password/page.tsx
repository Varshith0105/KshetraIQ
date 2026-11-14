"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { LeafIcon } from "../components/Icons";
import { getApiBaseUrl } from "../context/AuthContext";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState(""); const [busy, setBusy] = useState(false); const [notice, setNotice] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setNotice(""); try { const result = await fetch(`${getApiBaseUrl()}/api/v1/auth/password-reset/request`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); const body = await result.json().catch(() => null); setNotice(body?.message || "If an account exists for that email, password-reset instructions have been sent."); } catch { setNotice("We could not reach the server. Please try again."); } finally { setBusy(false); } }
  return <main className="auth-scene"><div className="auth-card"><Link href="/" className="auth-brand"><span><LeafIcon size={23} /></span><strong>Kshetra<span>IQ</span></strong></Link><p className="auth-kicker">Password recovery</p><h1>Reset your password</h1><p className="auth-lede">Enter your account email and we’ll send a one-time reset link if email delivery is configured.</p><form onSubmit={submit}><label>Email address<input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label><button className="auth-submit" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button></form>{notice && <p className="auth-note">{notice}</p>}<p className="auth-footer"><Link href="/login">Back to sign in</Link></p></div></main>;
}
