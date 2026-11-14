"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth, getApiBaseUrl } from "../../context/AuthContext";
import { LeafIcon, AlertCircleIcon } from "../../components/Icons";

function GoogleAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();

  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const oauthError = searchParams.get("error");
  const oauthErrorDesc = searchParams.get("error_description");

  const [status, setStatus] = useState<"processing" | "error" | "success">("processing");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const hasExchangedRef = useRef<boolean>(false);

  useEffect(() => {
    if (oauthError) {
      setStatus("error");
      setErrorMessage(oauthErrorDesc || `Google authentication cancelled or rejected (${oauthError}).`);
      return;
    }

    if (!code) {
      setStatus("error");
      setErrorMessage("Missing authorization code from Google OAuth redirect.");
      return;
    }

    if (hasExchangedRef.current) return;
    hasExchangedRef.current = true;

    const exchangeCode = async () => {
      try {
        const apiUrl = getApiBaseUrl();
        const redirectUri = `${window.location.origin}/auth/callback`;

        const res = await fetch(`${apiUrl}/api/v1/auth/google/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.detail || `Authentication failed with status ${res.status}`);
        }

        await res.json();

        await refreshUser();
        setStatus("success");
        const savedRedirect = typeof window !== "undefined" ? sessionStorage.getItem("kshetraiq_post_auth_redirect") : null;
        if (typeof window !== "undefined") sessionStorage.removeItem("kshetraiq_post_auth_redirect");
        const destination = savedRedirect && savedRedirect.startsWith("/") && !savedRedirect.startsWith("//")
          ? savedRedirect
          : "/dashboard";
        router.replace(destination);
      } catch (err: any) {
        setStatus("error");
        setErrorMessage(err.message || "Failed to exchange Google OAuth code.");
      }
    };

    exchangeCode();
  }, [code, state, oauthError, oauthErrorDesc, refreshUser, router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f3f7f4 0%, #e8f1e9 100%)",
        padding: 20,
        fontFamily: "Inter, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "#fff",
          borderRadius: 16,
          padding: 36,
          textAlign: "center",
          boxShadow: "0 10px 30px rgba(17, 56, 30, 0.08)",
          border: "1px solid #dce8dd",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: "linear-gradient(135deg, #1b4d2e, #2d7a46)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            margin: "0 auto 20px",
          }}
        >
          <LeafIcon size={24} />
        </div>

        {status === "processing" && (
          <div>
            <div
              style={{
                width: 36,
                height: 36,
                border: "3px solid #dce8dd",
                borderTopColor: "#1b4d2e",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
                margin: "0 auto 16px",
              }}
            />
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#11381e", marginBottom: 6 }}>
              Verifying Google Credentials
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#54775b" }}>
              Establishing secure session for your farm account...
            </p>
          </div>
        )}

        {status === "success" && (
          <div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#1b4d2e", marginBottom: 6 }}>
              Authentication Successful
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#54775b" }}>
              Redirecting to your KshetraIQ dashboard...
            </p>
          </div>
        )}

        {status === "error" && (
          <div>
            <div style={{ color: "#c53030", margin: "0 auto 12px", display: "inline-block" }}>
              <AlertCircleIcon size={32} />
            </div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#9b1c1c", marginBottom: 8 }}>
              Google Sign-In Failed
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#742a2a", lineHeight: 1.5, marginBottom: 24 }}>
              {errorMessage}
            </p>
            <Link
              href="/login"
              style={{
                display: "inline-block",
                padding: "10px 20px",
                background: "#1b4d2e",
                color: "#fff",
                borderRadius: 8,
                fontWeight: 600,
                fontSize: "0.88rem",
                textDecoration: "none",
              }}
            >
              Return to Login
            </Link>
          </div>
        )}
      </div>

      <style jsx global>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}

export default function GoogleAuthCallbackPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f3f7f4" }}>
          <div style={{ width: 36, height: 36, border: "3px solid #dce8dd", borderTopColor: "#1b4d2e", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
        </div>
      }
    >
      <GoogleAuthCallbackContent />
    </React.Suspense>
  );
}
