"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import {
  LeafIcon,
  AlertCircleIcon,
  InfoIcon,
} from "../components/Icons";

export default function SignupPage() {
  const router = useRouter();
  const { user, loading, register, getGoogleAuthUrl } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleNotice, setGoogleNotice] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [user, loading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }
    if (!email.trim()) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 6) {
      setError("Password must contain at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Password confirmation does not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password, fullName, confirmPassword);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. An account with this email may already exist.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignUp = async () => {
    setGoogleLoading(true);
    setGoogleNotice(null);
    try {
      const callbackUri = typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : undefined;
      if (typeof window !== "undefined") {
        sessionStorage.setItem("kshetraiq_post_auth_redirect", "/dashboard");
      }
      const res = await getGoogleAuthUrl(callbackUri);
      if (res.configured && res.url) {
        window.location.href = res.url;
      } else {
        setGoogleNotice(
          res.message || "Google OAuth credentials are not configured on the backend server."
        );
      }
    } catch (err: any) {
      setGoogleNotice(err.message || "Failed to initialize Google authentication.");
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f3f7f4 0%, #e8f1e9 100%)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "40px 20px",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Brand Header */}
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "linear-gradient(135deg, #1b4d2e, #2d7a46)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              boxShadow: "0 6px 14px rgba(27, 77, 46, 0.25)",
            }}
          >
            <LeafIcon size={24} />
          </div>
          <div style={{ textAlign: "left" }}>
            <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "#11381e", lineHeight: 1.1 }}>
              Kshetra<span style={{ color: "#2d7a46" }}>IQ</span>
            </div>
            <div style={{ fontSize: "0.72rem", color: "#4d6b52", fontWeight: 500 }}>
              AI-Powered Agricultural Intelligence
            </div>
          </div>
        </Link>
      </div>

      {/* Main Card */}
      <div
        style={{
          width: "100%",
          maxWidth: 460,
          background: "#fff",
          borderRadius: 16,
          padding: 32,
          boxShadow: "0 10px 30px rgba(17, 56, 30, 0.08)",
          border: "1px solid #dce8dd",
        }}
      >
        <h1 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#11381e", marginBottom: 6 }}>
          Create your farm account
        </h1>
        <p style={{ fontSize: "0.85rem", color: "#54775b", marginBottom: 24 }}>
          Join thousands of farmers making scientifically backed crop and irrigation decisions.
        </p>

        {/* Google Quick Signup */}
        <button
          onClick={handleGoogleSignUp}
          disabled={googleLoading}
          type="button"
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            padding: "11px 16px",
            background: "#fff",
            border: "1px solid #cfded1",
            borderRadius: 8,
            fontSize: "0.9rem",
            fontWeight: 600,
            color: "#273e2c",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.03h3.88c2.27-2.09 3.665-5.17 3.665-9.12z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.03c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.13C3.25 21.37 7.31 24 12 24z"
            />
            <path
              fill="#FBBC05"
              d="M5.28 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.57H1.26C.46 8.16 0 9.97 0 12s.46 3.84 1.26 5.43l4.02-3.14z"
            />
            <path
              fill="#EA4335"
              d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.63 1.26 6.57l4.02 3.14c.95-2.83 3.6-4.96 6.72-4.96z"
            />
          </svg>
          <span>{googleLoading ? "Connecting..." : "Sign up with Google"}</span>
        </button>

        {googleNotice && (
          <div
            style={{
              marginTop: 12,
              padding: "10px 12px",
              background: "#fff9db",
              border: "1px solid #ffe066",
              borderRadius: 6,
              fontSize: "0.78rem",
              color: "#744210",
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
            }}
          >
            <InfoIcon size={14} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{googleNotice}</span>
          </div>
        )}

        {/* Divider */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            margin: "20px 0",
            color: "#8aa691",
            fontSize: "0.78rem",
          }}
        >
          <div style={{ flex: 1, height: 1, background: "#e2ece3" }} />
          <span style={{ padding: "0 12px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            or register with email
          </span>
          <div style={{ flex: 1, height: 1, background: "#e2ece3" }} />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && (
            <div
              style={{
                padding: "10px 12px",
                background: "#fde8e8",
                border: "1px solid #f8b4b4",
                borderRadius: 6,
                color: "#9b1c1c",
                fontSize: "0.82rem",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <AlertCircleIcon size={14} />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#224127", marginBottom: 5 }}>
              Full Name / Farmer Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Ramesh Kumar"
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #cfded1",
                fontSize: "0.9rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#224127", marginBottom: 5 }}>
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="farmer@example.com"
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #cfded1",
                fontSize: "0.9rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
              <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "#224127" }}>
                Password (min. 6 characters)
              </label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#2d7a46",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #cfded1",
                fontSize: "0.9rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#224127", marginBottom: 5 }}>
              Confirm Password
            </label>
            <input
              type={showPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #cfded1",
                fontSize: "0.9rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              marginTop: 8,
              padding: "12px",
              borderRadius: 8,
              border: "none",
              background: "linear-gradient(135deg, #1b4d2e, #2d7a46)",
              color: "#fff",
              fontWeight: 600,
              fontSize: "0.92rem",
              cursor: "pointer",
              boxShadow: "0 2px 6px rgba(27, 77, 46, 0.2)",
            }}
          >
            {submitting ? "Creating your account..." : "Complete Registration"}
          </button>
        </form>

        {/* Footer Link */}
        <div style={{ marginTop: 24, textAlign: "center", fontSize: "0.85rem", color: "#4f7055" }}>
          Already have an account?{" "}
          <Link
            href="/login"
            style={{ color: "#1b4d2e", fontWeight: 700, textDecoration: "none" }}
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
